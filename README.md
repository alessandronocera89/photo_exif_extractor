# Photo EXIF Extractor

Copies photos from one folder into subfolders named with the EXIF capture date. Original files are not moved or changed.

Requires **Node.js** (for `npm run`) and **Python 3.11+**. Formats: `.jpg`, `.jpeg`, `.heic`, `.heif`, `.png`, `.tiff`, `.tif`.

```
OUTPUT_DIR/extraction_2026_08_17/     run date (local)
  2024_03_15/                         EXIF date
    IMG_001.jpg
  no_date/                            no usable EXIF date
```

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
| `NO_DATE_FOLDER` | Subfolder for photos with no EXIF date (`no_date`) |
| `OUTPUT_PREFIX` | Run folder prefix (`extraction_`) |

Paths are absolute, or relative to the working directory.

## Commands

```bash
npm start          # same as npm run extract
npm test
```
