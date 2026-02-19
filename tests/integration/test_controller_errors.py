from __future__ import annotations

from pathlib import Path

import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.controller import DocumentAggregator
from doc_aggregator.utils.manifest import ManifestStore


@pytest.mark.integration
def test_corrupt_input_file_logs_error_and_continues(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "good.txt").write_text("good data", encoding="utf-8")
    (input_dir / "bad.pdf").write_bytes(b"not a real pdf")

    output_dir = tmp_path / "out"
    aggregator = DocumentAggregator(input_dir, output_dir, AggregatorConfig())
    aggregator.run()

    assert (output_dir / "aggregated.docx").exists()
    manifest = ManifestStore(output_dir / ".cache" / "manifest.jsonl")
    statuses = sorted(record.status for record in manifest.records.values())
    assert statuses == ["done", "error"]
