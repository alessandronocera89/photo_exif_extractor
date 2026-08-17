# Photo EXIF Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that copies photos from one folder into `estrazione_del_YYYY_MM_DD / YYYY_MM_DD` (or `senza_data`) using EXIF capture dates.

**Architecture:** Four small modules. `config.py` loads `.env` and validates paths. `exif.py` returns a `date` or `None` from a photo. `organizer.py` creates the run folder and copies files with collision suffixes. `main.py` wires them and prints an Italian summary.

**Tech Stack:** Python 3.11+, python-dotenv, Pillow, pillow-heif, piexif (test fixtures only), pytest

## Global Constraints

- Python 3.11+
- Copy with `shutil.copy2`; never move or modify originals
- Source scan is non-recursive (root files only)
- Allowed formats come from `.env` `EXTENSIONS` (example: `.jpg,.jpeg,.heic,.heif,.png,.tiff,.tif`)
- Date folders use `YYYY_MM_DD` (underscores); run folder is `{OUTPUT_PREFIX}{YYYY_MM_DD}`
- Missing/invalid EXIF → `{NO_DATE_FOLDER}` (example: `senza_data`)
- EXIF tag order: `DateTimeOriginal`, then `DateTimeDigitized`, then `DateTime`
- EXIF timestamps are naive local datetimes (no timezone conversion)
- Name collisions: `foto.jpg` → `foto_1.jpg` → `foto_2.jpg`
- Relative paths resolve against process cwd
- `.env` is required and not versioned; ship `.env.example`
- User-facing CLI messages in Italian
- No dry-run, no log file, no CI, no GUI, no RAW, no recursion
- Run command: `python -m src.main` from project root

## File map

| File | Responsibility |
|---|---|
| `src/__init__.py` | Package marker |
| `src/config.py` | `Config`, `ConfigError`, `load_config`, `list_source_photos` |
| `src/exif.py` | `parse_exif_datetime`, `extract_photo_date` |
| `src/organizer.py` | `RunResult`, `unique_destination`, `run_folder_name`, `date_folder_name`, `organize_photos` |
| `src/main.py` | `print_summary`, `main` |
| `tests/helpers.py` | JPEG fixture writer (piexif + Pillow) |
| `tests/test_config.py` | Config validation |
| `tests/test_exif.py` | EXIF parsing and extraction |
| `tests/test_organizer.py` | Copy, grouping, collisions |
| `tests/test_main.py` | CLI exit codes and summary |
| `.env.example` | Placeholder config |
| `requirements.txt` | Runtime + test deps |
| `pytest.ini` | `pythonpath = .` |
| `.gitignore` | `.env`, venv, caches |
| `README.md` | Setup and run |

---

### Task 1: Config loader

