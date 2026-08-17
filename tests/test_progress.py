import io

from src.progress import ProgressBar, format_bytes


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
