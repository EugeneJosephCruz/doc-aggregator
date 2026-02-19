"""Language detection and OCR language mapping."""

from __future__ import annotations

from collections.abc import Iterable

from langdetect import DetectorFactory, detect_langs

from doc_aggregator.config import AggregatorConfig

LANG_MAP = {
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "nl": "nld",
}


def detect_ocr_language(
    text: str,
    config: AggregatorConfig,
    available_languages: Iterable[str] | None = None,
) -> str:
    """Choose a tesseract language code from text, with conservative fallbacks."""
    clean = text.strip()
    if len(clean) < config.langdetect_min_chars:
        return config.default_ocr_lang

    DetectorFactory.seed = config.langdetect_seed
    try:
        result = detect_langs(clean)[0]
    except Exception:
        return config.default_ocr_lang

    if result.prob < config.langdetect_min_confidence:
        return config.default_ocr_lang

    mapped = LANG_MAP.get(result.lang, config.default_ocr_lang)
    if available_languages is None:
        return mapped
    return mapped if mapped in set(available_languages) else config.default_ocr_lang
