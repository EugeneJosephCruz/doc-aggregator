"""Logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(
    output_dir: Path,
    *,
    verbose: bool = False,
    log_file: Path | None = None,
) -> tuple[logging.Logger, Path]:
    """Configure and return app logger and file path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_file or (output_dir / "processing.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("doc_aggregator")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, log_path
