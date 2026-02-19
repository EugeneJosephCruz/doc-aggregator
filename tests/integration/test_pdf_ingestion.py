from __future__ import annotations

import logging
from pathlib import Path

import fitz
import pytest
from docx import Document

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ingestion import pdf_reader


def _create_text_pdf(path: Path, text: str) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def _create_blank_pdf(path: Path) -> Path:
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


@pytest.mark.integration
def test_pdf_text_page_skips_ocr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = _create_text_pdf(tmp_path / "text.pdf", "hello text layer")
    segment = tmp_path / "segment.docx"

    def fail_ocr(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("OCR should not run for a text-rich page")

    monkeypatch.setattr(pdf_reader, "_ocr_page", fail_ocr)

    result = pdf_reader.process_pdf_file(
        source_path=source,
        display_name="text.pdf",
        segment_path=segment,
        config=AggregatorConfig(text_coverage_threshold=0.0),
        logger=logging.getLogger("test_pdf_text_page_skips_ocr"),
    )

    assert result["ocr_used"] is False
    assert segment.exists()


@pytest.mark.integration
def test_pdf_image_page_triggers_ocr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = _create_blank_pdf(tmp_path / "scan.pdf")
    segment = tmp_path / "scan_segment.docx"

    monkeypatch.setattr(pdf_reader, "_ocr_page", lambda *a, **k: "ocr text from page")

    result = pdf_reader.process_pdf_file(
        source_path=source,
        display_name="scan.pdf",
        segment_path=segment,
        config=AggregatorConfig(),
        logger=logging.getLogger("test_pdf_image_page_triggers_ocr"),
    )

    assert result["ocr_used"] is True
    doc = Document(str(segment))
    content = "\n".join(p.text for p in doc.paragraphs)
    assert "ocr text from page" in content
