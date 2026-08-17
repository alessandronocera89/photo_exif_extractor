from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.config import Config, list_source_photos
from src.exif import extract_photo_date


@dataclass
class RunResult:
    files_seen: int = 0
    copied_by_date: dict[str, int] = field(default_factory=dict)
    no_date_count: int = 0
    copy_errors: list[str] = field(default_factory=list)


def run_folder_name(prefix: str, run_date: date) -> str:
    return f"{prefix}{run_date.strftime('%Y_%m_%d')}"


def date_folder_name(photo_date: date | None, no_date_folder: str) -> str:
    if photo_date is None:
        return no_date_folder
    return photo_date.strftime("%Y_%m_%d")


def unique_destination(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 1
    while True:
        candidate = dest_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def organize_photos(config: Config, run_date: date | None = None) -> RunResult:
    today = run_date or date.today()
    run_dir = config.output_dir / run_folder_name(config.output_prefix, today)
    run_dir.mkdir(parents=True, exist_ok=True)
    result = RunResult()
    for source in list_source_photos(config.source_dir, config.extensions):
        result.files_seen += 1
        folder = date_folder_name(
            extract_photo_date(source), config.no_date_folder
        )
        dest_dir = run_dir / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(dest_dir, source.name)
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            result.copy_errors.append(f"{source.name}: {exc}")
            continue
        if folder == config.no_date_folder:
            result.no_date_count += 1
        else:
            result.copied_by_date[folder] = result.copied_by_date.get(folder, 0) + 1
    return result
