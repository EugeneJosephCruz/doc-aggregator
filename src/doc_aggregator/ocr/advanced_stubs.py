"""Optional advanced OCR backends."""

from __future__ import annotations

from pathlib import Path


def ocr_with_mistral(image_path: Path) -> str:
    """Advanced OCR hook.

    Expected contract:
    - input: local image path
    - output: extracted plain text
    """
    raise NotImplementedError("Implement Mistral OCR integration in this hook.")


def ocr_with_textract(image_path: Path) -> str:
    """Advanced OCR hook.

    Expected contract:
    - input: local image path
    - output: extracted plain text
    """
    raise NotImplementedError("Implement AWS Textract integration in this hook.")
