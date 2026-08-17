from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from datetime import datetime
from pathlib import Path


def apply_capture_times(path: Path, captured: datetime) -> None:
    timestamp = captured.timestamp()
    os.utime(path, (timestamp, timestamp))
    if sys.platform == "darwin":
        _set_macos_creation_time(path, timestamp)


def _set_macos_creation_time(path: Path, timestamp: float) -> None:
    libc_name = ctypes.util.find_library("c")
    if libc_name is None:
        return
    libc = ctypes.CDLL(libc_name, use_errno=True)

    class TimeSpec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_int64), ("tv_nsec", ctypes.c_long)]

    class AttrList(ctypes.Structure):
        _fields_ = [
            ("bitmapcount", ctypes.c_uint16),
            ("reserved", ctypes.c_uint16),
            ("commonattr", ctypes.c_uint32),
            ("volattr", ctypes.c_uint32),
            ("dirattr", ctypes.c_uint32),
            ("fileattr", ctypes.c_uint32),
            ("forkattr", ctypes.c_uint32),
        ]

    ATTR_BIT_MAP_COUNT = 5
    ATTR_CMN_CRTIME = 0x00000200
    attrs = AttrList(
        bitmapcount=ATTR_BIT_MAP_COUNT,
        reserved=0,
        commonattr=ATTR_CMN_CRTIME,
        volattr=0,
        dirattr=0,
        fileattr=0,
        forkattr=0,
    )
    seconds = int(timestamp)
    nanos = int(round((timestamp - seconds) * 1_000_000_000))
    timespec = TimeSpec(seconds, nanos)
    libc.setattrlist.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    result = libc.setattrlist(
        os.fsencode(path),
        ctypes.byref(attrs),
        ctypes.byref(timespec),
        ctypes.sizeof(timespec),
        0,
    )
    if result != 0:
        return
