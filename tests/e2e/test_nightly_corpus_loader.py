from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.nightly_loader import load_external_corpus


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.perf
def test_optional_nightly_corpus_loader(tmp_path: Path) -> None:
    if not (
        os.environ.get("DOC_AGGREGATOR_NIGHTLY_CORPUS_PATH")
        or os.environ.get("DOC_AGGREGATOR_NIGHTLY_CORPUS_URL")
    ):
        pytest.skip("No nightly corpus source configured")

    loaded = load_external_corpus(tmp_path / "nightly")
    assert loaded.exists()
