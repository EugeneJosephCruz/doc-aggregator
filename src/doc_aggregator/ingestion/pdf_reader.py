"""PDF ingestion with text extraction and OCR fallback."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import cv2
import fitz
import numpy as np

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ocr.preprocessor import preprocess_for_ocr
from doc_aggregator.ocr.tesseract_ocr import get_available_languages, run_tesseract_ocr
from doc_aggregator.structuring.segment import create_text_segment
from doc_aggregator.utils.language import detect_ocr_language


def process_pdf_file(
    source_path: Path,
    display_name: str,
    segment_path: Path,
    config: AggregatorConfig,
    logger,
) -> dict[str, bool]:
    """Extract text from PDFs, OCR pages with little/no selectable text."""
    pages_text: list[str] = []
    ocr_used = False
    available_langs = get_available_languages()
    lang_hint = config.default_ocr_lang

    with fitz.open(str(source_path)) as pdf_doc:
        page_count = min(pdf_doc.page_count, config.max_pdf_pages)
        if pdf_doc.page_count > config.max_pdf_pages:
            logger.warning(
                "PDF %s truncated from %d to %d pages",
                source_path,
                pdf_doc.page_count,
                config.max_pdf_pages,
            )

        for page_index in range(page_count):
            page = pdf_doc[page_index]
            extracted_text = page.get_text("text") or ""

            if should_ocr_page(page, extracted_text, config):
                page_text = _ocr_page(page, config, logger, lang_hint=lang_hint)
                ocr_used = True
            else:
                page_text = extracted_text

            page_text = page_text.strip()
            pages_text.append(page_text)
            if page_text:
                lang_hint = detect_ocr_language(
                    page_text,
                    config,
                    available_languages=available_langs,
                )

    joined = "\n\n".join(text for text in pages_text if text)
    create_text_segment(display_name, joined, segment_path)
    return {"ocr_used": ocr_used}


def should_ocr_page(page: fitz.Page, extracted_text: str, config: AggregatorConfig) -> bool:
    """Decide OCR fallback based on text presence and estimated text coverage."""
    text = extracted_text.strip()
    if not text:
        return True

    page_area = max(float(page.rect.width * page.rect.height), 1.0)
    coverage_area = 0.0
    for block in page.get_text("blocks"):
        if len(block) < 5:
            continue
        x0, y0, x1, y1, block_text = block[:5]
        if str(block_text).strip():
            coverage_area += max((x1 - x0) * (y1 - y0), 0.0)

    coverage_ratio = min(coverage_area / page_area, 1.0)
    return coverage_ratio < config.text_coverage_threshold


def _ocr_page(
    page: fitz.Page,
    config: AggregatorConfig,
    logger,
    *,
    lang_hint: str | None = None,
) -> str:
    zoom = config.ocr_dpi / 72.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    if pixmap.width * pixmap.height > config.max_ocr_pixels:
        raise ValueError(
            f"OCR image pixels {pixmap.width * pixmap.height} exceed max_ocr_pixels"
        )

    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )
    if pixmap.n == 4:
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    elif pixmap.n == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    preprocessed = preprocess_for_ocr(image)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_tesseract_ocr, preprocessed, config, lang_hint=lang_hint)
        try:
            text, lang_used = future.result(timeout=config.ocr_page_timeout_sec)
            logger.info("OCR page used language '%s'", lang_used)
            return text
        except concurrent.futures.TimeoutError:
            logger.error("OCR timed out for page %d", page.number)
            return ""
