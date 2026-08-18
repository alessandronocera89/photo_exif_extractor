from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

REQUIRED_KEYS = (
    "SOURCE_DIR",
    "OUTPUT_DIR",
    "EXTENSIONS",
    "NO_DATE_FOLDER",
    "OUTPUT_PREFIX",
)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    source_dir: Path
    output_dir: Path
    extensions: frozenset[str]
    no_date_folder: str
    output_prefix: str
    group_by: str = "date"


def parse_folder_name(raw: str, key: str) -> str:
    name = raw.strip()
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        raise ConfigError(f"{key} is not a valid folder name")
    return name


def parse_group_by(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        return "date"
    value = str(raw).strip().lower()
    if value not in {"date", "tree"}:
        raise ConfigError("GROUP_BY must be date or tree")
    return value


def source_folder_name(source_dir: Path) -> str:
    name = source_dir.name
    if not name or name in {".", ".."}:
        raise ConfigError(f"SOURCE_DIR does not have a usable folder name: {source_dir}")
    return name


def _resolved(path: Path) -> Path:
    return path.resolve()


def _casefold_paths() -> bool:
    return sys.platform == "darwin" or os.name == "nt"


def _same_path(left: Path, right: Path) -> bool:
    left_r = _resolved(left)
    right_r = _resolved(right)
    try:
        if left_r.exists() and right_r.exists() and os.path.samefile(left_r, right_r):
            return True
    except OSError:
        pass
    if _casefold_paths():
        return str(left_r).casefold() == str(right_r).casefold()
    return left_r == right_r


def _is_within(path: Path, parent: Path) -> bool:
    if _same_path(path, parent):
        return True
    path_r = _resolved(path)
    parent_r = _resolved(parent)
    try:
        if path_r.is_relative_to(parent_r):
            return True
    except ValueError:
        pass
    if not _casefold_paths():
        return False
    path_key = str(path_r).casefold()
    parent_key = str(parent_r).casefold()
    sep = os.sep
    return path_key.startswith(parent_key + sep) or path_key.startswith(parent_key + "/")


def source_skip_dirs(source_dir: Path, output_dir: Path, run_dir: Path) -> frozenset[Path]:
    skip: set[Path] = set()
    for candidate in (output_dir, run_dir):
        if not _same_path(candidate, source_dir) and _is_within(candidate, source_dir):
            skip.add(_resolved(candidate))
    return frozenset(skip)


def parse_extensions(raw: str) -> frozenset[str]:
    items: list[str] = []
    for part in raw.split(","):
        ext = part.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        items.append(ext)
    if not items:
        raise ConfigError("EXTENSIONS is empty")
    return frozenset(items)


def list_source_photos(
    source_dir: Path,
    extensions: frozenset[str],
    skip_dirs: frozenset[Path] | None = None,
) -> list[Path]:
    source = source_dir.resolve()
    skip = {_resolved(path) for path in (skip_dirs or frozenset())}

    def is_skipped(path: Path) -> bool:
        return any(_is_within(path, item) for item in skip)

    photos: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        current = Path(dirpath).resolve()
        if is_skipped(current):
            dirnames[:] = []
            continue
        dirnames[:] = [
            name for name in dirnames if not is_skipped((current / name).resolve())
        ]
        for filename in filenames:
            path = current / filename
            if path.is_file() and path.suffix.lower() in extensions:
                photos.append(path)
    return sorted(photos, key=lambda p: p.relative_to(source).as_posix().lower())


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def load_config(env_path: Path | None = None) -> Config:
    path = env_path or Path(".env")
    if not path.is_file():
        raise ConfigError(f"Missing .env file: {path}")
    values = dotenv_values(path)
    for key in REQUIRED_KEYS:
        value = values.get(key)
        if value is None or not str(value).strip():
            raise ConfigError(f"Required .env key missing: {key}")

    extensions = parse_extensions(str(values["EXTENSIONS"]))
    source_dir = _resolve_path(str(values["SOURCE_DIR"]))
    output_dir = _resolve_path(str(values["OUTPUT_DIR"]))

    if not source_dir.is_dir():
        raise ConfigError(f"SOURCE_DIR does not exist or is not a folder: {source_dir}")
    source_name = source_folder_name(source_dir)
    output_prefix = parse_folder_name(str(values["OUTPUT_PREFIX"]), "OUTPUT_PREFIX")
    group_by = parse_group_by(values.get("GROUP_BY"))
    run_dir = output_dir / f"{output_prefix}{source_name}"
    photos = list_source_photos(
        source_dir,
        extensions,
        source_skip_dirs(source_dir, output_dir, run_dir),
    )
    if not photos:
        raise ConfigError(
            f"No files with an allowed extension in SOURCE_DIR: {source_dir}"
        )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"OUTPUT_DIR is not writable: {output_dir}") from exc
    if not os.access(output_dir, os.W_OK):
        raise ConfigError(f"OUTPUT_DIR is not writable: {output_dir}")

    return Config(
        source_dir=source_dir,
        output_dir=output_dir,
        extensions=extensions,
        no_date_folder=parse_folder_name(str(values["NO_DATE_FOLDER"]), "NO_DATE_FOLDER"),
        output_prefix=output_prefix,
        group_by=group_by,
    )
