from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ingestion import image_reader


@pytest.mark.integration
def test_image_reader_ocr_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    image = np.zeros((100, 240, 3), dtype=np.uint8)
    cv2.putText(image, "Hello", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    cv2.imwrite(str(source), image)

    segment = tmp_path / "segment.docx"
    monkeypatch.setattr(image_reader, "run_tesseract_ocr", lambda *a, **k: ("hello", "eng"))

    result = image_reader.process_image_file(
        source_path=source,
        display_name="sample.png",
        segment_path=segment,
        config=AggregatorConfig(),
        logger=logging.getLogger("test_image_reader_ocr_flow"),
    )

    assert result["ocr_used"] is True
    assert segment.exists()
