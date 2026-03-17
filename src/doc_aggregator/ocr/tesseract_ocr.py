"""Tesseract OCR adapter with language fallback logic."""

from __future__ import annotations

import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytesseract

from doc_aggregator.config import AggregatorConfig


def _resolve_tesseract_cmd() -> None:
    """Ensure pytesseract can find the tesseract binary even without conda activate."""
    if shutil.which("tesseract"):
        return
    env_bin = Path(sys.executable).resolve().parent / "tesseract"
    if env_bin.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(env_bin)


_resolve_tesseract_cmd()


@lru_cache(maxsize=1)
def get_available_languages() -> tuple[str, ...]:
    """Return installed tesseract languages."""
    try:
        langs = tuple(sorted(pytesseract.get_languages(config="")))
    except Exception:
        langs = ()
    return langs


def resolve_language(lang_hint: str | None, config: AggregatorConfig) -> str:
    """Resolve OCR language hint against installed language packs."""
    available = set(get_available_languages())
    default = config.default_ocr_lang
    if not available:
        return lang_hint or default

    if lang_hint and lang_hint in available:
        return lang_hint
    if default in available:
        return default
    return sorted(available)[0]


def run_tesseract_ocr(
    image,
    config: AggregatorConfig,
    *,
    lang_hint: str | None = None,
) -> tuple[str, str]:
    """Run OCR and return tuple of (text, lang_used)."""
    lang = resolve_language(lang_hint, config)
    text = pytesseract.image_to_string(image, lang=lang)
    return text, lang
