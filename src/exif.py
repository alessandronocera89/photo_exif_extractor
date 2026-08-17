from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

DATETIME_ORIGINAL = 36867
DATETIME_DIGITIZED = 36868
DATETIME = 306
TAG_ORDER = (DATETIME_ORIGINAL, DATETIME_DIGITIZED, DATETIME)


def parse_exif_datetime(value: object) -> date | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    date_part = text.split()[0]
    for fmt in ("%Y:%m:%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def _exif_get(exif: Image.Exif, tag: int) -> object | None:
    if tag in exif:
        return exif.get(tag)
    try:
        nested = exif.get_ifd(0x8769)
    except Exception:
        nested = {}
    if tag in nested:
        return nested.get(tag)
    return None


def extract_photo_date(path: Path) -> date | None:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return None
            for tag in TAG_ORDER:
                parsed = parse_exif_datetime(_exif_get(exif, tag))
                if parsed is not None:
                    return parsed
            return None
    except Exception:
        return None
