# Photo EXIF Extractor

Copies photos and videos from a folder tree into a run folder. Original files are not moved or changed.

Requires **Node.js** (for `npm run`) and **Python 3.11+**. Formats: `.jpg`, `.jpeg`, `.heic`, `.heif`, `.png`, `.tiff`, `.tif`, `.mp4`, `.mov`, `.m4v`, `.avi`, `.mkv`, `.3gp`.

`SOURCE_DIR` is scanned recursively. The run folder is `OUTPUT_PREFIX` plus the source folder name (so it can sit next to the source on Desktop or Documents). `GROUP_BY=date` flattens by capture date; `GROUP_BY=tree` keeps the source directories.

```
OUTPUT_DIR/extraction_Viaggio_Giappone/   prefix + source folder name
  2024_03_15/                             GROUP_BY=date (capture date)
    IMG_001.jpg
    IMG_001.mov
  no_date/                                no usable capture date
```

With `GROUP_BY=tree` the same run looks like the source tree (`Tokyo/…`, `Kyoto/giorno2/…`) and timestamps on copies still come from EXIF / video metadata.

Photos use EXIF. Videos use container metadata (QuickTime/MP4 tags, MKV `DateUTC`, AVI `IDIT`/`ICRD`). Dates are read from headers without loading the whole file into memory.

Details: [docs/behavior.md](docs/behavior.md)

## Setup

```bash
npm run setup
```

Creates `.venv`, installs Python packages, copies `.env.example` to `.env` if `.env` is missing. Then edit `.env`:

| Key | Role |
|---|---|
| `SOURCE_DIR` | Root folder to scan (includes subfolders) |
| `OUTPUT_DIR` | Parent of the run folder |
| `EXTENSIONS` | Comma-separated list, case-insensitive |
| `NO_DATE_FOLDER` | Required folder name for files with no capture date; ignored when `GROUP_BY=tree` (`no_date`) |
| `OUTPUT_PREFIX` | Run folder prefix (`extraction_`) |
| `GROUP_BY` | Optional. `date` (default) or `tree` |

Paths are absolute, or relative to the working directory. Existing `.env` files are not rewritten by setup; omit `GROUP_BY` to keep date grouping. Run folders from older versions named `extraction_YYYY_MM_DD` are not reused.

## Commands

```bash
npm start          # same as npm run extract
npm test
```
