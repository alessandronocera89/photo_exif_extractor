from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.config import Config
from src.organizer import (
    copy_file,
    date_folder_name,
    organize_photos,
    run_folder_name,
    unique_destination,
)
from tests.helpers import make_heif, make_jpeg, make_mp4


def _config(
    tmp_path: Path,
    extensions: frozenset[str] | None = None,
    group_by: str = "date",
) -> Config:
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    return Config(
        source_dir=source,
        output_dir=output,
        extensions=extensions or frozenset({".jpg", ".jpeg", ".heic", ".png", ".tif"}),
        no_date_folder="no_date",
        output_prefix="extraction_",
        group_by=group_by,
    )


def test_run_folder_name():
    assert run_folder_name("extraction_", "Viaggio_Giappone") == "extraction_Viaggio_Giappone"


def test_date_folder_name():
    assert date_folder_name(date(2024, 3, 15), "no_date") == "2024_03_15"
    assert date_folder_name(None, "no_date") == "no_date"


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
    result = organize_photos(config)
    run_dir = config.output_dir / "extraction_foto"
    assert (run_dir / "2024_03_15" / "a.jpg").is_file()
    assert (run_dir / "2024_03_15" / "b.jpg").is_file()
    assert (run_dir / "2024_03_16" / "c.jpg").is_file()
    assert result.files_seen == 3
    assert result.copied_by_date == {"2024_03_15": 2, "2024_03_16": 1}
    assert result.no_date_count == 0
    assert (config.source_dir / "a.jpg").is_file()


def test_no_date_goes_to_no_date_folder(tmp_path: Path):
    config = _config(tmp_path)
    Image.new("RGB", (8, 8), "blue").save(config.source_dir / "plain.jpg", "JPEG")
    result = organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "no_date" / "plain.jpg"
    assert dest.is_file()
    assert result.no_date_count == 1
    assert result.copied_by_date == {}


def test_name_collision_renames(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "foto.jpg", datetime_original="2024:03:15 10:00:00")
    organize_photos(config)
    make_jpeg(config.source_dir / "foto.jpg", datetime_original="2024:03:15 11:00:00")
    organize_photos(config)
    folder = config.output_dir / "extraction_foto" / "2024_03_15"
    assert (folder / "foto.jpg").is_file()
    assert (folder / "foto_1.jpg").is_file()


def test_ignores_disallowed_extensions(tmp_path: Path):
    config = _config(tmp_path, extensions=frozenset({".jpg"}))
    make_jpeg(config.source_dir / "ok.jpg", datetime_original="2024:03:15 10:00:00")
    (config.source_dir / "notes.txt").write_text("hello", encoding="utf-8")
    result = organize_photos(config)
    run_dir = config.output_dir / "extraction_foto"
    assert result.files_seen == 1
    assert list((run_dir / "2024_03_15").iterdir())[0].name == "ok.jpg"
    assert not (run_dir / "notes.txt").exists()


def test_groups_heif_by_exif_date(tmp_path: Path):
    config = _config(tmp_path)
    make_heif(config.source_dir / "iphone.heic", datetime_original="2024:06:20 10:00:00")
    result = organize_photos(config)
    run_dir = config.output_dir / "extraction_foto"
    assert (run_dir / "2024_06_20" / "iphone.heic").is_file()
    assert result.files_seen == 1
    assert result.copied_by_date == {"2024_06_20": 1}
    assert result.no_date_count == 0


def test_copy_failure_records_error_and_continues(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "ok.jpg", datetime_original="2024:03:15 10:00:00")
    make_jpeg(config.source_dir / "fail.jpg", datetime_original="2024:03:16 10:00:00")
    original_copy = copy_file

    def flaky_copy(src, dst, *args, **kwargs):
        if Path(src).name == "fail.jpg":
            raise OSError("copy failed")
        return original_copy(src, dst, *args, **kwargs)

    with patch("src.organizer.copy_file", side_effect=flaky_copy):
        result = organize_photos(config)

    run_dir = config.output_dir / "extraction_foto"
    assert result.files_seen == 2
    assert len(result.copy_errors) == 1
    assert "fail.jpg" in result.copy_errors[0]
    assert (run_dir / "2024_03_15" / "ok.jpg").is_file()
    assert not (run_dir / "2024_03_16" / "fail.jpg").exists()


def test_mkdir_failure_records_error_and_continues(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "ok.jpg", datetime_original="2024:03:15 10:00:00")
    make_jpeg(config.source_dir / "fail.jpg", datetime_original="2024:03:16 10:00:00")
    original_mkdir = Path.mkdir

    def flaky_mkdir(self, *args, **kwargs):
        if self.name == "2024_03_16":
            raise OSError("mkdir failed")
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", flaky_mkdir):
        result = organize_photos(config)

    run_dir = config.output_dir / "extraction_foto"
    assert result.files_seen == 2
    assert len(result.copy_errors) == 1
    assert "fail.jpg" in result.copy_errors[0]
    assert (run_dir / "2024_03_15" / "ok.jpg").is_file()
    assert not (run_dir / "2024_03_16" / "fail.jpg").exists()


