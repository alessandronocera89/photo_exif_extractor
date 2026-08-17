from pathlib import Path

import piexif
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def _exif_bytes(
    datetime_original: str | None = None,
    datetime_digitized: str | None = None,
    datetime: str | None = None,
) -> bytes:
    zeroth: dict[int, bytes] = {}
    exif_ifd: dict[int, bytes] = {}
    if datetime:
        zeroth[piexif.ImageIFD.DateTime] = datetime.encode("utf-8")
    if datetime_original:
        exif_ifd[piexif.ExifIFD.DateTimeOriginal] = datetime_original.encode("utf-8")
    if datetime_digitized:
        exif_ifd[piexif.ExifIFD.DateTimeDigitized] = datetime_digitized.encode("utf-8")
    return piexif.dump({"0th": zeroth, "Exif": exif_ifd})


def make_jpeg(
    path: Path,
    datetime_original: str | None = None,
    datetime_digitized: str | None = None,
    datetime: str | None = None,
) -> Path:
    image = Image.new("RGB", (8, 8), "red")
    image.save(path, "JPEG", exif=_exif_bytes(datetime_original, datetime_digitized, datetime))
    return path


def make_heif(
    path: Path,
    datetime_original: str | None = None,
    datetime_digitized: str | None = None,
    datetime: str | None = None,
) -> Path:
    image = Image.new("RGB", (8, 8), "red")
    image.save(path, "HEIF", exif=_exif_bytes(datetime_original, datetime_digitized, datetime))
    return path
