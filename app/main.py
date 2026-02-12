from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import datetime
import shutil
import mimetypes
import hashlib
import subprocess
import re

from PIL import Image, ImageOps, UnidentifiedImageError
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

from app.core.scanner import FileScanner
from app.core.metadata import MetadataService
from app.db.models import init_db, SessionLocal, DuplicateGroup, FileEntry
from pydantic import BaseModel

app = FastAPI(title="Local File Organizer")

# Initialize DB
init_db()

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def localhost_only(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    if client_host not in allowed_hosts:
        return JSONResponse(status_code=403, content={"detail": "Access restricted to localhost"})
    return await call_next(request)

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff",
    ".heic", ".heif", ".avif", ".jxl",
    ".dng", ".arw", ".cr2", ".cr3", ".nef", ".nrw", ".raf", ".rw2", ".orf", ".srw", ".pef",
    ".3fr", ".iiq", ".erf", ".kdc", ".mrw", ".raw",
}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".3gp"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
THUMB_CACHE_DIR = os.path.join("memory-bank", "thumb-cache")
THUMB_CACHE_VERSION = "v2-heif-orientation"
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
ALLOWED_SOURCE_ROOTS: set[str] = set()


def _file_ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _normalize_abs(path: str) -> str:
    return os.path.abspath(path)


def _register_allowed_root(path: str) -> None:
    abs_path = _normalize_abs(path)
    if os.path.isdir(abs_path):
        ALLOWED_SOURCE_ROOTS.add(abs_path)


def _is_under_root(path: str, root: str) -> bool:
    try:
        common = os.path.commonpath([_normalize_abs(path), _normalize_abs(root)])
        return common == _normalize_abs(root)
    except ValueError:
        return False


def _is_allowed_source_path(path: str) -> bool:
    return any(_is_under_root(path, root) for root in ALLOWED_SOURCE_ROOTS)


def _is_media(path: str) -> bool:
    return _file_ext(path) in MEDIA_EXTENSIONS


def _is_video(path: str) -> bool:
    return _file_ext(path) in VIDEO_EXTENSIONS


def _safe_media_response(path: str) -> FileResponse:
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


def _unique_destination_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    if not os.path.exists(candidate):
        return candidate
    i = 2
    while True:
        candidate = os.path.join(directory, f"{base} ({i}){ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def _thumbnail_cache_path(path: str, size: int) -> str:
    try:
        stat = os.stat(path)
        cache_key = f"{THUMB_CACHE_VERSION}|{os.path.abspath(path)}|{size}|{stat.st_mtime_ns}|{stat.st_size}"
    except OSError:
        cache_key = f"{THUMB_CACHE_VERSION}|{os.path.abspath(path)}|{size}|missing"
    digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
    return os.path.join(THUMB_CACHE_DIR, f"{digest}.jpg")


def _create_image_thumbnail(src_path: str, dst_path: str, size: int, quality: int = 62) -> bool:
    try:
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")
            img.thumbnail((size, size))
            img.save(dst_path, format="JPEG", quality=quality, optimize=False)
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def _create_video_thumbnail(src_path: str, dst_path: str, size: int, quality: int = 4) -> bool:
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "00:00:01",
        "-i",
        src_path,
        "-frames:v",
        "1",
        "-vf",
        f"scale={size}:-1:force_original_aspect_ratio=decrease",
        "-q:v",
        str(quality),
        "-y",
        dst_path,
    ]
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=12, check=False)
        return result.returncode == 0 and os.path.isfile(dst_path)
    except (OSError, subprocess.SubprocessError):
        return False



def _create_media_thumbnail(src_path: str, dst_path: str, size: int, quality: int = 62) -> bool:
    if _is_video(src_path):
        return _create_video_thumbnail(src_path, dst_path, size, quality=4)

    if _create_image_thumbnail(src_path, dst_path, size, quality=quality):
        return True

    # Fallback for formats Pillow may not decode (HEIC/RAW variants).
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        src_path,
        "-frames:v",
        "1",
        "-vf",
        f"scale={size}:-1:force_original_aspect_ratio=decrease",
        "-q:v",
        "4",
        "-y",
        dst_path,
    ]
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=12, check=False)
        return result.returncode == 0 and os.path.isfile(dst_path)
    except (OSError, subprocess.SubprocessError):
        return False


