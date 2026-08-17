from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from mutagen.mp4 import MP4

from src.exif import parse_exif_datetime

MAC_EPOCH_OFFSET = 2082844800
MATROSKA_EPOCH_OFFSET = 978307200
APPLE_CREATION = "----:com.apple.quicktime:creationdate"
COPYRIGHT_DAY = "\xa9day"
MP4_SUFFIXES = frozenset({".mp4", ".mov", ".m4v", ".3gp"})
MKV_SUFFIXES = frozenset({".mkv"})
AVI_SUFFIXES = frozenset({".avi"})
VIDEO_SUFFIXES = MP4_SUFFIXES | MKV_SUFFIXES | AVI_SUFFIXES
EBML_CONTAINER_IDS = {0x1A45DFA3, 0x18538067, 0x1549A966}
_IDIT_CTIME = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})"
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_video_datetime(value: object) -> datetime | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)) and value:
        return parse_video_datetime(value[0])
    if not isinstance(value, str):
        return None
    text = value.strip().strip("\x00")
    if not text:
        return None
    if text.isdigit() and len(text) == 4:
        return None
    iso = text.replace("Z", "+00:00")
    if "T" in iso:
        iso = _normalize_iso_offset(iso)
        try:
            parsed = datetime.fromisoformat(iso)
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed.replace(tzinfo=None)
    ctime = _parse_idit_ctime(text)
    if ctime is not None:
        return ctime
    return parse_exif_datetime(text)


def _parse_idit_ctime(text: str) -> datetime | None:
    match = _IDIT_CTIME.match(text)
    if match is None:
        return None
    month = _MONTHS.get(match.group(1))
    if month is None:
        return None
    try:
        return datetime(
            int(match.group(6)),
            month,
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
        )
    except ValueError:
        return None


def _normalize_iso_offset(text: str) -> str:
    if len(text) >= 5 and (text[-5] in "+-") and text[-3] != ":":
        return text[:-2] + ":" + text[-2:]
    return text


def _unix_to_local(unix: float) -> datetime:
    return datetime.fromtimestamp(unix)


def extract_video_datetime(path: Path) -> datetime | None:
    suffix = path.suffix.lower()
    try:
        if suffix in MP4_SUFFIXES:
            return _extract_mp4_datetime(path)
        if suffix in MKV_SUFFIXES:
            return _extract_mkv_datetime(path)
        if suffix in AVI_SUFFIXES:
            return _extract_avi_datetime(path)
    except Exception:
        return None
    return None


def _extract_mp4_datetime(path: Path) -> datetime | None:
    try:
        mp4 = MP4(path)
        tags = mp4.tags or {}
        for key in (APPLE_CREATION, COPYRIGHT_DAY):
            parsed = parse_video_datetime(tags.get(key))
            if parsed is not None:
                return parsed
    except Exception:
        pass
    with path.open("rb") as fh:
        moov = _find_box_payload_stream(fh, b"moov")
    if moov is None:
        return None
    parsed = _read_quicktime_creationdate(moov)
    if parsed is not None:
        return parsed
    return _read_mvhd_datetime_from(moov)


def _find_box_payload_stream(fh: BinaryIO, wanted: bytes) -> bytes | None:
    while True:
        header = fh.read(8)
        if len(header) < 8:
            return None
        size = int.from_bytes(header[:4], "big")
        tag = header[4:8]
        header_len = 8
        if size == 1:
            extra = fh.read(8)
            if len(extra) < 8:
                return None
            size = int.from_bytes(extra, "big")
            header_len = 16
        elif size == 0:
            if tag == wanted:
                return fh.read()
            return None
        payload_size = size - header_len
        if payload_size < 0:
            return None
        if tag == wanted:
            payload = fh.read(payload_size)
            if len(payload) != payload_size:
                return None
            return payload
        fh.seek(payload_size, os.SEEK_CUR)


def _find_box_payload(data: bytes, wanted: bytes) -> bytes | None:
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        tag = data[offset + 4 : offset + 8]
        header = 8
        if size == 1:
            if offset + 16 > len(data):
                break
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        elif size == 0:
            size = len(data) - offset
        if size < header or offset + size > len(data):
            break
        if tag == wanted:
            return data[offset + header : offset + size]
        offset += size
    return None


def _read_mvhd_datetime_from(moov: bytes) -> datetime | None:
    payload = _find_box_payload(moov, b"mvhd")
    if payload is None or len(payload) < 8:
        return None
    version = payload[0]
    body = payload[4:]
    if version == 1:
        if len(body) < 8:
            return None
        created = int.from_bytes(body[0:8], "big")
    else:
        if len(body) < 4:
            return None
        created = int.from_bytes(body[0:4], "big")
    if created in {0, 1}:
        return None
    return _unix_to_local(created - MAC_EPOCH_OFFSET)


def _meta_payload(meta: bytes) -> bytes:
    if len(meta) >= 8 and meta[4:8] in {b"hdlr", b"keys", b"ilst"}:
        return meta
    if len(meta) >= 12:
        return meta[4:]
    return meta


def _parse_mdta_keys(payload: bytes) -> list[str]:
    if len(payload) < 8:
        return []
    count = int.from_bytes(payload[4:8], "big")
    names: list[str] = []
    offset = 8
    for _ in range(count):
        if offset + 8 > len(payload):
            break
        key_size = int.from_bytes(payload[offset : offset + 4], "big")
        if key_size < 8 or offset + key_size > len(payload):
            break
        names.append(payload[offset + 8 : offset + key_size].decode("utf-8", errors="replace"))
        offset += key_size
    return names


