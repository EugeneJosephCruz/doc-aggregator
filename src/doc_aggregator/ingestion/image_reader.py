"""Image ingestion using OCR pipeline."""

from __future__ import annotations

from pathlib import Path

import cv2

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ocr.preprocessor import preprocess_for_ocr
from doc_aggregator.ocr.tesseract_ocr import run_tesseract_ocr
from doc_aggregator.structuring.segment import create_text_segment


def process_image_file(
    source_path: Path,
    display_name: str,
    segment_path: Path,
    config: AggregatorConfig,
    logger,
    *,
    lang_hint: str | None = None,
) -> dict[str, bool]:
    """Extract text from an image and write a segment docx."""
    image = cv2.imread(str(source_path))
    if image is None:
        raise ValueError(f"Cannot decode image file: {source_path}")

    pixels = int(image.shape[0]) * int(image.shape[1])
    if pixels > config.max_ocr_pixels:
        raise ValueError(
            f"Image pixel count {pixels} exceeds max_ocr_pixels {config.max_ocr_pixels}"
        )

    preprocessed = preprocess_for_ocr(image)
    text, lang_used = run_tesseract_ocr(preprocessed, config, lang_hint=lang_hint)
    logger.info("OCR image %s using language '%s'", source_path, lang_used)
    create_text_segment(display_name, text, segment_path)
    return {"ocr_used": True}