def _choose_recommended_file(files: List[FileEntry]) -> Optional[FileEntry]:
    if not files:
        return None

    positive_tokens = ("dcim", "camera", "photos", "pictures", "original", "iphone", "android")
    negative_tokens = (
        "edited", "edit", "whatsapp", "telegram", "download", "cache", "temp", "export",
        "backup", "compressed", "thumbnail", "thumb", "preview",
    )
    noisy_name = re.compile(r"\(\d+\)|copy|kopya|duplicate|dupe", re.IGNORECASE)

    def score(file_entry: FileEntry):
        path = (file_entry.path or "").lower()
        name = (file_entry.filename or os.path.basename(file_entry.path) or "").lower()
        ext = _file_ext(path)

        points = 0
        if ext in IMAGE_EXTENSIONS:
            points += 40
        elif ext in VIDEO_EXTENSIONS:
            points += 35
        else:
            points += 10

        if re.match(r"^(img_|dsc_|vid_|pxl_|mvimg_)", name):
            points += 6

        for token in positive_tokens:
            if token in path:
                points += 4
        for token in negative_tokens:
            if token in path or token in name:
                points -= 6
        if noisy_name.search(name):
            points -= 4

        depth = path.count("\\") + path.count("/")
        try:
            st = os.stat(file_entry.path)
            older_priority = -st.st_mtime
        except OSError:
            older_priority = float("-inf")

        return (points, -depth, older_priority, -len(name))

    return max(files, key=score)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return FileResponse('app/static/index.html')

@app.post("/api/scan")
async def scan_directory(path: str, db: Session = Depends(get_db)):
    normalized_root = _normalize_abs(path)
    if not os.path.exists(normalized_root):
        raise HTTPException(status_code=400, detail="Path does not exist")
    
    try:
        ALLOWED_SOURCE_ROOTS.clear()
        _register_allowed_root(normalized_root)

        # Clear previous results - clear FileEntries first due to foreign key
        db.query(FileEntry).delete()
        db.query(DuplicateGroup).delete()
        db.commit()
        
        scanner = FileScanner()
        results = await scanner.scan_directory(normalized_root)
        
        # Save to DB
        for hash_val, files in results.items():
            group = DuplicateGroup(hash_value=hash_val, file_size=files[0]['size'])
            db.add(group)
            db.flush() # Flush to get ID without full commit
            
            for f in files:
                entry = FileEntry(
                    path=f['path'], 
                    filename=f['name'], 
                    group_id=group.id,
                    is_original=False 
                )
                db.add(entry)
        
        db.commit()
        return {"status": "completed", "groups_found": len(results)}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.get("/api/duplicates")
def get_duplicates(db: Session = Depends(get_db)):
    groups = db.query(DuplicateGroup).all()
    # Serialize manually for simplicity or use Pydantic models
    data = []
    for g in groups:
        data.append({
            "id": g.id,
            "hash": g.hash_value,
            "size": g.file_size,
            "files": [
                {"id": f.id, "path": f.path, "name": f.filename, "is_original": f.is_original} 
                for f in g.files
            ]
        })
    return data