def _parse_mdta_ilst(payload: bytes) -> dict[int, str]:
    values: dict[int, str] = {}
    offset = 0
    while offset + 8 <= len(payload):
        size = int.from_bytes(payload[offset : offset + 4], "big")
        index = int.from_bytes(payload[offset + 4 : offset + 8], "big")
        if size < 8 or offset + size > len(payload):
            break
        data = _find_box_payload(payload[offset + 8 : offset + size], b"data")
        if data is not None and len(data) >= 8:
            values[index] = data[8:].decode("utf-8", errors="replace")
        offset += size
    return values


def _read_quicktime_creationdate(moov: bytes) -> datetime | None:
    meta = _find_box_payload(moov, b"meta")
    if meta is None:
        udta = _find_box_payload(moov, b"udta")
        if udta is not None:
            meta = _find_box_payload(udta, b"meta")
    if meta is None:
        return None
    inner = _meta_payload(meta)
    keys_payload = _find_box_payload(inner, b"keys")
    ilst_payload = _find_box_payload(inner, b"ilst")
    if keys_payload is None or ilst_payload is None:
        return None
    names = _parse_mdta_keys(keys_payload)
    values = _parse_mdta_ilst(ilst_payload)
    for index, name in enumerate(names, start=1):
        if name == "com.apple.quicktime.creationdate" or name.endswith(".creationdate"):
            parsed = parse_video_datetime(values.get(index))
            if parsed is not None:
                return parsed
    return None


def _extract_mkv_datetime(path: Path) -> datetime | None:
    with path.open("rb") as fh:
        nanos = _find_mkv_dateutc_stream(fh, None)
    if nanos is None:
        return None
    unix = nanos / 1_000_000_000 + MATROSKA_EPOCH_OFFSET
    return _unix_to_local(unix)


def _read_ebml_vint(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset >= len(data):
        return None
    first = data[offset]
    width = 0
    for bit in range(8):
        if first & (0x80 >> bit):
            width = bit + 1
            break
    if width == 0 or offset + width > len(data):
        return None
    value = first & ((1 << (8 - width)) - 1)
    for i in range(1, width):
        value = (value << 8) | data[offset + i]
    return value, width


def _read_ebml_vint_stream(fh: BinaryIO, end: int | None) -> tuple[int, int] | None:
    pos = fh.tell()
    if end is not None and pos >= end:
        return None
    first_b = fh.read(1)
    if not first_b:
        return None
    first = first_b[0]
    width = 0
    for bit in range(8):
        if first & (0x80 >> bit):
            width = bit + 1
            break
    if width == 0:
        return None
    if end is not None and pos + width > end:
        return None
    rest = fh.read(width - 1) if width > 1 else b""
    if len(rest) != width - 1:
        return None
    return _read_ebml_vint(first_b + rest, 0)


def _find_mkv_dateutc_stream(fh: BinaryIO, end: int | None) -> int | None:
    while True:
        id_start = fh.tell()
        if end is not None and id_start >= end:
            return None
        id_info = _read_ebml_vint_stream(fh, end)
        if id_info is None:
            return None
        id_width = id_info[1]
        fh.seek(id_start)
        raw_id_bytes = fh.read(id_width)
        if len(raw_id_bytes) != id_width:
            return None
        raw_id = int.from_bytes(raw_id_bytes, "big")
        size_info = _read_ebml_vint_stream(fh, end)
        if size_info is None:
            return None
        size, _size_width = size_info
        payload_start = fh.tell()
        payload_end = payload_start + size
        if end is not None:
            payload_end = min(payload_end, end)
        if raw_id == 0x4461 and size == 8:
            data = fh.read(8)
            if len(data) == 8:
                return int.from_bytes(data, "big", signed=True)
            return None
        if raw_id in EBML_CONTAINER_IDS:
            found = _find_mkv_dateutc_stream(fh, payload_end)
            if found is not None:
                return found
            fh.seek(payload_end)
            continue
        fh.seek(payload_end)


def _extract_avi_datetime(path: Path) -> datetime | None:
    with path.open("rb") as fh:
        header = fh.read(12)
        if len(header) < 12 or header[:4] != b"RIFF":
            return None
        found = _avi_scan_info(fh)
    parsed = parse_video_datetime(found.get(b"IDIT"))
    if parsed is not None:
        return parsed
    return parse_video_datetime(found.get(b"ICRD"))


def _avi_scan_info(fh: BinaryIO) -> dict[bytes, str]:
    found: dict[bytes, str] = {}
    while True:
        hdr = fh.read(8)
        if len(hdr) < 8:
            return found
        chunk_id = hdr[:4]
        size = int.from_bytes(hdr[4:8], "little")
        payload_start = fh.tell()
        if chunk_id == b"LIST":
            list_type = fh.read(4)
            if list_type == b"INFO":
                _avi_read_info_list(fh, size - 4, found)
        fh.seek(payload_start + size)
        if size % 2:
            fh.seek(1, os.SEEK_CUR)
    return found


def _avi_read_info_list(fh: BinaryIO, remaining: int, found: dict[bytes, str]) -> None:
    end = fh.tell() + remaining
    while fh.tell() + 8 <= end:
        hdr = fh.read(8)
        if len(hdr) < 8:
            return
        chunk_id = hdr[:4]
        size = int.from_bytes(hdr[4:8], "little")
        payload = fh.read(min(size, end - fh.tell()))
        if chunk_id in {b"IDIT", b"ICRD"}:
            found[chunk_id] = payload.decode("utf-8", errors="replace")
        next_pos = fh.tell()
        if size % 2:
            next_pos += 1
        fh.seek(min(next_pos, end))
