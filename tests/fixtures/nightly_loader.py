"""Optional external corpus loader for nightly OCR/perf tests."""

from __future__ import annotations

import os
import tarfile
import urllib.request
import zipfile
from pathlib import Path


def load_external_corpus(destination: Path) -> Path:
    """Load nightly corpus from env-configured path or URL.

    Supported environment variables:
    - DOC_AGGREGATOR_NIGHTLY_CORPUS_PATH: local .zip/.tar.gz archive
    - DOC_AGGREGATOR_NIGHTLY_CORPUS_URL: remote .zip/.tar.gz URL
    """
    destination.mkdir(parents=True, exist_ok=True)

    local_path = os.environ.get("DOC_AGGREGATOR_NIGHTLY_CORPUS_PATH")
    remote_url = os.environ.get("DOC_AGGREGATOR_NIGHTLY_CORPUS_URL")

    if local_path:
        archive = Path(local_path).expanduser().resolve()
        if not archive.exists():
            raise FileNotFoundError(f"Nightly corpus archive not found: {archive}")
        return _extract_archive(archive, destination)

    if remote_url:
        target = destination / "nightly_corpus_download"
        urllib.request.urlretrieve(remote_url, target)  # noqa: S310
        return _extract_archive(target, destination)

    raise RuntimeError(
        "Set DOC_AGGREGATOR_NIGHTLY_CORPUS_PATH or DOC_AGGREGATOR_NIGHTLY_CORPUS_URL"
    )


def _extract_archive(archive: Path, destination: Path) -> Path:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(destination)
        return destination
    if archive.suffixes[-2:] == [".tar", ".gz"] or archive.suffix == ".tgz":
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(destination)
        return destination
    raise ValueError(f"Unsupported nightly corpus archive type: {archive.name}")
