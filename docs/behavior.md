# Behavior

## Input

Files under `SOURCE_DIR` are read recursively, at every nested level. Directory symlinks are not followed. A file is included if its extension is in `EXTENSIONS` (compared in lowercase). Photos and videos share the same run.

If `OUTPUT_DIR` or the run folder is inside `SOURCE_DIR` (a proper subdirectory, not `SOURCE_DIR` itself), that subtree is skipped so a later run does not re-copy previous output. On macOS and Windows the skip also matches the same folder when the path spelling differs only in case.

If `SOURCE_DIR` is missing, is not a folder, has no usable folder name, or has no matching files, the process exits with code 1.

## Output

Run folder: `OUTPUT_DIR` / `OUTPUT_PREFIX` + the source folder name.

Example with defaults and `SOURCE_DIR=…/Viaggio_Giappone`: `OUTPUT_DIR/extraction_Viaggio_Giappone`.

If source and output share a parent (Desktop, Documents), the prefix keeps the run folder distinct from the source folder.

A second run on the same source uses the same run folder. Files already there are not deleted. Older run folders named with the local run date (`extraction_YYYY_MM_DD`) are not reused.

`GROUP_BY` (optional, default `date`, case-insensitive):

### `GROUP_BY=date`

Files are **copied** into:

- `YYYY_MM_DD` from the capture date, or
- `NO_DATE_FOLDER` (`no_date` by default) if there is no usable capture date

A photo and a video from the same day go in the same date folder, including files that lived in different source subfolders. Nested source paths are flattened; the destination name is the original basename.

### `GROUP_BY=tree`

The path relative to `SOURCE_DIR` is mirrored under the run folder. There are no date folders. `NO_DATE_FOLDER` is ignored. Empty source directories are not recreated. A file with no capture date stays at its mirrored path; the copy keeps the source timestamps.

If the destination name exists: `photo.jpg`, then `photo_1.jpg`, `photo_2.jpg`, and so on.

## Capture date

### Photos

Tags are tried in this order:

1. `DateTimeOriginal`
2. `DateTimeDigitized`
3. `DateTime`

### Videos

| Format | Order |
|---|---|
| MP4 / MOV / M4V / 3GP | `com.apple.quicktime.creationdate` from QuickTime `mdta` keys or iTunes tags → `©day` → movie header `creation_time` (`mvhd`; sentinels `0` and `1` are skipped). iPhone `.mov` files store the capture date in `moov/meta` (`mdta`); `mvhd` is often the export/backup time and must not win. |
| MKV | `DateUTC` (nanoseconds since 2001-01-01 UTC) |
| AVI | `IDIT` → `ICRD` (only inside `LIST INFO`; `movi` is skipped) |

Naive values are treated as local wall time, with no timezone conversion. Values with an offset keep the clock as written and drop the offset. `mvhd` and MKV `DateUTC` are UTC instants converted to the machine local timezone. A `©day` value that is only a year is invalid. AVI `IDIT` ctime strings are parsed with English month names, independent of the OS locale.

The date part names the folder when `GROUP_BY=date`. The time part is used for file timestamps on copies.

A missing tag, an invalid datetime, or a file that cannot be opened has no usable capture date: with `GROUP_BY=date` it goes to `NO_DATE_FOLDER`; with `GROUP_BY=tree` it stays at the mirrored path.

Metadata is read by seeking through container headers. Media payloads (`mdat`, Matroska Clusters, AVI `movi`) are skipped, so large videos are not loaded into memory to get the date.

## File timestamps on copies

After a successful copy, if a capture datetime was found:

- modification time is set to that datetime on all platforms
- on macOS and Windows, creation time is set to the same datetime
- on Linux, creation/birth time is not changed (not reliably writable)

Originals are not changed. Copies without a capture datetime keep the timestamps of the source file.

## Progress

If stderr is a terminal, a progress line is printed.

The total is the sum of the sizes of the files to copy. The bar moves as bytes are written (1 MB chunks) and when each file finishes. File count is shown as `done/total`. The current file is the path relative to `SOURCE_DIR`; names longer than 40 characters keep the end (`.../giorno2/IMG_002.mov`).

## Errors

These stop the run (exit code 1): missing `.env`, missing required key, invalid `GROUP_BY`, unreadable `SOURCE_DIR`, unusable `SOURCE_DIR` name, no matching files, unwritable `OUTPUT_DIR`, failure to create the run folder.

A copy or mkdir failure on one file is recorded in the summary (`Copy errors`) using the path relative to `SOURCE_DIR`. The other files continue.

`NO_DATE_FOLDER` and `OUTPUT_PREFIX` must be a single folder name: no `/`, `\`, `.`, or `..`. `GROUP_BY` must be `date` or `tree` when set.
