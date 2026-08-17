# Behavior

## Input

Only files in the root of `SOURCE_DIR` are read. Subfolders are ignored. A file is included if its extension is in `EXTENSIONS` (compared in lowercase). Photos and videos share the same run.

If `SOURCE_DIR` is missing, is not a folder, or has no matching files, the process exits with code 1.

## Output

Run folder: `OUTPUT_DIR` / `OUTPUT_PREFIX` + local date of the run (`YYYY_MM_DD`).

Example with defaults: `OUTPUT_DIR/extraction_2026_08_17`.

Files are **copied** into:

- `YYYY_MM_DD` from the capture date, or
- `NO_DATE_FOLDER` (`no_date` by default) if there is no usable capture date

A photo and a video from the same day go in the same date folder. A second run on the same calendar day uses the same run folder. Files already there are not deleted.

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

The date part names the folder. The time part is used for file timestamps.

A missing tag, an invalid datetime, or a file that cannot be opened goes to `NO_DATE_FOLDER`.

Metadata is read by seeking through container headers. Media payloads (`mdat`, Matroska Clusters, AVI `movi`) are skipped, so large videos are not loaded into memory to get the date.

## File timestamps on copies

After a successful copy, if a capture datetime was found:

- modification time is set to that datetime on all platforms
- on macOS and Windows, creation time is set to the same datetime
- on Linux, creation/birth time is not changed (not reliably writable)

Originals are not changed. Copies without a capture datetime keep the timestamps of the source file.

## Progress

If stderr is a terminal, a progress line is printed.

The total is the sum of the sizes of the files to copy. The bar moves as bytes are written (1 MB chunks) and when each file finishes. File count is shown as `done/total`.

## Errors

These stop the run (exit code 1): missing `.env`, missing required key, unreadable `SOURCE_DIR`, no matching files, unwritable `OUTPUT_DIR`, failure to create the run folder.

A copy or mkdir failure on one file is recorded in the summary (`Copy errors`). The other files continue.

`NO_DATE_FOLDER` and `OUTPUT_PREFIX` must be a single folder name: no `/`, `\`, `.`, or `..`.
