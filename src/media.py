from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.exif import extract_photo_datetime
from src.video import VIDEO_SUFFIXES, extract_video_datetime

PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".heic", ".heif", ".png", ".tiff", ".tif"})


def extract_capture_datetime(path: Path) -> datetime | None:
    suffix = path.suffix.lower()
    if suffix in PHOTO_SUFFIXES:
        return extract_photo_datetime(path)
    if suffix in VIDEO_SUFFIXES:
        return extract_video_datetime(path)
    return None
