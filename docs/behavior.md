# Behavior

## Input

Only files in the root of `SOURCE_DIR` are read. Subfolders are ignored. A file is included if its extension is in `EXTENSIONS` (compared in lowercase).

If `SOURCE_DIR` is missing, is not a folder, or has no matching files, the process exits with code 1.

## Output

Run folder: `OUTPUT_DIR` / `OUTPUT_PREFIX` + local date of the run (`YYYY_MM_DD`).

Example with defaults: `OUTPUT_DIR/extraction_2026_08_17`.

Photos are **copied** into:

- `YYYY_MM_DD` from the EXIF date, or
- `NO_DATE_FOLDER` (`no_date` by default) if there is no usable EXIF date

A second run on the same calendar day uses the same run folder. Files already there are not deleted.

If the destination name exists: `photo.jpg`, then `photo_1.jpg`, `photo_2.jpg`, and so on.

## EXIF date

Tags are tried in this order:

1. `DateTimeOriginal`
2. `DateTimeDigitized`
3. `DateTime`

The date part names the folder. The time part is used for file timestamps. Values are treated as local time, with no timezone conversion.

A missing tag, an invalid datetime, or a file that cannot be opened goes to `NO_DATE_FOLDER`.

## File timestamps on copies

After a successful copy, if an EXIF datetime was found:

- modification time is set to that datetime
- on macOS, creation time is set to the same datetime

Originals are not changed. Copies without EXIF keep the timestamps of the source file.

## Progress

If stderr is a terminal, a progress line is printed.

The total is the sum of the sizes of the files to copy. The bar moves as bytes are written (1 MB chunks) and when each file finishes. File count is shown as `done/total`.

## Errors

These stop the run (exit code 1): missing `.env`, missing required key, unreadable `SOURCE_DIR`, no matching photos, unwritable `OUTPUT_DIR`, failure to create the run folder.

A copy or mkdir failure on one file is recorded in the summary (`Copy errors`). The other files continue.

`NO_DATE_FOLDER` and `OUTPUT_PREFIX` must be a single folder name: no `/`, `\`, `.`, or `..`.
