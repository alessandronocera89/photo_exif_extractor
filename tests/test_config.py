from pathlib import Path

import pytest

from src.config import (
    ConfigError,
    list_source_photos,
    load_config,
    parse_extensions,
    parse_folder_name,
)


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
        "NO_DATE_FOLDER": "no_date",
        "OUTPUT_PREFIX": "extraction_",
    }


def test_parse_extensions_normalizes_case_and_dot():
    assert parse_extensions(".JPG, jpeg, PNG") == frozenset({".jpg", ".jpeg", ".png"})


def test_parse_extensions_empty_raises():
    with pytest.raises(ConfigError, match="EXTENSIONS"):
        parse_extensions(" , ")


def test_parse_folder_name_rejects_path_separators():
    with pytest.raises(ConfigError, match="NO_DATE_FOLDER"):
        parse_folder_name("../fuori", "NO_DATE_FOLDER")
    with pytest.raises(ConfigError, match="OUTPUT_PREFIX"):
        parse_folder_name("extraction/of_", "OUTPUT_PREFIX")
    assert parse_folder_name("no_date", "NO_DATE_FOLDER") == "no_date"


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
    assert config.no_date_folder == "no_date"
    assert config.output_prefix == "extraction_"


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
    with pytest.raises(ConfigError, match="No photos"):
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
        NO_DATE_FOLDER="no_date",
        OUTPUT_PREFIX="extraction_",
    )
    config = load_config(env)
    assert config.source_dir == (tmp_path / "foto").resolve()
    assert config.output_dir == (tmp_path / "out").resolve()


def test_load_config_rejects_path_in_no_date_folder(tmp_path: Path):
    values = _valid_values(tmp_path)
    values["NO_DATE_FOLDER"] = "../fuori"
    env = _write_env(tmp_path, **values)
    with pytest.raises(ConfigError, match="NO_DATE_FOLDER"):
        load_config(env)
