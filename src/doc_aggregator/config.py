"""Configuration models for doc-aggregator."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(slots=True)
class AggregatorConfig:
    """Tunable runtime settings."""

    # Scanning
    max_file_count: int = 5000
    max_file_size_mb: float = 200.0
    max_recursion_depth: int = 20
    follow_symlinks: bool = False
    excluded_dir_pattern: str = "_doc_aggregator_output*"

    # PDF OCR trigger
    text_coverage_threshold: float = 0.05
    ocr_dpi: int = 300
    max_ocr_pixels: int = 25_000_000
    ocr_page_timeout_sec: int = 60
    max_pdf_pages: int = 2000

    # Language detection
    langdetect_seed: int = 0
    langdetect_min_chars: int = 50
    langdetect_min_confidence: float = 0.8
    default_ocr_lang: str = "eng"

    # Output
    output_name: str = "aggregated.docx"
    strip_external_relationships: bool = True
    auto_open: bool = False

    # Logging
    verbose: bool = False

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> "AggregatorConfig":
        """Build config from parsed CLI args."""
        cfg = cls()

        if getattr(args, "ocr_dpi", None):
            cfg.ocr_dpi = int(args.ocr_dpi)
        if getattr(args, "max_file_size_mb", None):
            cfg.max_file_size_mb = float(args.max_file_size_mb)
        if getattr(args, "output_name", None):
            cfg.output_name = str(args.output_name)
        if getattr(args, "no_strip_external", False):
            cfg.strip_external_relationships = False
        if getattr(args, "verbose", False):
            cfg.verbose = True
        if getattr(args, "open", False):
            cfg.auto_open = True

        cfg.validate()
        return cfg

    def validate(self) -> None:
        """Validate settings and raise ValueError when invalid."""
        if self.max_file_count <= 0:
            raise ValueError("max_file_count must be > 0")
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be > 0")
        if self.max_recursion_depth < 0:
            raise ValueError("max_recursion_depth must be >= 0")
        if self.ocr_dpi <= 0:
            raise ValueError("ocr_dpi must be > 0")
        if self.max_ocr_pixels <= 0:
            raise ValueError("max_ocr_pixels must be > 0")
        if self.ocr_page_timeout_sec <= 0:
            raise ValueError("ocr_page_timeout_sec must be > 0")
        if self.max_pdf_pages <= 0:
            raise ValueError("max_pdf_pages must be > 0")
        if not self.output_name.lower().endswith(".docx"):
            raise ValueError("output_name must end with .docx")
