from datetime import datetime
from pathlib import Path

from src.video import extract_video_datetime, parse_video_datetime
from tests.helpers import make_avi, make_mkv, make_mp4


def test_parse_video_datetime_exif_shape():
    assert parse_video_datetime("2024:03:15 14:30:00") == datetime(2024, 3, 15, 14, 30, 0)


def test_parse_video_datetime_iso_drops_offset_keeps_clock():
    assert parse_video_datetime("2024-03-15T14:30:00+0200") == datetime(2024, 3, 15, 14, 30, 0)
    assert parse_video_datetime("2024-03-15T14:30:00+02:00") == datetime(2024, 3, 15, 14, 30, 0)
    assert parse_video_datetime(b"2024-03-15T14:30:00+0200") == datetime(2024, 3, 15, 14, 30, 0)


def test_parse_video_datetime_year_only_is_invalid():
    assert parse_video_datetime("2024") is None


def test_parse_video_datetime_idit_ctime():
    assert parse_video_datetime("Fri Mar 15 14:30:00 2024") == datetime(2024, 3, 15, 14, 30, 0)


def test_mp4_prefers_apple_creationdate_over_day(tmp_path: Path):
    path = make_mp4(
        tmp_path / "clip.mp4",
        apple_creation="2024-03-15T14:30:00+0200",
        day="2024-01-01",
    )
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 14, 30, 0)


def test_mp4_uses_day_when_apple_tag_missing(tmp_path: Path):
    path = make_mp4(tmp_path / "clip.mp4", day="2024-03-16 09:00:00")
    assert extract_video_datetime(path) == datetime(2024, 3, 16, 9, 0, 0)


def test_mp4_falls_back_to_mvhd_utc_as_local(tmp_path: Path, monkeypatch):
    seen: list[float] = []
    path = make_mp4(tmp_path / "clip.mp4", mvhd_unix=1_710_511_800)

    def fake_local(unix: float) -> datetime:
        seen.append(unix)
        return datetime(2024, 3, 15, 14, 30, 0)

    monkeypatch.setattr("src.video._unix_to_local", fake_local)
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 14, 30, 0)
    assert seen == [1_710_511_800]


def test_mp4_skips_mvhd_sentinel_zero(tmp_path: Path):
    path = make_mp4(tmp_path / "clip.mp4", mvhd_unix=None)
    assert extract_video_datetime(path) is None


def test_mp4_skips_mvhd_sentinel_one(tmp_path: Path):
    path = make_mp4(tmp_path / "clip.mp4", mvhd_mac=1)
    assert extract_video_datetime(path) is None


def test_mp4_prefers_quicktime_mdta_creationdate_over_mvhd(tmp_path: Path):
    path = make_mp4(
        tmp_path / "iphone.mov",
        mvhd_unix=1_596_216_000,
        qt_creation="2018-04-03T00:24:38+02:00",
        mdat=b"x" * 1024,
    )
    assert extract_video_datetime(path) == datetime(2018, 4, 3, 0, 24, 38)


def test_corrupt_video_returns_none(tmp_path: Path):
    path = tmp_path / "broken.mp4"
    path.write_bytes(b"not a video")
    assert extract_video_datetime(path) is None


def test_mkv_dateutc_converted_from_2001_epoch(tmp_path: Path, monkeypatch):
    path = make_mkv(tmp_path / "clip.mkv", 0)
    monkeypatch.setattr(
        "src.video._unix_to_local",
        lambda unix: datetime(2001, 1, 1, 0, 0, 0) if unix == 978307200 else None,
    )
    assert extract_video_datetime(path) == datetime(2001, 1, 1, 0, 0, 0)


def test_avi_prefers_idit_over_icrd(tmp_path: Path):
    path = make_avi(
        tmp_path / "clip.avi",
        idit="Fri Mar 15 14:30:00 2024",
        icrd="2024-01-01",
    )
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 14, 30, 0)


def test_avi_icrd_date_only(tmp_path: Path):
    path = make_avi(tmp_path / "clip.avi", icrd="2024-03-15")
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 0, 0, 0)


def test_avi_ignores_idit_inside_movi(tmp_path: Path):
    path = make_avi(
        tmp_path / "clip.avi",
        icrd="2024-03-15",
        movi_idit="Fri Jan 01 00:00:00 2020",
    )
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 0, 0, 0)


def test_mp4_reads_mvhd_after_mdat_without_slurping(tmp_path: Path, monkeypatch):
    path = make_mp4(
        tmp_path / "clip.mp4",
        mvhd_unix=1_710_511_800,
        mdat=b"x" * 4096,
    )
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda self: (_ for _ in ()).throw(AssertionError("read_bytes")),
    )
    monkeypatch.setattr(
        "src.video._unix_to_local",
        lambda unix: datetime(2024, 3, 15, 14, 30, 0) if unix == 1_710_511_800 else None,
    )
    assert extract_video_datetime(path) == datetime(2024, 3, 15, 14, 30, 0)


def test_mkv_and_avi_do_not_slurp_whole_file(tmp_path: Path, monkeypatch):
    mkv = make_mkv(tmp_path / "clip.mkv", 0)
    avi = make_avi(tmp_path / "clip.avi", icrd="2024-03-15")
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda self: (_ for _ in ()).throw(AssertionError("read_bytes")),
    )
    monkeypatch.setattr(
        "src.video._unix_to_local",
        lambda unix: datetime(2001, 1, 1, 0, 0, 0) if unix == 978307200 else None,
    )
    assert extract_video_datetime(mkv) == datetime(2001, 1, 1, 0, 0, 0)
    assert extract_video_datetime(avi) == datetime(2024, 3, 15, 0, 0, 0)
