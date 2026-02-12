# Progress

## Milestones
- [x] Local FastAPI app scaffolding
- [x] Duplicate scan (size + xxhash)
- [x] Duplicate review UI and per-group original selection
- [x] Safe export-only cleanup (no source deletion)
- [x] Date Fixer page (EXIF/Filename/Manual)
- [x] Media preview for images and videos
- [x] Hover large preview with autoplay video
- [x] Cache-backed thumbnail pipeline
- [x] Recommendation engine (`Mark Recommended`)
- [x] Duplicate pagination and incremental load
- [x] Export naming policy: original filename, collision-safe suffix
- [x] Modal UX fix: Cancel + Approve (both pages)
- [x] Processing indicator during long operations
- [x] Skip labeling for unresolved files
- [x] EXIF decision engine with year-mismatch override rule

## Quality Checks Run
- Python syntax checks:
- `python -m py_compile app/main.py app/core/metadata.py`
- Functional smoke checks:
- thumbnail generation (image + video)
- route existence checks
- EXIF decision scenario tests (future EXIF vs filename year, exif-only, filename-only-year)

## Current Status
- Core flows working end-to-end.
- Memory-bank updated to reflect current architecture and rules.

## Known Limitations
- UI integration tests yok (manual verification agirlikli).
- Very large datasets may still need deeper virtualization in frontend.
