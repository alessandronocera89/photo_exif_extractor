from __future__ import annotations

import sys
from typing import TextIO


def format_bytes(n: int) -> str:
    size = float(max(n, 0))
    for unit in ("B", "KB", "MB", "GB"):
        if unit == "B":
            if size < 1024:
                return f"{int(size)} B"
        elif size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class ProgressBar:
    def __init__(
        self,
        total_files: int,
        total_bytes: int,
        enabled: bool,
        stream: TextIO | None = None,
    ) -> None:
        self.total_files = max(total_files, 0)
        self.total_bytes = max(total_bytes, 0)
        self.enabled = enabled
        self.stream = stream if stream is not None else sys.stderr
        self._last_len = 0
        if self.enabled:
            print(
                f"Processing: {self.total_files} files, {format_bytes(self.total_bytes)}",
                file=self.stream,
                flush=True,
            )

    def update(self, files_done: int, bytes_done: int, current_name: str) -> None:
        if not self.enabled:
            return
        if self.total_bytes > 0:
            ratio = min(max(bytes_done, 0) / self.total_bytes, 1.0)
        elif self.total_files > 0:
            ratio = min(max(files_done, 0) / self.total_files, 1.0)
        else:
            ratio = 1.0
        width = 28
        filled = int(width * ratio)
        bar = "#" * filled + "-" * (width - filled)
        percent = int(ratio * 100)
        name = current_name.replace("\n", " ")[:40]
        line = (
            f"[{bar}] {percent:3d}%  {files_done}/{self.total_files}  "
            f"{format_bytes(bytes_done)} / {format_bytes(self.total_bytes)}  {name}"
        )
        padded = line + (" " * max(self._last_len - len(line), 0))
        self._last_len = len(line)
        print(f"\r{padded}", end="", file=self.stream, flush=True)

    def finish(self) -> None:
        if not self.enabled:
            return
        self.update(self.total_files, self.total_bytes, "")
        print(file=self.stream, flush=True)
