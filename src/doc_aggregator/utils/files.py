"""Filesystem scanning and TOCTOU helpers."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from doc_aggregator.config import AggregatorConfig

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".docx",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".tiff",
    ".tif",
}


@dataclass(slots=True)
class ScannedFile:
    """Normalized metadata for a discovered file."""

    path: Path
    relative_path: str
    display_name: str
    size: int
    mtime: float
    inode: int


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _is_excluded_dir(dir_name: str, config: AggregatorConfig) -> bool:
    return fnmatch.fnmatch(dir_name, config.excluded_dir_pattern)


def scan_supported_files(
    input_dir: Path,
    config: AggregatorConfig,
    logger,
) -> list[ScannedFile]:
    """Recursively scan input directory with depth/count/size guards."""
    root = input_dir.resolve()
    discovered: list[ScannedFile] = []

    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current_dir, depth = stack.pop()
        if depth > config.max_recursion_depth:
            logger.warning("Skipping %s: exceeded max recursion depth", current_dir)
            continue

        try:
            with os.scandir(current_dir) as it:
                entries = list(it)
        except OSError as exc:
            logger.error("Cannot scan %s: %s", current_dir, exc)
            continue

        entries.sort(key=lambda e: e.name.lower())
        for entry in entries:
            entry_path = Path(entry.path)
            try:
                if entry.is_dir(follow_symlinks=config.follow_symlinks):
                    if _is_excluded_dir(entry.name, config):
                        logger.info("Skipping output directory %s", entry_path)
                        continue
                    stack.append((entry_path, depth + 1))
                    continue

                if not entry.is_file(follow_symlinks=config.follow_symlinks):
                    continue
                if not is_supported_file(entry_path):
                    continue

                stat = entry.stat(follow_symlinks=config.follow_symlinks)
                size_limit = int(config.max_file_size_mb * 1024 * 1024)
                if stat.st_size > size_limit:
                    logger.warning(
                        "Skipping oversized file %s (%d bytes > %d bytes)",
                        entry_path,
                        stat.st_size,
                        size_limit,
                    )
                    continue

                rel = str(entry_path.relative_to(root))
                discovered.append(
                    ScannedFile(
                        path=entry_path.resolve(),
                        relative_path=rel,
                        display_name=entry_path.name,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        inode=stat.st_ino,
                    )
                )

                if len(discovered) >= config.max_file_count:
                    logger.warning(
                        "File discovery capped at max_file_count=%d",
                        config.max_file_count,
                    )
                    return _apply_duplicate_name_disambiguation(discovered)
            except OSError as exc:
                logger.error("Error processing entry %s: %s", entry_path, exc)

    return _apply_duplicate_name_disambiguation(discovered)


def _apply_duplicate_name_disambiguation(files: Iterable[ScannedFile]) -> list[ScannedFile]:
    items = list(files)
    basename_counts: dict[str, int] = {}
    for item in items:
        basename_counts[item.path.name] = basename_counts.get(item.path.name, 0) + 1

    for item in items:
        if basename_counts[item.path.name] > 1:
            item.display_name = item.relative_path
    return items


def validate_file_unchanged(file_meta: ScannedFile) -> bool:
    """Return True when a file still matches metadata captured during scan."""
    try:
        stat = file_meta.path.stat()
    except OSError:
        return False
    return (
        stat.st_size == file_meta.size
        and abs(stat.st_mtime - file_meta.mtime) < 1e-6
        and stat.st_ino == file_meta.inode
    )
