# Photo EXIF Extractor — Design

Date: 2026-08-17

## Goal

A command-line Python tool that reads photos from a single source folder, extracts the capture date from EXIF, and copies them into date-named subfolders. Original files are never moved or modified.

## Decisions

- Language: Python
- EXIF: Pillow + pillow-heif (no ExifTool binary)
- Config: `.env` via python-dotenv
- Missing EXIF date: copy into `senza_data`
- Source scan: non-recursive (root files only)
- Formats: JPEG, HEIC/HEIF, PNG, TIFF
- Name collisions: auto-suffix `_1`, `_2`, …
- Copy, do not move

## Layout

```
photo_exif_extractor/
  .env
  .env.example
  requirements.txt
  README.md
  src/
    __init__.py
    config.py
    exif.py
    organizer.py
    main.py
  tests/
```

## Runtime flow

1. Load `.env` from the working directory and validate required keys.
2. Confirm `SOURCE_DIR` exists and contains at least one file with an allowed extension.
3. Create `{OUTPUT_DIR}/{OUTPUT_PREFIX}{YYYY_MM_DD}` using the local date of the run (default: `estrazione_del_2026_08_17`).
4. For each allowed file in the source root:
   - Extract EXIF date → folder `YYYY_MM_DD`, or `{NO_DATE_FOLDER}` if missing/invalid.
   - Copy with `shutil.copy2` (preserves timestamps; does not modify the original). If the destination filename already exists, append `_1`, `_2`, …
5. Print a summary: files seen, copied per date, sent to `{NO_DATE_FOLDER}`, copy errors.

If the run folder already exists (second run on the same day), reuse it and add files. Do not delete existing copies.

## Configuration

`.env` keys:

| Key | Required | Meaning |
|---|---|---|
| `SOURCE_DIR` | yes | Folder with the photos (root only) |
| `OUTPUT_DIR` | yes | Parent folder for extraction runs |
| `EXTENSIONS` | yes | Comma-separated list, case-insensitive |
| `NO_DATE_FOLDER` | yes | Folder name for photos with no usable EXIF date |
| `OUTPUT_PREFIX` | yes | Prefix for the run folder (`estrazione_del_`) |

Paths may be absolute or relative. Relative paths resolve against the process working directory (the folder from which the script is launched). Missing `.env`, missing required keys, invalid `SOURCE_DIR`, no matching photos, or unwritable `OUTPUT_DIR` abort the run with a non-zero exit code.

Run from the project root: `python -m src.main`

`.env` is not versioned. `.env.example` ships with placeholder paths.

Default `EXTENSIONS`: `.jpg,.jpeg,.heic,.heif,.png,.tiff,.tif`

## EXIF date rules

Try tags in this order:

1. `DateTimeOriginal`
2. `DateTimeDigitized`
3. `DateTime`

Use the date part only (`YYYY_MM_DD`). Time is ignored. Photos from the same calendar day go in the same folder.

JPEG/PNG/TIFF: Pillow. HEIC/HEIF: register `pillow-heif`, then the same Pillow path.

If no tag exists, the value is not a valid datetime, or the file cannot be read: treat as no date and copy into `{NO_DATE_FOLDER}`. A per-file failure does not stop the run. EXIF timestamps are interpreted as naive local datetimes (no timezone conversion).

## Copy collisions

Given destination `foto.jpg` already present:

- first extra copy → `foto_1.jpg`
- next → `foto_2.jpg`
- and so on, before the extension

## Errors

Hard stop (exit ≠ 0):

- `.env` missing or required key missing
- `SOURCE_DIR` missing or has no allowed photos
- `OUTPUT_DIR` not writable

Continue and report:

- corrupt file / unreadable EXIF → `{NO_DATE_FOLDER}`
- copy failure for one file → skip that file, count it in the summary

No dry-run. No log file. Terminal summary only.

## Tests

`pytest`, with in-memory/generated fixtures (minimal JPEG with fake EXIF). No real photos in the repo.

Cover:

- grouping by EXIF date into `YYYY_MM_DD`
- no date → `senza_data`
- name collision → `_1`, `_2`
- disallowed extensions ignored
- empty source → startup error

No CI in this version.

## Out of scope

- Recursive source folders
- RAW formats
- Moving or deleting originals
- GUI
- Dry-run flag
- File logging
- CI
