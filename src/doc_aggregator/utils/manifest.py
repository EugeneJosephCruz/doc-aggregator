"""Manifest persistence for resumable processing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from doc_aggregator.utils.files import ScannedFile


@dataclass(slots=True)
class ManifestRecord:
    """One file's processing lifecycle state."""

    path: str
    rel: str
    display_name: str
    size: int
    mtime: float
    inode: int
    order: int
    sha256: str | None = None
    status: str = "pending"
    ocr_used: bool = False
    segment: str | None = None
    error: str | None = None

    @classmethod
    def from_scanned(cls, scanned: ScannedFile, order: int) -> "ManifestRecord":
        return cls(
            path=str(scanned.path),
            rel=scanned.relative_path,
            display_name=scanned.display_name,
            size=scanned.size,
            mtime=scanned.mtime,
            inode=scanned.inode,
            order=order,
        )

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "ManifestRecord":
        return cls(**payload)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    def metadata_matches(self, scanned: ScannedFile) -> bool:
        return (
            self.size == scanned.size
            and abs(self.mtime - scanned.mtime) < 1e-6
            and self.inode == scanned.inode
        )

    def mark_done(self, sha256: str, segment: str, ocr_used: bool) -> None:
        self.sha256 = sha256
        self.segment = segment
        self.ocr_used = ocr_used
        self.status = "done"
        self.error = None

    def mark_error(self, message: str) -> None:
        self.status = "error"
        self.error = message


class ManifestStore:
    """Append-only JSONL manifest with in-memory latest state per file path."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, ManifestRecord] = {}
        self._pending: list[ManifestRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            record = ManifestRecord.from_json(payload)
            self.records[record.path] = record

    def get(self, file_path: Path) -> ManifestRecord | None:
        return self.records.get(str(file_path.resolve()))

    def upsert(self, record: ManifestRecord) -> None:
        self.records[record.path] = record
        self._pending.append(record)

    def flush(self) -> None:
        if not self._pending:
            return
        with self.path.open("a", encoding="utf-8") as fp:
            for record in self._pending:
                fp.write(json.dumps(record.to_json(), ensure_ascii=True) + "\n")
        self._pending.clear()

    def completed_segments(self, cache_dir: Path) -> list[Path]:
        segments: list[tuple[int, Path]] = []
        for record in self.records.values():
            if record.status != "done" or not record.segment:
                continue
            segment_path = (cache_dir / record.segment).resolve()
            if segment_path.exists():
                segments.append((record.order, segment_path))
        return [path for _, path in sorted(segments, key=lambda x: x[0])]


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 hash for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
