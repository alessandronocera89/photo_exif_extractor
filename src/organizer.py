from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, TextIO

from src.config import Config, list_source_photos, source_folder_name, source_skip_dirs
from src.media import extract_capture_datetime
from src.progress import ProgressBar
from src.timestamps import apply_capture_times

CHUNK_SIZE = 1024 * 1024


@dataclass
class RunResult:
    files_seen: int = 0
    copied_by_date: dict[str, int] = field(default_factory=dict)
    no_date_count: int = 0
    copy_errors: list[str] = field(default_factory=list)


def run_folder_name(prefix: str, source_name: str) -> str:
    return f"{prefix}{source_name}"


def date_folder_name(photo_date: date | None, no_date_folder: str) -> str:
    if photo_date is None:
        return no_date_folder
    return photo_date.strftime("%Y_%m_%d")


def source_relative_path(source_dir: Path, path: Path) -> Path:
    return path.resolve().relative_to(source_dir.resolve())


def source_relative_label(source_dir: Path, path: Path) -> str:
    try:
        return source_relative_path(source_dir, path).as_posix()
    except ValueError:
        return path.name


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


def copy_file(
    src: Path,
    dst: Path,
    on_bytes: Callable[[int], None] | None = None,
) -> None:
    with src.open("rb") as source, dst.open("wb") as destination:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            destination.write(chunk)
            if on_bytes is not None:
                on_bytes(len(chunk))
    shutil.copystat(src, dst)


def _file_weight(path: Path) -> int:
    try:
        return max(path.stat().st_size, 1)
    except OSError:
        return 1


def organize_photos(
    config: Config,
    *,
    show_progress: bool = False,
    progress_stream: TextIO | None = None,
) -> RunResult:
    run_dir = config.output_dir / run_folder_name(
        config.output_prefix,
        source_folder_name(config.source_dir),
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    skip = source_skip_dirs(config.source_dir, config.output_dir, run_dir)
    photos = list_source_photos(config.source_dir, config.extensions, skip)
    weights = [_file_weight(path) for path in photos]
    bar = ProgressBar(
        total_files=len(photos),
        total_bytes=sum(weights),
        enabled=show_progress,
        stream=progress_stream,
    )
    result = RunResult()
    bytes_done = 0
    try:
        for index, source in enumerate(photos):
            result.files_seen += 1
            weight = weights[index]
            label = source_relative_label(config.source_dir, source)
            bar.update(index, bytes_done, label)
            captured = extract_capture_datetime(source)
            if config.group_by == "tree":
                try:
                    relative = source_relative_path(config.source_dir, source)
                except ValueError:
                    relative = Path(source.name)
                if relative.is_absolute() or ".." in relative.parts:
                    dest_dir = run_dir
                    dest_name = source.name
                    folder_key = "."
                else:
                    dest_dir = run_dir.joinpath(*relative.parent.parts)
                    dest_name = relative.name
                    folder_key = relative.parent.as_posix()
            else:
                folder_key = date_folder_name(
                    captured.date() if captured is not None else None,
                    config.no_date_folder,
                )
                dest_dir = run_dir / folder_key
                dest_name = source.name
            destination = unique_destination(dest_dir, dest_name)
            copied = 0

            def on_chunk(n: int, _name: str = label) -> None:
                nonlocal copied, bytes_done
                copied += n
                bytes_done += n
                bar.update(index, bytes_done, _name)

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                copy_file(source, destination, on_chunk)
            except OSError as exc:
                bytes_done += max(weight - copied, 0)
                result.copy_errors.append(f"{label}: {exc}")
                bar.update(index + 1, bytes_done, label)
                continue
            if captured is not None:
                try:
                    apply_capture_times(destination, captured)
                except OSError:
                    pass
            bytes_done += max(weight - copied, 0)
            bar.update(index + 1, bytes_done, label)
            if captured is None:
                result.no_date_count += 1
            else:
                result.copied_by_date[folder_key] = (
                    result.copied_by_date.get(folder_key, 0) + 1
                )
    finally:
        bar.finish()
    return result
