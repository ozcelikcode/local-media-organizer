# Local Media Organizer

A local-first toolkit for organizing duplicate media and fixing date metadata safely.

This project is designed for privacy-conscious users who want full control over their files. It runs on your machine, works offline, and avoids destructive operations in source folders.

## What It Does

### 1. Duplicate Organizer
- Scans a selected folder and groups duplicate files.
- Lets you mark one file as the original in each group.
- Supports "Mark Recommended" for faster selection.
- Exports selected originals to a target directory.

### 2. Date Fixer
- Processes photos and videos using one of three modes:
  - EXIF mode
  - Filename mode
  - Manual date mode
- Writes permanent metadata updates on exported copies.
- Clearly marks unresolved files as `SKIP`.

## Safety & Privacy Model

This application follows a strict safety model:

- Source files are never deleted.
- Source files are not modified in-place.
- Export files keep original names.
- Name collisions are handled safely using suffixes like `(2)`, `(3)`.
- API access is restricted to localhost.
- Media preview routes are limited to scanned roots.

In short: no cloud upload, no telemetry, no external file sharing.

## Core Rules in EXIF Mode

The current date resolution logic is:

1. EXIF is the primary source.
2. If EXIF year and filename year match, EXIF is kept.
3. If EXIF year is later than filename year, filename date is used.
4. If EXIF is missing, filename date is used when available.
5. If both EXIF and filename date are missing, the file is skipped.

For videos, image EXIF writing is not attempted. File system timestamps are updated instead.

## Requirements

- Python 3.10+
- Windows (primary target)
- `ffmpeg` (required for video thumbnails)

## Installation

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Optional check:

```powershell
ffmpeg -version
```

## Run

### Option A (recommended)

```powershell
run_app.bat
```

### Option B

```powershell
venv\Scripts\python -m uvicorn app.main:app --reload
```

Then open:

- http://127.0.0.1:8000

## Basic Usage

### Duplicate Organizer
1. Enter a source path and run scan.
2. Use manual selection or **Mark Recommended**.
3. Set export destination.
4. Click **Export Selected** and approve.

### Date Fixer
1. Enter a source path and run scan.
2. Choose mode (EXIF / Filename / Manual).
3. Set export destination.
4. Click **Export & Fix Files** and approve.

## API Overview

- `POST /api/scan`
- `GET /api/duplicates_page`
- `POST /api/mark_original/{file_id}`
- `POST /api/recommend_originals`
- `POST /api/commit_cleanup`
- `POST /api/metadata/scan`
- `GET /api/metadata/preview`
- `GET /api/metadata/thumbnail`
- `POST /api/metadata/apply`

## Performance Notes

- Duplicate groups are loaded incrementally.
- Thumbnails are cached on disk.
- Hover preview is optimized for large datasets.

## Troubleshooting

### "EXIF write failed" on video files
That behavior is expected with image EXIF libraries. The app now applies file system timestamp updates for videos instead.

### "Path is not in allowed scanned roots"
Scan the source directory again and retry.

## Screenshots

> Add screenshots in this section before publishing.

### Duplicate Organizer

<!-- Add screenshot here -->

### Date Fixer

<!-- Add screenshot here -->

### Recommendation Flow

<!-- Add screenshot here -->

## License

Choose and add your license before publishing.
