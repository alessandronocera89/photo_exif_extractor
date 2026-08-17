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