def test_second_run_reuses_folder(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 10:00:00")
    organize_photos(config)
    (config.source_dir / "a.jpg").unlink()
    make_jpeg(config.source_dir / "b.jpg", datetime_original="2024:03:16 10:00:00")
    organize_photos(config)
    run_dir = config.output_dir / "extraction_foto"
    assert (run_dir / "2024_03_15" / "a.jpg").is_file()
    assert (run_dir / "2024_03_16" / "b.jpg").is_file()


def test_photo_and_video_share_date_folder(tmp_path: Path):
    config = _config(tmp_path, extensions=frozenset({".jpg", ".mp4"}))
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 10:00:00")
    make_mp4(config.source_dir / "b.mp4", day="2024-03-15 11:00:00")
    result = organize_photos(config)
    folder = config.output_dir / "extraction_foto" / "2024_03_15"
    assert (folder / "a.jpg").is_file()
    assert (folder / "b.mp4").is_file()
    assert result.copied_by_date == {"2024_03_15": 2}


def test_video_without_metadata_goes_to_no_date(tmp_path: Path):
    config = _config(tmp_path, extensions=frozenset({".mp4"}))
    make_mp4(config.source_dir / "clip.mp4")
    result = organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "no_date" / "clip.mp4"
    assert dest.is_file()
    assert result.no_date_count == 1


def test_copied_file_uses_exif_capture_time(tmp_path: Path):
    config = _config(tmp_path)
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 14:30:00")
    organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "2024_03_15" / "a.jpg"
    expected = datetime(2024, 3, 15, 14, 30, 0).timestamp()
    stat = dest.stat()
    assert abs(stat.st_mtime - expected) < 2
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime is not None:
        assert abs(birthtime - expected) < 2


def test_copied_video_uses_capture_time(tmp_path: Path):
    config = _config(tmp_path, extensions=frozenset({".mp4"}))
    make_mp4(config.source_dir / "clip.mp4", day="2024-03-15 14:30:00")
    organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "2024_03_15" / "clip.mp4"
    expected = datetime(2024, 3, 15, 14, 30, 0).timestamp()
    stat = dest.stat()
    assert abs(stat.st_mtime - expected) < 2
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime is not None:
        assert abs(birthtime - expected) < 2


def test_organize_progress_uses_total_file_sizes(tmp_path: Path):
    config = _config(tmp_path)
    (config.source_dir / "large.jpg").write_bytes(b"x" * 300)
    (config.source_dir / "small.jpg").write_bytes(b"x" * 100)
    stream = StringIO()
    organize_photos(
        config,
        show_progress=True,
        progress_stream=stream,
    )
    text = stream.getvalue()
    assert "Processing: 2 files, 400 B" in text
    assert "100%" in text


def test_date_mode_flattens_nested_files(tmp_path: Path):
    config = _config(tmp_path)
    album = config.source_dir / "Tokyo"
    album.mkdir()
    make_jpeg(album / "IMG_001.jpg", datetime_original="2024:03:15 10:00:00")
    result = organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "2024_03_15" / "IMG_001.jpg"
    assert dest.is_file()
    assert result.copied_by_date == {"2024_03_15": 1}
    assert (config.source_dir / "Tokyo" / "IMG_001.jpg").is_file()


def test_date_mode_collision_from_two_folders(tmp_path: Path):
    config = _config(tmp_path)
    (config.source_dir / "a").mkdir()
    (config.source_dir / "b").mkdir()
    make_jpeg(config.source_dir / "a" / "foto.jpg", datetime_original="2024:03:15 10:00:00")
    make_jpeg(config.source_dir / "b" / "foto.jpg", datetime_original="2024:03:15 11:00:00")
    organize_photos(config)
    folder = config.output_dir / "extraction_foto" / "2024_03_15"
    assert (folder / "foto.jpg").is_file()
    assert (folder / "foto_1.jpg").is_file()


def test_tree_mode_mirrors_relative_path(tmp_path: Path):
    config = _config(tmp_path, group_by="tree")
    album = config.source_dir / "Kyoto" / "giorno2"
    album.mkdir(parents=True)
    make_jpeg(album / "IMG_002.jpg", datetime_original="2024:03:15 10:00:00")
    make_jpeg(config.source_dir / "loose.jpg", datetime_original="2024:03:16 08:00:00")
    result = organize_photos(config)
    run_dir = config.output_dir / "extraction_foto"
    assert (run_dir / "Kyoto" / "giorno2" / "IMG_002.jpg").is_file()
    assert (run_dir / "loose.jpg").is_file()
    assert not (run_dir / "2024_03_15").exists()
    assert not (run_dir / "no_date").exists()
    assert result.files_seen == 2
    assert (config.source_dir / "Kyoto" / "giorno2" / "IMG_002.jpg").is_file()


def test_tree_mode_no_date_stays_in_place(tmp_path: Path):
    config = _config(tmp_path, group_by="tree")
    Image.new("RGB", (8, 8), "blue").save(config.source_dir / "plain.jpg", "JPEG")
    result = organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "plain.jpg"
    assert dest.is_file()
    assert result.no_date_count == 1
    assert not (config.output_dir / "extraction_foto" / "no_date").exists()


def test_tree_mode_second_run_suffixes(tmp_path: Path):
    config = _config(tmp_path, group_by="tree")
    nested = config.source_dir / "Tokyo"
    nested.mkdir()
    make_jpeg(nested / "IMG_001.jpg", datetime_original="2024:03:15 10:00:00")
    organize_photos(config)
    organize_photos(config)
    folder = config.output_dir / "extraction_foto" / "Tokyo"
    assert (folder / "IMG_001.jpg").is_file()
    assert (folder / "IMG_001_1.jpg").is_file()


def test_tree_mode_sets_capture_timestamps(tmp_path: Path):
    config = _config(tmp_path, group_by="tree")
    make_jpeg(config.source_dir / "a.jpg", datetime_original="2024:03:15 14:30:00")
    organize_photos(config)
    dest = config.output_dir / "extraction_foto" / "a.jpg"
    expected = datetime(2024, 3, 15, 14, 30, 0).timestamp()
    assert abs(dest.stat().st_mtime - expected) < 2


def test_copy_error_uses_relative_path(tmp_path: Path):
    config = _config(tmp_path)
    nested = config.source_dir / "Kyoto"
    nested.mkdir()
    make_jpeg(nested / "fail.jpg", datetime_original="2024:03:15 10:00:00")
    with patch("src.organizer.copy_file", side_effect=OSError("copy failed")):
        result = organize_photos(config)
    assert result.copy_errors
    assert "Kyoto/fail.jpg" in result.copy_errors[0]


def test_output_beside_source_on_same_parent(tmp_path: Path):
    desktop = tmp_path / "Scrivania"
    source = desktop / "Viaggio_Giappone"
    source.mkdir(parents=True)
    make_jpeg(source / "a.jpg", datetime_original="2024:03:15 10:00:00")
    config = Config(
        source_dir=source,
        output_dir=desktop,
        extensions=frozenset({".jpg"}),
        no_date_folder="no_date",
        output_prefix="extraction_",
        group_by="date",
    )
    organize_photos(config)
    dest = desktop / "extraction_Viaggio_Giappone" / "2024_03_15" / "a.jpg"
    assert dest.is_file()
    assert (source / "a.jpg").is_file()
    assert source.is_dir()


def test_organize_skips_run_dir_when_source_equals_output(tmp_path: Path):
    source = tmp_path / "foto"
    source.mkdir()
    make_jpeg(source / "a.jpg", datetime_original="2024:03:15 10:00:00")
    config = Config(
        source_dir=source,
        output_dir=source,
        extensions=frozenset({".jpg"}),
        no_date_folder="no_date",
        output_prefix="extraction_",
        group_by="date",
    )
    organize_photos(config)
    result = organize_photos(config)
    run_dir = source / "extraction_foto" / "2024_03_15"
    assert result.files_seen == 1
    assert (run_dir / "a.jpg").is_file()
    assert (run_dir / "a_1.jpg").is_file()
    assert sorted(path.name for path in run_dir.iterdir()) == ["a.jpg", "a_1.jpg"]


def test_organize_skips_nested_output_on_second_run(tmp_path: Path):
    source = tmp_path / "foto"
    output = source / "out"
    source.mkdir()
    output.mkdir()
    make_jpeg(source / "a.jpg", datetime_original="2024:03:15 10:00:00")
    config = Config(
        source_dir=source,
        output_dir=output,
        extensions=frozenset({".jpg"}),
        no_date_folder="no_date",
        output_prefix="extraction_",
        group_by="date",
    )
    organize_photos(config)
    result = organize_photos(config)
    run_dir = output / "extraction_foto" / "2024_03_15"
    assert result.files_seen == 1
    assert (run_dir / "a.jpg").is_file()
    assert (run_dir / "a_1.jpg").is_file()
    assert sorted(path.name for path in run_dir.iterdir()) == ["a.jpg", "a_1.jpg"]