**Files:**
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/test_config.py`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `class ConfigError(Exception)`
  - `@dataclass(frozen=True) class Config` with `source_dir: Path`, `output_dir: Path`, `extensions: frozenset[str]`, `no_date_folder: str`, `output_prefix: str`
  - `def parse_extensions(raw: str) -> frozenset[str]`
  - `def list_source_photos(source_dir: Path, extensions: frozenset[str]) -> list[Path]`
  - `def load_config(env_path: Path | None = None) -> Config`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

import pytest

from src.config import ConfigError, list_source_photos, load_config, parse_extensions


def _write_env(path: Path, **values: str) -> Path:
    env = path / ".env"
    lines = [f"{key}={value}" for key, value in values.items()]
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env


def _valid_values(tmp_path: Path) -> dict[str, str]:
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    (source / "a.jpg").write_bytes(b"x")
    output.mkdir()
    return {
        "SOURCE_DIR": str(source),
        "OUTPUT_DIR": str(output),
        "EXTENSIONS": ".jpg,.jpeg,.heic,.heif,.png,.tiff,.tif",
        "NO_DATE_FOLDER": "senza_data",
        "OUTPUT_PREFIX": "estrazione_del_",
    }


def test_parse_extensions_normalizes_case_and_dot():
    assert parse_extensions(".JPG, jpeg, PNG") == frozenset({".jpg", ".jpeg", ".png"})


def test_parse_extensions_empty_raises():
    with pytest.raises(ConfigError, match="EXTENSIONS"):
        parse_extensions(" , ")


def test_list_source_photos_root_only_and_ignores_other_extensions(tmp_path: Path):
    source = tmp_path / "foto"
    nested = source / "sub"
    nested.mkdir(parents=True)
    (source / "a.jpg").write_bytes(b"x")
    (source / "b.TXT").write_bytes(b"x")
    (source / "c.HEIC").write_bytes(b"x")
    (nested / "d.jpg").write_bytes(b"x")
    photos = list_source_photos(source, frozenset({".jpg", ".heic"}))
    names = {p.name for p in photos}
    assert names == {"a.jpg", "c.HEIC"}


def test_load_config_success(tmp_path: Path):
    env = _write_env(tmp_path, **_valid_values(tmp_path))
    config = load_config(env)
    assert config.source_dir.is_dir()
    assert config.output_dir.is_dir()
    assert ".jpg" in config.extensions
    assert ".heic" in config.extensions
    assert config.no_date_folder == "senza_data"
    assert config.output_prefix == "estrazione_del_"


def test_load_config_missing_file(tmp_path: Path):
    with pytest.raises(ConfigError, match=".env"):
        load_config(tmp_path / "missing.env")


def test_load_config_missing_key(tmp_path: Path):
    values = _valid_values(tmp_path)
    del values["SOURCE_DIR"]
    env = _write_env(tmp_path, **values)
    with pytest.raises(ConfigError, match="SOURCE_DIR"):
        load_config(env)


def test_load_config_missing_source_dir(tmp_path: Path):
    values = _valid_values(tmp_path)
    values["SOURCE_DIR"] = str(tmp_path / "does-not-exist")
    env = _write_env(tmp_path, **values)
    with pytest.raises(ConfigError, match="SOURCE_DIR"):
        load_config(env)


def test_load_config_empty_source(tmp_path: Path):
    values = _valid_values(tmp_path)
    source = tmp_path / "foto"
    for child in source.iterdir():
        child.unlink()
    env = _write_env(tmp_path, **values)
    with pytest.raises(ConfigError, match="Nessuna foto"):
        load_config(env)


def test_load_config_creates_output_dir_if_missing(tmp_path: Path):
    values = _valid_values(tmp_path)
    output = tmp_path / "new-out"
    values["OUTPUT_DIR"] = str(output)
    env = _write_env(tmp_path, **values)
    config = load_config(env)
    assert config.output_dir.is_dir()


def test_load_config_unwritable_output_dir(tmp_path: Path):
    values = _valid_values(tmp_path)
    output = tmp_path / "locked-out"
    output.mkdir()
    output.chmod(0o555)
    values["OUTPUT_DIR"] = str(output)
    env = _write_env(tmp_path, **values)
    try:
        with pytest.raises(ConfigError, match="OUTPUT_DIR"):
            load_config(env)
    finally:
        output.chmod(0o755)


def test_load_config_relative_paths_use_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    source = Path("foto")
    output = Path("out")
    source.mkdir()
    output.mkdir()
    (source / "a.jpg").write_bytes(b"x")
    env = _write_env(
        tmp_path,
        SOURCE_DIR="foto",
        OUTPUT_DIR="out",
        EXTENSIONS=".jpg",
        NO_DATE_FOLDER="senza_data",
        OUTPUT_PREFIX="estrazione_del_",
    )
    config = load_config(env)
    assert config.source_dir == (tmp_path / "foto").resolve()
    assert config.output_dir == (tmp_path / "out").resolve()
```

