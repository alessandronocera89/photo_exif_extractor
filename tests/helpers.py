from pathlib import Path
from struct import pack

import piexif
from mutagen.mp4 import AtomDataType, MP4, MP4FreeForm
from PIL import Image
from pillow_heif import register_heif_opener

APPLE_KEY = "----:com.apple.quicktime:creationdate"

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


def _box(tag: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + tag + payload


def _full_box(tag: bytes, version: int, flags: int, payload: bytes) -> bytes:
    return _box(tag, bytes([version]) + flags.to_bytes(3, "big") + payload)


def _quicktime_meta_box(creationdate: str) -> bytes:
    name = b"com.apple.quicktime.creationdate"
    key = (8 + len(name)).to_bytes(4, "big") + b"mdta" + name
    keys = _full_box(b"keys", 0, 0, (1).to_bytes(4, "big") + key)
    text = creationdate.encode("utf-8")
    data = _box(b"data", (1).to_bytes(4, "big") + (0).to_bytes(4, "big") + text)
    entry_index = (1).to_bytes(4, "big")
    ilst = _box(b"ilst", (8 + len(data)).to_bytes(4, "big") + entry_index + data)
    hdlr = _box(
        b"hdlr",
        (0).to_bytes(4, "big") + (0).to_bytes(4, "big") + b"mdta" + (0).to_bytes(12, "big"),
    )
    return _box(b"meta", hdlr + keys + ilst)


def make_mp4(
    path: Path,
    *,
    apple_creation: str | None = None,
    day: str | None = None,
    mvhd_unix: int | None = None,
    mvhd_mac: int | None = None,
    mdat: bytes | None = None,
    qt_creation: str | None = None,
) -> Path:
    creation = 0
    if mvhd_mac is not None:
        creation = mvhd_mac
    elif mvhd_unix is not None:
        creation = mvhd_unix + 2082844800
    mvhd_payload = b"".join(
        [
            creation.to_bytes(4, "big"),
            creation.to_bytes(4, "big"),
            (1000).to_bytes(4, "big"),
            (0).to_bytes(4, "big"),
            (0x00010000).to_bytes(4, "big"),
            (0x0100).to_bytes(2, "big"),
            (0).to_bytes(2, "big"),
            (0).to_bytes(8, "big"),
            pack(">9i", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000),
            (0).to_bytes(24, "big"),
            (2).to_bytes(4, "big"),
        ]
    )
    moov_body = _full_box(b"mvhd", 0, 0, mvhd_payload)
    if qt_creation:
        moov_body += _quicktime_meta_box(qt_creation)
    moov = _box(b"moov", moov_body)
    ftyp = _box(b"ftyp", b"isom" + (0).to_bytes(4, "big") + b"isommp41")
    parts = [ftyp]
    if mdat is not None:
        parts.append(_box(b"mdat", mdat))
    parts.append(moov)
    path.write_bytes(b"".join(parts))
    if apple_creation or day:
        mp4 = MP4(path)
        if apple_creation:
            mp4[APPLE_KEY] = [MP4FreeForm(apple_creation.encode("utf-8"), AtomDataType.UTF8)]
        if day:
            mp4["\xa9day"] = [day]
        mp4.save()
    return path


def _ebml_id(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _ebml_vint(value: int) -> bytes:
    for width in range(1, 9):
        max_val = (1 << (width * 7)) - 1
        if value <= max_val:
            marker = 1 << (8 - width)
            return (marker | value).to_bytes(width, "big")
    raise ValueError("vint too large")


def _ebml_element(element_id: int, payload: bytes) -> bytes:
    return _ebml_id(element_id) + _ebml_vint(len(payload)) + payload


def make_mkv(path: Path, date_utc_nanos: int) -> Path:
    date_el = _ebml_element(0x4461, date_utc_nanos.to_bytes(8, "big", signed=True))
    info = _ebml_element(0x1549A966, date_el)
    doctype = _ebml_element(0x4282, b"matroska")
    ebml = _ebml_element(0x1A45DFA3, doctype)
    segment = _ebml_element(0x18538067, info)
    path.write_bytes(ebml + segment)
    return path


def make_avi(
    path: Path,
    *,
    idit: str | None = None,
    icrd: str | None = None,
    movi_idit: str | None = None,
) -> Path:
    def chunk(tag: bytes, data: bytes) -> bytes:
        size = len(data)
        padded = data + (b"\x00" if size % 2 else b"")
        return tag + size.to_bytes(4, "little") + padded

    parts = b""
    if movi_idit is not None:
        movi_body = chunk(b"IDIT", movi_idit.encode("ascii"))
        parts += b"LIST" + (len(movi_body) + 4).to_bytes(4, "little") + b"movi" + movi_body
    info_body = b""
    if idit is not None:
        info_body += chunk(b"IDIT", idit.encode("ascii"))
    if icrd is not None:
        info_body += chunk(b"ICRD", icrd.encode("ascii"))
    if info_body:
        parts += b"LIST" + (len(info_body) + 4).to_bytes(4, "little") + b"INFO" + info_body
    riff_size = 4 + len(parts)
    path.write_bytes(b"RIFF" + riff_size.to_bytes(4, "little") + b"AVI " + parts)
    return path
