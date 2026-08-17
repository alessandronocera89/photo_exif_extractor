# Photo EXIF Extractor

Copies photos and videos from one folder into subfolders named with the capture date. Original files are not moved or changed.

Requires **Node.js** (for `npm run`) and **Python 3.11+**. Formats: `.jpg`, `.jpeg`, `.heic`, `.heif`, `.png`, `.tiff`, `.tif`, `.mp4`, `.mov`, `.m4v`, `.avi`, `.mkv`, `.3gp`.

```
OUTPUT_DIR/extraction_2026_08_17/     run date (local)
  2024_03_15/                         capture date
    IMG_001.jpg
    IMG_001.mov
  no_date/                            no usable capture date
```

Photos use EXIF. Videos use container metadata (QuickTime/MP4 tags, MKV `DateUTC`, AVI `IDIT`/`ICRD`). Dates are read from headers without loading the whole file into memory.

Details: [docs/behavior.md](docs/behavior.md)

## Setup

```bash
npm run setup
```

Creates `.venv`, installs Python packages, copies `.env.example` to `.env` if `.env` is missing. Then edit `.env`:

| Key | Role |
|---|---|
| `SOURCE_DIR` | Input folder (files in the root only, no subfolders) |
| `OUTPUT_DIR` | Parent of the run folder |
| `EXTENSIONS` | Comma-separated list, case-insensitive |
| `NO_DATE_FOLDER` | Subfolder for files with no capture date (`no_date`) |
| `OUTPUT_PREFIX` | Run folder prefix (`extraction_`) |

Paths are absolute, or relative to the working directory. Existing `.env` files are not rewritten by setup; add video extensions there if you already customized it.

## Commands

```bash
npm start          # same as npm run extract
npm test
```