@app.get("/api/duplicates_page")
def get_duplicates_page(offset: int = 0, limit: int = 32, db: Session = Depends(get_db)):
    offset = max(0, offset)
    limit = max(1, min(limit, 250))

    total = db.query(DuplicateGroup).count()
    selected_originals = db.query(FileEntry).filter(FileEntry.is_original == True).count()
    groups = (
        db.query(DuplicateGroup)
        .order_by(DuplicateGroup.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = []
    for g in groups:
        data.append({
            "id": g.id,
            "hash": g.hash_value,
            "size": g.file_size,
            "files": [
                {"id": f.id, "path": f.path, "name": f.filename, "is_original": f.is_original}
                for f in g.files
            ],
        })

    return {"total": total, "selected_originals": selected_originals, "groups": data}

@app.post("/api/mark_original/{file_id}")
def mark_original(file_id: int, db: Session = Depends(get_db)):
    file_entry = db.query(FileEntry).filter(FileEntry.id == file_id).first()
    if not file_entry:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Unmark others in group
    group_files = db.query(FileEntry).filter(FileEntry.group_id == file_entry.group_id).all()
    for f in group_files:
        f.is_original = False
    
    file_entry.is_original = True
    db.commit()
    return {"status": "ok"}


@app.post("/api/recommend_originals")
def recommend_originals(db: Session = Depends(get_db)):
    groups = db.query(DuplicateGroup).all()
    updated_groups = 0

    for group in groups:
        recommended = _choose_recommended_file(group.files)
        if not recommended:
            continue

        for f in group.files:
            f.is_original = (f.id == recommended.id)

        updated_groups += 1

    db.commit()
    return {"status": "ok", "updated_groups": updated_groups}

@app.post("/api/commit_cleanup")
def commit_cleanup(export_path: str, db: Session = Depends(get_db)):
    normalized_export_path = _normalize_abs(export_path)
    if not os.path.exists(normalized_export_path):
        raise HTTPException(status_code=400, detail="Export path not found")
        
    groups = db.query(DuplicateGroup).all()
    processed_count = 0
    
    for group in groups:
        original = next((f for f in group.files if f.is_original), None)
        if not original:
            continue # Skip groups where no original is selected
            
        # SAFETY EXPORT: Copy original to Target
        try:
            if not _is_allowed_source_path(original.path):
                continue
            original_name = original.filename or os.path.basename(original.path)
            dest_path = _unique_destination_path(normalized_export_path, original_name)
            
            shutil.copy2(original.path, dest_path)
            
            # NO DELETION - SOURCE REMAINS UNTOUCHED
            
            processed_count += 1
            
        except Exception:
            # Keep loop alive; report only final processed count for privacy.
            pass
            
    # Cleanup DB - we are done with this session
    db.query(DuplicateGroup).delete()
    db.commit()
    
    return {"status": "completed", "processed_groups": processed_count}

# METADATA ENDPOINTS

class DateUpdateRequest(BaseModel):
    files: List[str]
    mode: str # 'exif', 'filename', 'manual'
    manual_date: Optional[str] = None
    export_path: Optional[str] = None

@app.post("/api/metadata/scan")
def scan_metadata(path: str):
    normalized_root = _normalize_abs(path)
    if not os.path.exists(normalized_root):
        raise HTTPException(status_code=400, detail="Path does not exist")
    ALLOWED_SOURCE_ROOTS.clear()
    _register_allowed_root(normalized_root)
    
    service = MetadataService()
    files_data = []
    
    for entry in os.scandir(normalized_root):
        if entry.is_file():
            f_path = entry.path
            if not _is_media(f_path):
                continue
            
            # Get Current System Date
            stats = entry.stat()
            current_date = datetime.datetime.fromtimestamp(stats.st_ctime) # Creation time
            
            # Predict Dates
            exif_date = service.get_exif_date(f_path)
            name_date = service.parse_filename_date(f_path)
            
            files_data.append({
                "path": f_path,
                "name": entry.name,
                "current_date": current_date.isoformat(),
                "exif_date": exif_date.isoformat() if exif_date else None,
                "filename_date": name_date.isoformat() if name_date else None,
                "has_prediction": bool(exif_date or name_date)
            })

    files_data.sort(key=lambda x: x["name"].lower())
    return files_data

@app.get("/api/metadata/preview")
def metadata_preview(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    normalized_path = os.path.abspath(path)
    if not os.path.isfile(normalized_path):
        raise HTTPException(status_code=404, detail="File not found")
    if not _is_allowed_source_path(normalized_path):
        raise HTTPException(status_code=403, detail="Path is not in allowed scanned roots")

    if not _is_media(normalized_path):
        raise HTTPException(status_code=400, detail="Unsupported media format")

    if _is_video(normalized_path):
        return _safe_media_response(normalized_path)

    preview_size = 900
    preview_cache = _thumbnail_cache_path(normalized_path, preview_size)
    if not os.path.isfile(preview_cache):
        ok = _create_media_thumbnail(normalized_path, preview_cache, preview_size, quality=74)
        if not ok:
            raise HTTPException(status_code=500, detail="Preview generation failed")
    return FileResponse(preview_cache, media_type="image/jpeg")


@app.get("/api/metadata/thumbnail")
def metadata_thumbnail(path: str, size: int = 240):
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    normalized_path = os.path.abspath(path)
    if not os.path.isfile(normalized_path):
        raise HTTPException(status_code=404, detail="File not found")
    if not _is_allowed_source_path(normalized_path):
        raise HTTPException(status_code=403, detail="Path is not in allowed scanned roots")

    if not _is_media(normalized_path):
        raise HTTPException(status_code=400, detail="Unsupported media format")

    size = max(96, min(size, 512))
    cache_path = _thumbnail_cache_path(normalized_path, size)

    if not os.path.isfile(cache_path):
        ok = _create_media_thumbnail(normalized_path, cache_path, size, quality=62)
        if not ok:
            raise HTTPException(status_code=500, detail="Thumbnail generation failed")

    return FileResponse(cache_path, media_type="image/jpeg")

@app.post("/api/metadata/apply")
def apply_metadata_changes(req: DateUpdateRequest):
    # Validate export_path - if not provided or empty, return error
    if not req.export_path or not req.export_path.strip():
        raise HTTPException(status_code=400, detail="Export path is required")
    
    normalized_export_path = _normalize_abs(req.export_path)
    if not os.path.exists(normalized_export_path):
        raise HTTPException(status_code=400, detail="Export path does not exist")


    service = MetadataService()
    results = {"success": 0, "failed": 0, "errors": []}
    
    for path in req.files:
        normalized_source_path = _normalize_abs(path)
        if not _is_allowed_source_path(normalized_source_path):
            results["failed"] += 1
            results["errors"].append(f"{os.path.basename(path)}: source path is not in allowed scanned roots")
            continue
        if not _is_media(normalized_source_path):
            results["failed"] += 1
            results["errors"].append(f"{os.path.basename(path)}: unsupported media format")
            continue
        # Pass export_path as destination
        ok, msg = service.apply_date_to_file(normalized_source_path, req.mode, req.manual_date, destination_path=normalized_export_path)
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"{os.path.basename(path)}: {msg}")
            
    return results


