import io

from src.progress import ProgressBar, clip_name, format_bytes


def test_clip_name_keeps_short_names():
    assert clip_name("small.jpg") == "small.jpg"


def test_clip_name_keeps_the_end_of_long_relative_paths():
    name = "vacanze/Kyoto/giorno2/album/IMG_002.mov"
    clipped = clip_name(name, limit=24)
    assert clipped.startswith("...")
    assert clipped.endswith("IMG_002.mov")
    assert len(clipped) == 24


def test_format_bytes_units():
    assert format_bytes(0) == "0 B"
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"


def test_progress_ratio_is_weighted_by_bytes():
    stream = io.StringIO()
    bar = ProgressBar(total_files=2, total_bytes=400, enabled=True, stream=stream)
    bar.update(files_done=1, bytes_done=100, current_name="small.jpg")
    output = stream.getvalue()
    assert "Processing: 2 files, 400 B" in output
    assert " 25%" in output
    assert "1/2" in output
    assert "small.jpg" in output


def test_progress_disabled_writes_nothing():
    stream = io.StringIO()
    bar = ProgressBar(total_files=2, total_bytes=400, enabled=False, stream=stream)
    bar.update(1, 100, "a.jpg")
    bar.finish()
    assert stream.getvalue() == ""
