from pathlib import Path

import piexif
from PIL import Image


def make_jpeg(
    path: Path,
    datetime_original: str | None = None,
    datetime_digitized: str | None = None,
    datetime: str | None = None,
) -> Path:
    image = Image.new("RGB", (8, 8), "red")
    zeroth: dict[int, bytes] = {}
    exif_ifd: dict[int, bytes] = {}
    if datetime:
        zeroth[piexif.ImageIFD.DateTime] = datetime.encode("utf-8")
    if datetime_original:
        exif_ifd[piexif.ExifIFD.DateTimeOriginal] = datetime_original.encode("utf-8")
    if datetime_digitized:
        exif_ifd[piexif.ExifIFD.DateTimeDigitized] = datetime_digitized.encode("utf-8")
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif_ifd})
    image.save(path, "JPEG", exif=exif_bytes)
    return path