Also create `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

And `requirements.txt`:

```
python-dotenv>=1.0
Pillow>=10.0
pillow-heif>=0.16
piexif>=1.1
pytest>=8.0
```

And `.gitignore`:

```
.env
.venv/
__pycache__/
.pytest_cache/
*.pyc
```

And `.env.example`:

```
SOURCE_DIR=/percorso/cartella/foto
OUTPUT_DIR=/percorso/dove/salvare
EXTENSIONS=.jpg,.jpeg,.heic,.heif,.png,.tiff,.tif
NO_DATE_FOLDER=senza_data
OUTPUT_PREFIX=estrazione_del_
```

And empty `src/__init__.py`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pip install -r requirements.txt
pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'` (or import error on `load_config`).

- [ ] **Step 3: Write minimal implementation**

Create `src/config.py`:

```python
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
        raise ConfigError("EXTENSIONS is empty")
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: PASS (all tests in `test_config.py`).

- [ ] **Step 5: Commit**

```bash
git init
git add src/__init__.py src/config.py tests/test_config.py .env.example requirements.txt pytest.ini .gitignore
git commit -m "$(cat <<'EOF'
feat: load and validate photo extractor .env config

EOF
)"
```

If git is not initialized or user asked not to commit, skip this step and continue.

---

### Task 2: EXIF date extraction

**Files:**
- Create: `src/exif.py`
- Create: `tests/helpers.py`
- Create: `tests/test_exif.py`

**Interfaces:**
- Consumes: nothing from Task 1 at runtime (tests may use `tmp_path` only)
- Produces:
  - `def parse_exif_datetime(value: object) -> date | None`
  - `def extract_photo_date(path: Path) -> date | None`
  - Tag priority inside `extract_photo_date`: DateTimeOriginal (36867), DateTimeDigitized (36868), DateTime (306)

- [ ] **Step 1: Write the failing tests**

Create `tests/helpers.py`:

```python
from pathlib import Path

import piexif
from PIL import Image


def make_jpeg(
    path: Path,
    datetime_original: str | None = None,
    datetime_digitized: str | None = None,
    datetime: str | None = None,
) -> Path:
    image = Image.new("RGB", (8, 8), "red")
    zeroth: dict[int, bytes] = {}
    exif_ifd: dict[int, bytes] = {}
    if datetime:
        zeroth[piexif.ImageIFD.DateTime] = datetime.encode("utf-8")
    if datetime_original:
        exif_ifd[piexif.ExifIFD.DateTimeOriginal] = datetime_original.encode("utf-8")
    if datetime_digitized:
        exif_ifd[piexif.ExifIFD.DateTimeDigitized] = datetime_digitized.encode("utf-8")
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif_ifd})
    image.save(path, "JPEG", exif=exif_bytes)
    return path
```

Create `tests/test_exif.py`:

```python
from datetime import date
from pathlib import Path

from src.exif import extract_photo_date, parse_exif_datetime
from tests.helpers import make_jpeg


def test_parse_exif_datetime_standard():
    assert parse_exif_datetime("2024:03:15 14:30:00") == date(2024, 3, 15)


def test_parse_exif_datetime_date_only():
    assert parse_exif_datetime("2024:03:15") == date(2024, 3, 15)


def test_parse_exif_datetime_hyphens():
    assert parse_exif_datetime("2024-03-15 14:30:00") == date(2024, 3, 15)


def test_parse_exif_datetime_bytes():
    assert parse_exif_datetime(b"2024:03:15 14:30:00") == date(2024, 3, 15)


def test_parse_exif_datetime_invalid():
    assert parse_exif_datetime("not-a-date") is None
    assert parse_exif_datetime("") is None
    assert parse_exif_datetime(None) is None


def test_extract_prefers_datetime_original(tmp_path: Path):
    path = make_jpeg(
        tmp_path / "a.jpg",
        datetime_original="2024:01:10 09:00:00",
        datetime_digitized="2024:02:10 09:00:00",
        datetime="2024:03:10 09:00:00",
    )
    assert extract_photo_date(path) == date(2024, 1, 10)


