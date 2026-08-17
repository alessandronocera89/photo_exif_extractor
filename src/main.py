from __future__ import annotations

import sys
from pathlib import Path

from src.config import ConfigError, load_config
from src.organizer import RunResult, organize_photos


def print_summary(result: RunResult) -> None:
    print(f"Foto analizzate: {result.files_seen}")
    print("Copiate per data:")
    if result.copied_by_date:
        for folder in sorted(result.copied_by_date):
            print(f"  {folder}: {result.copied_by_date[folder]}")
    else:
        print("  (nessuna)")
    print(f"Senza data: {result.no_date_count}")
    print(f"Errori di copia: {len(result.copy_errors)}")
    for error in result.copy_errors:
        print(f"  - {error}")


def main(env_path: Path | None = None) -> int:
    try:
        config = load_config(env_path)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = organize_photos(config)
    print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
