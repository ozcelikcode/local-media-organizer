# System Patterns

## Runtime Architecture
- Backend: FastAPI (`app/main.py`)
- Services: Scanner (`app/core/scanner.py`), Metadata (`app/core/metadata.py`)
- DB: SQLite + SQLAlchemy models (`app/db/models.py`)
- Frontend: static Alpine.js pages (`app/static/index.html`, `app/static/date_fixer.html`)

## Key Backend Patterns
1. Duplicate Scan Pipeline
- `os.walk` ile boyut map
- ayni boyut gruplarinda xxhash
- sadece hash çakisanlar duplicate group

2. Paged Read Pattern
- `/api/duplicates_page?offset&limit`
- frontend incremental append
- total + selected_originals sayaçlari döner

3. Recommendation Pattern
- `/api/recommend_originals`
- grup içi skor fonksiyonu ile tek aday (`_choose_recommended_file`)
- her grupta tek `is_original = true`

4. Media Preview Pattern
- `/api/metadata/preview` raw media serve
- `/api/metadata/thumbnail` cache'li jpeg thumbnail
- video thumbnail ffmpeg ile üretilir
- cache: `memory-bank/thumb-cache`

5. Export Naming Pattern
- Orijinal dosya adi korunur
- çakisma halinde `name (2).ext` formati
- overwrite yapilmaz

6. EXIF Decision Pattern
- `resolve_exif_mode_date`:
- exif+filename year match -> exif
- exif year > filename year -> filename override
- exif only -> exif
- filename only -> filename
- none -> unresolved/skip

## Frontend Interaction Patterns
- Reusable modal state: `showApprove`, `confirmFn`
- Approve/Cancel deterministic action
- Processing state gate (`processing` flag)
- Hover preview with short delay (perf)

## Data Integrity Pattern
- Source mutate edilmez
- Kalici metadata degisikligi export copy üzerinde yapilir
- Basarisiz dosyalar per-file error listesine yazilir
