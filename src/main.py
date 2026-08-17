from __future__ import annotations

import sys
from pathlib import Path

from src.config import ConfigError, load_config
from src.organizer import RunResult, organize_photos


def print_summary(result: RunResult) -> None:
    print(f"Photos scanned: {result.files_seen}")
    print("Copied by date:")
    if result.copied_by_date:
        for folder in sorted(result.copied_by_date):
            print(f"  {folder}: {result.copied_by_date[folder]}")
    else:
        print("  (none)")
    print(f"No date: {result.no_date_count}")
    print(f"Copy errors: {len(result.copy_errors)}")
    for error in result.copy_errors:
        print(f"  - {error}")


def main(env_path: Path | None = None) -> int:
    try:
        config = load_config(env_path)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        result = organize_photos(config, show_progress=sys.stderr.isatty())
    except OSError as exc:
        print(f"Could not create the extraction folder: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
