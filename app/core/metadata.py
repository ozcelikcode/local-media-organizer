import os
import re
import datetime
from typing import Optional, Tuple
from PIL import Image
import ctypes
from ctypes import wintypes

# Windows Time Structs
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

FILE_WRITE_ATTRIBUTES = 0x0100
OPEN_EXISTING = 3

def unique_destination_path(directory: str, filename: str) -> str:
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

def set_file_creation_time(path: str, timestamp: float):
    """
    Sets the creation time of a file on Windows using ctypes.
    """
    # Convert timestamp to Windows file time (100-nanosecond intervals since Jan 1, 1601)
    # Unix epoch is Jan 1, 1970. Difference is 11644473600 seconds.
    creation_time = int((timestamp + 11644473600) * 10000000)
    
    handle = kernel32.CreateFileW(
        path, 
        FILE_WRITE_ATTRIBUTES, 
        0, 
        None, 
        OPEN_EXISTING, 
        0x02000000, # FILE_FLAG_BACKUP_SEMANTICS for directories, needed? standard file is fine
        None
    )
    
    if handle == -1:
        return False
        
    c_creation_time = wintypes.FILETIME(creation_time & 0xFFFFFFFF, creation_time >> 32)
    
    # We only change creation time here. Access/Write can be handled by os.utime if needed
    result = kernel32.SetFileTime(handle, ctypes.byref(c_creation_time), None, None)
    kernel32.CloseHandle(handle)
    
    # Also update Modified time to match, as requested implicitly by "Change Date" usually
    os.utime(path, (timestamp, timestamp))
    
    return result != 0

