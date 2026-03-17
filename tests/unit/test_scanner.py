from __future__ import annotations

import logging
from pathlib import Path

import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.utils.files import PDF_ONLY_EXTENSIONS, scan_supported_files


@pytest.mark.unit
def test_scanner_excludes_output_dirs(tmp_path: Path) -> None:
    (tmp_path / "normal.txt").write_text("ok", encoding="utf-8")
    skipped_dir = tmp_path / "_doc_aggregator_output_2026-01-01_0101"
    skipped_dir.mkdir()
    (skipped_dir / "inside.txt").write_text("skip me", encoding="utf-8")

    logger = logging.getLogger("test_scanner_excludes_output_dirs")
    config = AggregatorConfig()
    files = scan_supported_files(tmp_path, config, logger)

    rel_paths = sorted([f.relative_path for f in files])
    assert rel_paths == ["normal.txt"]


@pytest.mark.unit
def test_scanner_duplicate_name_disambiguation(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "same.txt").write_text("one", encoding="utf-8")
    (tmp_path / "b" / "same.txt").write_text("two", encoding="utf-8")

    logger = logging.getLogger("test_scanner_duplicate_name_disambiguation")
    config = AggregatorConfig()
    files = scan_supported_files(tmp_path, config, logger)

    names = sorted([f.display_name for f in files])
    assert names == ["a/same.txt", "b/same.txt"]


@pytest.mark.unit
def test_scanner_supports_explicit_exclusions(tmp_path: Path) -> None:
    keep = tmp_path / "keep.pdf"
    skip = tmp_path / "skip.pdf"
    keep.write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    skip.write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    logger = logging.getLogger("test_scanner_supports_explicit_exclusions")
    config = AggregatorConfig()
    files = scan_supported_files(
        tmp_path,
        config,
        logger,
        extensions=PDF_ONLY_EXTENSIONS,
        exclude_paths={skip},
    )

    rel_paths = [f.relative_path for f in files]
    assert rel_paths == ["keep.pdf"]
