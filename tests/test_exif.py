from datetime import date
from pathlib import Path

from PIL import Image

from src.exif import extract_photo_date, parse_exif_datetime
from tests.helpers import make_heif, make_jpeg


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


def test_extract_heif_datetime_original(tmp_path: Path):
    path = make_heif(tmp_path / "iphone.heic", datetime_original="2024:06:20 10:00:00")
    with Image.open(path) as image:
        assert image.format == "HEIF"
    assert extract_photo_date(path) == date(2024, 6, 20)