class MetadataService:
    def __init__(self):
        self.exif_date_tag = 36867 # DateTimeOriginal
        self.exif_writable_exts = {".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".png"}

    def can_write_exif(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in self.exif_writable_exts
    
    def get_exif_date(self, path: str) -> Optional[datetime.datetime]:
        """Extracts DateTimeOriginal from image EXIF."""
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if not exif:
                    return None
                
                # Try DateTimeOriginal (36867) then DateTime (306)
                date_str = exif.get(36867) or exif.get(306)
                
                if date_str:
                    # Format: YYYY:MM:DD HH:MM:SS
                    return datetime.datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    def parse_filename_date_info(self, path: str) -> Tuple[Optional[datetime.datetime], str]:
        """
        Parses date/time hints from filename with precision info.
        Precision values: datetime, date, year-month, year, none
        """
        filename = os.path.basename(path)

        # YYYYMMDD[HHMM[SS]] and separated variants like YYYY-MM-DD 20.35.25
        full_pattern = re.compile(
            r"(?<!\d)"
            r"((?:19|20)\d{2})"
            r"[-_. ]?"
            r"(0[1-9]|1[0-2])"
            r"[-_. ]?"
            r"(0[1-9]|[12]\d|3[01])"
            r"(?:[T _.-]?"
            r"([01]\d|2[0-3])"
            r"[:._-]?"
            r"([0-5]\d)"
            r"(?:[:._-]?([0-5]\d))?"
            r")?"
            r"(?!\d)"
        )
        match = full_pattern.search(filename)
        if match:
            try:
                y, m, d = map(int, match.group(1, 2, 3))
                if match.group(4) and match.group(5):
                    H = int(match.group(4))
                    M = int(match.group(5))
                    S = int(match.group(6) or "0")
                    return datetime.datetime(y, m, d, H, M, S), "datetime"
                return datetime.datetime(y, m, d, 12, 0, 0), "date"
            except ValueError:
                pass

        # YYYY-MM (no day)
        ym_pattern = re.compile(
            r"(?<!\d)"
            r"((?:19|20)\d{2})"
            r"[-_. ]"
            r"(0[1-9]|1[0-2])"
            r"(?!\d)"
        )
        match = ym_pattern.search(filename)
        if match:
            try:
                y, m = map(int, match.group(1, 2))
                return datetime.datetime(y, m, 1, 12, 0, 0), "year-month"
            except ValueError:
                pass

        # YYYY only
        year_pattern = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
        match = year_pattern.search(filename)
        if match:
            try:
                y = int(match.group(1))
                return datetime.datetime(y, 1, 1, 12, 0, 0), "year"
            except ValueError:
                pass

        return None, "none"

    def parse_filename_date(self, path: str) -> Optional[datetime.datetime]:
        parsed, _ = self.parse_filename_date_info(path)
        return parsed

    def resolve_exif_mode_date(self, path: str) -> Tuple[Optional[datetime.datetime], str, str]:
        """
        Priority rule:
        1) EXIF is primary.
        2) If EXIF and filename year match, keep EXIF.
        3) If EXIF year is later than filename year, use filename date.
        4) If EXIF exists and is not later, keep EXIF.
        5) If EXIF missing, use filename date.
        """
        exif_date = self.get_exif_date(path)
        filename_date, filename_precision = self.parse_filename_date_info(path)

        if exif_date and filename_date:
            if exif_date.year == filename_date.year:
                return exif_date, "exif", "year-match"
            if exif_date.year > filename_date.year:
                return filename_date, "filename", "filename-overrides-future-exif"
            return exif_date, "exif", "exif-priority-mismatch"

        if exif_date:
            return exif_date, "exif", "exif-only"

        if filename_date:
            return filename_date, "filename", f"filename-only-{filename_precision}"

        return None, "none", "unresolved"

    def write_exif_date(self, path: str, dt: datetime.datetime, overwrite: bool = False) -> Tuple[bool, str]:
        """
        Writes EXIF DateTimeOriginal/DateTimeDigitized/DateTime to the file.
        Existing EXIF date fields are preserved unless overwrite=True.
        """
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                has_exif = bool(exif.get(36867) or exif.get(306))
                if has_exif and not overwrite:
                    return True, "EXIF already exists - unchanged"

                date_str = dt.strftime("%Y:%m:%d %H:%M:%S")
                exif[36867] = date_str  # DateTimeOriginal
                exif[36868] = date_str  # DateTimeDigitized
                exif[306] = date_str    # DateTime

                fmt = (img.format or "").upper()
                if fmt not in {"JPEG", "JPG", "TIFF", "WEBP", "PNG"}:
                    return False, f"EXIF write not supported for format: {fmt or 'UNKNOWN'}"

                img.save(path, exif=exif.tobytes())
                return True, date_str
        except Exception as e:
            return False, f"EXIF write failed: {str(e)}"

    def apply_date_to_file(self, path: str, mode: str, manual_date: str = None, destination_path: str = None) -> Tuple[bool, str]:
        """
        Applies date to file based on mode.
        If destination_path is provided, copies file there first, then modifies the COPY.
        Returns: (Success, Message)
        """
        import shutil
        
        target_file_path = path
        
        # 1. Handle Copy if Destination Provided
        if destination_path:
            if not os.path.isdir(destination_path):
                return False, "Destination is not a directory"
            
            fname = os.path.basename(path)
            target_file_path = unique_destination_path(destination_path, fname)
            
            try:
                shutil.copy2(path, target_file_path)
            except Exception as e:
                return False, f"Copy failed: {str(e)}"

        # 2. Determine Date
        target_date = None
        
        if mode == 'manual':
            if not manual_date:
                return False, "No date provided"
            try:
                target_date = datetime.datetime.fromisoformat(manual_date)
            except ValueError:
                return False, "Invalid manual date"
                
        elif mode == 'exif':
            resolved_date, resolved_source, resolved_rule = self.resolve_exif_mode_date(path)
            if not resolved_date:
                return False, "No EXIF and no usable date in filename"

            # If filename should override (future EXIF mismatch) or EXIF missing, write/update EXIF on target.
            # Video files cannot carry image EXIF via Pillow; for those, we only apply filesystem timestamp.
            exif_writable = self.can_write_exif(target_file_path)
            if resolved_source == "filename":
                if exif_writable:
                    ok, msg = self.write_exif_date(target_file_path, resolved_date, overwrite=True)
                    if not ok:
                        return False, msg
            else:
                # Keep existing EXIF as primary, but ensure target has EXIF after copy.
                if exif_writable and not self.get_exif_date(target_file_path):
                    ok, msg = self.write_exif_date(target_file_path, resolved_date, overwrite=False)
                    if not ok:
                        return False, msg

            # Align filesystem time to resolved date (always).
            timestamp = resolved_date.timestamp()
            success = set_file_creation_time(target_file_path, timestamp)
            if not success:
                return False, "Failed to set system time"

            suffix = "filesystem-only" if not exif_writable else resolved_rule
            return True, f"{resolved_date.isoformat()} ({suffix})"
                
        elif mode == 'filename':
            target_date = self.parse_filename_date(path) # Read from SOURCE
            if not target_date:
                return False, "No date in filename"
        
        # 3. Apply to Target
        if target_date:
            timestamp = target_date.timestamp()
            success = set_file_creation_time(target_file_path, timestamp)
            if success:
                return True, target_date.isoformat()
            else:
                return False, "Failed to set system time"
                
        return False, "Unknown error"
