"""TXT ingestion with robust encoding handling."""

from __future__ import annotations

from pathlib import Path

import chardet

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.structuring.segment import create_text_segment


def process_txt_file(
    source_path: Path,
    display_name: str,
    segment_path: Path,
    config: AggregatorConfig,
    logger,
) -> dict[str, bool]:
    """Extract text from .txt and write a segment docx."""
    size_limit = int(config.max_file_size_mb * 1024 * 1024)
    raw = source_path.read_bytes()
    if len(raw) > size_limit:
        raise ValueError(f"{source_path} exceeds max_file_size_mb")

    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"
    confidence = float(detected.get("confidence") or 0.0)
    if confidence < 0.5:
        logger.warning(
            "Low encoding confidence (%s) for %s, falling back to utf-8",
            confidence,
            source_path,
        )
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw.decode(encoding, errors="replace")

    create_text_segment(display_name, text, segment_path)
    return {"ocr_used": False}
