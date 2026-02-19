from __future__ import annotations

import logging
from pathlib import Path

import pytest
from docx import Document

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ingestion import txt_reader


@pytest.mark.integration
def test_txt_encoding_detection_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_bytes("caf\xe9".encode("latin-1"))
    segment = tmp_path / "segment.docx"

    def fake_detect(_: bytes) -> dict[str, object]:
        return {"encoding": "utf-8", "confidence": 0.1}

    monkeypatch.setattr(txt_reader.chardet, "detect", fake_detect)

    result = txt_reader.process_txt_file(
        source_path=source,
        display_name="sample.txt",
        segment_path=segment,
        config=AggregatorConfig(),
        logger=logging.getLogger("test_txt_encoding_detection_fallback"),
    )

    assert result["ocr_used"] is False
    assert segment.exists()
    doc = Document(str(segment))
    content = "\n".join(p.text for p in doc.paragraphs)
    assert "sample.txt" in content
