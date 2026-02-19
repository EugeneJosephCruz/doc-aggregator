from __future__ import annotations

from pathlib import Path

import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.controller import DocumentAggregator


@pytest.mark.integration
def test_manifest_resume_skips_done_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.txt").write_text("hello", encoding="utf-8")

    output_dir = tmp_path / "out"
    cfg = AggregatorConfig()

    first = DocumentAggregator(input_dir, output_dir, cfg, resume=False)
    first.run()
    assert (output_dir / "aggregated.docx").exists()

    second = DocumentAggregator(input_dir, output_dir, cfg, resume=True)

    def should_not_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("Resume should skip already completed files")

    monkeypatch.setattr(second, "_extract_to_segment", should_not_run)
    second.run()