def test_extract_falls_back_to_digitized(tmp_path: Path):
    path = make_jpeg(
        tmp_path / "a.jpg",
        datetime_digitized="2024:02:10 09:00:00",
        datetime="2024:03:10 09:00:00",
    )
    assert extract_photo_date(path) == date(2024, 2, 10)


def test_extract_falls_back_to_datetime(tmp_path: Path):
    path = make_jpeg(tmp_path / "a.jpg", datetime="2024:03:10 09:00:00")
    assert extract_photo_date(path) == date(2024, 3, 10)


def test_extract_no_exif_returns_none(tmp_path: Path):
    path = tmp_path / "plain.jpg"
    from PIL import Image

    Image.new("RGB", (8, 8), "blue").save(path, "JPEG")
    assert extract_photo_date(path) is None


def test_extract_corrupt_file_returns_none(tmp_path: Path):
    path = tmp_path / "broken.jpg"
    path.write_bytes(b"not an image")
    assert extract_photo_date(path) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_exif.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.exif'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/exif.py`:

```python
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

DATETIME_ORIGINAL = 36867
DATETIME_DIGITIZED = 36868
DATETIME = 306
TAG_ORDER = (DATETIME_ORIGINAL, DATETIME_DIGITIZED, DATETIME)


def parse_exif_datetime(value: object) -> date | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    date_part = text.split()[0]
    for fmt in ("%Y:%m:%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def _exif_get(exif: Image.Exif, tag: int) -> object | None:
    if tag in exif:
        return exif.get(tag)
    try:
        nested = exif.get_ifd(0x8769)
    except Exception:
        nested = {}
    if tag in nested:
        return nested.get(tag)
    return None


def extract_photo_date(path: Path) -> date | None:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return None
            for tag in TAG_ORDER:
                parsed = parse_exif_datetime(_exif_get(exif, tag))
                if parsed is not None:
                    return parsed
            return None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_exif.py tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/exif.py tests/helpers.py tests/test_exif.py
git commit -m "$(cat <<'EOF'
feat: extract capture date from photo EXIF tags

EOF
)"
```

---

### Task 3: Organizer (folders, copy, collisions)

**Files:**
- Create: `src/organizer.py`
- Create: `tests/test_organizer.py`

**Interfaces:**
- Consumes:
  - `Config` from `src.config`
  - `list_source_photos(source_dir, extensions)` from `src.config`
  - `extract_photo_date(path) -> date | None` from `src.exif`
- Produces:
  - `@dataclass class RunResult` with `files_seen: int`, `copied_by_date: dict[str, int]`, `no_date_count: int`, `copy_errors: list[str]`
  - `def run_folder_name(prefix: str, run_date: date) -> str`
  - `def date_folder_name(photo_date: date | None, no_date_folder: str) -> str`
  - `def unique_destination(dest_dir: Path, filename: str) -> Path`
  - `def organize_photos(config: Config, run_date: date | None = None) -> RunResult`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_organizer.py`:

```python
from datetime import date
from pathlib import Path

from PIL import Image

from src.config import Config
from src.organizer import (
    date_folder_name,
    organize_photos,
    run_folder_name,
    unique_destination,
)
from tests.helpers import make_jpeg


def _config(tmp_path: Path, extensions: frozenset[str] | None = None) -> Config:
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    return Config(
        source_dir=source,
        output_dir=output,
        extensions=extensions or frozenset({".jpg", ".jpeg", ".heic", ".png", ".tif"}),
        no_date_folder="senza_data",
        output_prefix="estrazione_del_",
    )


def test_run_folder_name():
    assert run_folder_name("estrazione_del_", date(2026, 8, 17)) == "estrazione_del_2026_08_17"


def test_date_folder_name():
    assert date_folder_name(date(2024, 3, 15), "senza_data") == "2024_03_15"
    assert date_folder_name(None, "senza_data") == "senza_data"


