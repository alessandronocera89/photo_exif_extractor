import sys
from datetime import datetime
from pathlib import Path

import pytest

from src.timestamps import apply_capture_times, _unix_to_windows_filetime


def test_unix_to_windows_filetime_known_epoch():
    low, high = _unix_to_windows_filetime(0)
    value = (high << 32) | low
    assert value == 116444736000000000


def test_apply_capture_times_sets_mtime(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"x")
    captured = datetime(2024, 3, 15, 14, 30, 0)
    apply_capture_times(path, captured)
    assert abs(path.stat().st_mtime - captured.timestamp()) < 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows creation time")
def test_windows_creation_time_set(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"x")
    captured = datetime(2024, 3, 15, 14, 30, 0)
    apply_capture_times(path, captured)
    assert abs(path.stat().st_ctime - captured.timestamp()) < 2
