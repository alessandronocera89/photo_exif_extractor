from __future__ import annotations

import os
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
        raise ConfigError("EXTENSIONS è vuoto")
    return frozenset(items)


def list_source_photos(source_dir: Path, extensions: frozenset[str]) -> list[Path]:
    photos = [
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    ]
    return sorted(photos, key=lambda p: p.name.lower())


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def load_config(env_path: Path | None = None) -> Config:
    path = env_path or Path(".env")
    if not path.is_file():
        raise ConfigError(f"File .env mancante: {path}")
    values = dotenv_values(path)
    for key in REQUIRED_KEYS:
        value = values.get(key)
        if value is None or not str(value).strip():
            raise ConfigError(f"Chiave obbligatoria mancante nel .env: {key}")

    extensions = parse_extensions(str(values["EXTENSIONS"]))
    source_dir = _resolve_path(str(values["SOURCE_DIR"]))
    output_dir = _resolve_path(str(values["OUTPUT_DIR"]))

    if not source_dir.is_dir():
        raise ConfigError(f"SOURCE_DIR inesistente o non è una cartella: {source_dir}")

    photos = list_source_photos(source_dir, extensions)
    if not photos:
        raise ConfigError(
            f"Nessuna foto con estensione ammessa in SOURCE_DIR: {source_dir}"
        )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"OUTPUT_DIR non scrivibile: {output_dir}") from exc
    if not os.access(output_dir, os.W_OK):
        raise ConfigError(f"OUTPUT_DIR non scrivibile: {output_dir}")

    return Config(
        source_dir=source_dir,
        output_dir=output_dir,
        extensions=extensions,
        no_date_folder=str(values["NO_DATE_FOLDER"]).strip(),
        output_prefix=str(values["OUTPUT_PREFIX"]).strip(),
    )