def test_unique_destination_suffixes(tmp_path: Path):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "foto.jpg").write_bytes(b"a")
    first = unique_destination(dest, "foto.jpg")
    first.write_bytes(b"b")
    second = unique_destination(dest, "foto.jpg")
    assert first.name == "foto_1.jpg"
    assert second.name == "foto_2.jpg"


def test_groups_by_exif_date(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 10:00:00")
    make_jpeg(config.source_dir / "b.jpg", datetime_original="2024:03:15 18:00:00")
    make_jpeg(config.source_dir / "c.jpg", datetime_original="2024:03:16 08:00:00")
    result = organize_photos(config, run_date=date(2026, 8, 17))
    run_dir = config.output_dir / "estrazione_del_2026_08_17"
    assert (run_dir / "2024_03_15" / "a.jpg").is_file()
    assert (run_dir / "2024_03_15" / "b.jpg").is_file()
    assert (run_dir / "2024_03_16" / "c.jpg").is_file()
    assert result.files_seen == 3
    assert result.copied_by_date == {"2024_03_15": 2, "2024_03_16": 1}
    assert result.no_date_count == 0
    assert (config.source_dir / "a.jpg").is_file()


def test_no_date_goes_to_senza_data(tmp_path: Path):
    config = _config(tmp_path)
    Image.new("RGB", (8, 8), "blue").save(config.source_dir / "plain.jpg", "JPEG")
    result = organize_photos(config, run_date=date(2026, 8, 17))
    dest = config.output_dir / "estrazione_del_2026_08_17" / "senza_data" / "plain.jpg"
    assert dest.is_file()
    assert result.no_date_count == 1
    assert result.copied_by_date == {}


def test_name_collision_renames(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "foto.jpg", datetime_original="2024:03:15 10:00:00")
    organize_photos(config, run_date=date(2026, 8, 17))
    make_jpeg(config.source_dir / "foto.jpg", datetime_original="2024:03:15 11:00:00")
    organize_photos(config, run_date=date(2026, 8, 17))
    folder = config.output_dir / "estrazione_del_2026_08_17" / "2024_03_15"
    assert (folder / "foto.jpg").is_file()
    assert (folder / "foto_1.jpg").is_file()


def test_ignores_disallowed_extensions(tmp_path: Path):
    config = _config(tmp_path, extensions=frozenset({".jpg"}))
    make_jpeg(config.source_dir / "ok.jpg", datetime_original="2024:03:15 10:00:00")
    (config.source_dir / "notes.txt").write_text("hello", encoding="utf-8")
    result = organize_photos(config, run_date=date(2026, 8, 17))
    run_dir = config.output_dir / "estrazione_del_2026_08_17"
    assert result.files_seen == 1
    assert list((run_dir / "2024_03_15").iterdir())[0].name == "ok.jpg"
    assert not (run_dir / "notes.txt").exists()


def test_second_run_same_day_reuses_folder(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 10:00:00")
    organize_photos(config, run_date=date(2026, 8, 17))
    (config.source_dir / "a.jpg").unlink()
    make_jpeg(config.source_dir / "b.jpg", datetime_original="2024:03:16 10:00:00")
    organize_photos(config, run_date=date(2026, 8, 17))
    run_dir = config.output_dir / "estrazione_del_2026_08_17"
    assert (run_dir / "2024_03_15" / "a.jpg").is_file()
    assert (run_dir / "2024_03_16" / "b.jpg").is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_organizer.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.organizer'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/organizer.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_organizer.py tests/test_exif.py tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/organizer.py tests/test_organizer.py
git commit -m "$(cat <<'EOF'
feat: copy photos into EXIF date folders

EOF
)"
```

---

### Task 4: CLI entrypoint, summary, README

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `load_config`, `ConfigError` from `src.config`; `organize_photos`, `RunResult` from `src.organizer`
- Produces:
  - `def print_summary(result: RunResult) -> None`
  - `def main(env_path: Path | None = None) -> int` — `0` on success, `1` on `ConfigError`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main.py`:

```python
from pathlib import Path

from src.main import main, print_summary
from src.organizer import RunResult
from tests.helpers import make_jpeg


def _write_env(tmp_path: Path, source: Path, output: Path) -> Path:
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                f"SOURCE_DIR={source}",
                f"OUTPUT_DIR={output}",
                "EXTENSIONS=.jpg,.jpeg,.heic,.heif,.png,.tiff,.tif",
                "NO_DATE_FOLDER=senza_data",
                "OUTPUT_PREFIX=estrazione_del_",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return env


def test_main_success_copies_and_returns_zero(tmp_path: Path, capsys):
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    make_jpeg(source / "a.jpg", datetime_original="2024:03:15 10:00:00")
    env = _write_env(tmp_path, source, output)
    assert main(env) == 0
    captured = capsys.readouterr()
    assert "Foto analizzate: 1" in captured.out
    assert "2024_03_15" in captured.out


def test_main_missing_env_returns_one(tmp_path: Path, capsys):
    assert main(tmp_path / "nope.env") == 1
    captured = capsys.readouterr()
    assert captured.err
    assert "Foto analizzate" not in captured.out


def test_main_empty_source_returns_one(tmp_path: Path):
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    env = _write_env(tmp_path, source, output)
    assert main(env) == 1


def test_print_summary_includes_counts(capsys):
    result = RunResult(
        files_seen=3,
        copied_by_date={"2024_03_15": 2},
        no_date_count=1,
        copy_errors=["x.jpg: boom"],
    )
    print_summary(result)
    text = capsys.readouterr().out
    assert "Foto analizzate: 3" in text
    assert "2024_03_15: 2" in text
    assert "Senza data: 1" in text
    assert "x.jpg: boom" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.main'`.

- [ ] **Step 3: Write minimal implementation and README**

Create `src/main.py`:

```python
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
```

Create `README.md`:

```markdown
# Photo EXIF Extractor

Copia le foto da una cartella sorgente in sottocartelle per data EXIF (`YYYY_MM_DD`), dentro `estrazione_del_YYYY_MM_DD` (data di esecuzione). Le originali non vengono spostate.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Modifica `.env` con i path reali.

## Uso

Dalla root del progetto:

```bash
python -m src.main
```

Le foto senza data EXIF vanno in `senza_data`. File con lo stesso nome vengono rinominati `foto_1.jpg`, `foto_2.jpg`, …

## Test

```bash
pytest
```
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest -v
```

Expected: PASS (all tests in `tests/`).

Then do a manual smoke check only if a real photo folder is available; otherwise the pytest suite is the verification.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py README.md
git commit -m "$(cat <<'EOF'
feat: add CLI entrypoint and usage README

EOF
)"
```

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| `.env` required keys, relative cwd paths | 1 |
| `SOURCE_DIR` exists and has allowed photos | 1 |
| `OUTPUT_DIR` created / not writable | 1 |
| Non-recursive listing, case-insensitive extensions | 1 |
| DateTimeOriginal → Digitized → DateTime | 2 |
| Invalid/missing/corrupt → no date | 2 |
| pillow-heif registered for HEIC/HEIF | 2 |
| Run folder `{OUTPUT_PREFIX}{YYYY_MM_DD}` | 3 |
| Date folders `YYYY_MM_DD`, `NO_DATE_FOLDER` | 3 |
| `shutil.copy2`, originals untouched | 3 |
| Collision `_1`, `_2` | 3 |
| Reuse run folder on same day | 3 |
| Ignore disallowed extensions | 3 |
| CLI `python -m src.main`, Italian summary | 4 |
| Exit 1 on config errors | 4 |
| `.env.example`, README, pytest fixtures | 1 + 4 |
| No dry-run / log / CI / recursion / RAW | out of scope, not implemented |
