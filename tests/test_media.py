from datetime import datetime
from pathlib import Path

from src.media import extract_capture_datetime
from tests.helpers import make_jpeg, make_mp4


def test_dispatcher_uses_photo_exif(tmp_path: Path):
    path = make_jpeg(tmp_path / "a.jpg", datetime_original="2024:03:15 10:00:00")
    assert extract_capture_datetime(path) == datetime(2024, 3, 15, 10, 0, 0)


def test_dispatcher_uses_video_metadata(tmp_path: Path):
    path = make_mp4(tmp_path / "a.mp4", day="2024-03-15 10:00:00")
    assert extract_capture_datetime(path) == datetime(2024, 3, 15, 10, 0, 0)


def test_dispatcher_unknown_suffix_returns_none(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("x", encoding="utf-8")
    assert extract_capture_datetime(path) is None
