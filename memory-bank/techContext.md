# Technical Context

## Stack
- Python 3.14 (venv)
- FastAPI + Uvicorn
- SQLAlchemy + SQLite (`files.db`)
- Pillow (image + EXIF)
- xxhash (fast hashing)
- ffmpeg (video thumbnail extraction)
- Alpine.js + Tailwind CDN (static UI)

## Important Files
- Backend entry: `app/main.py`
- Metadata logic: `app/core/metadata.py`
- Scanner: `app/core/scanner.py`
- Duplicate UI: `app/static/index.html`
- Date Fixer UI: `app/static/date_fixer.html`
- Run script: `run_app.bat`

## APIs (Current)
- `POST /api/scan`
- `GET /api/duplicates_page`
- `POST /api/mark_original/{file_id}`
- `POST /api/recommend_originals`
- `POST /api/commit_cleanup`
- `POST /api/metadata/scan`
- `GET /api/metadata/preview`
- `GET /api/metadata/thumbnail`
- `POST /api/metadata/apply`

## Performance Controls
- Duplicate pagination (`limit` max 100 backend, frontend page size 125 request)
- Incremental UI render (`Daha Fazla Yukle`)
- Thumbnail cache reuse (key = path + size + mtime + file size)
- Hover preview delayed show (120ms)

## Operational Notes
- `run_app.bat` python -m uvicorn ile baslatir.
- ffmpeg kurulu degilse video thumbnail üretimi fail edebilir.
- Cache büyümesi normal; periyodik cleanup opsiyonel eklenebilir.

## Constraints
- Windows path/ctime semantics geçerli.
- EXIF write format kisiti: JPEG/JPG/TIFF/WEBP/PNG.
- Video dosyalarda EXIF yazimi yok; sistem zamani set edilir (mode'e bagli).
