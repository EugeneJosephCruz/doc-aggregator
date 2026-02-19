from __future__ import annotations

from pathlib import Path

import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.controller import DocumentAggregator


class _FailingDoc:
    def save(self, *_args, **_kwargs) -> None:
        raise RuntimeError("intentional failure")


class _ComposerStub:
    def __init__(self, _config) -> None:
        pass

    def merge_all(self, _segments):
        return _FailingDoc()


@pytest.mark.unit
def test_atomic_output_write_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    aggregator = DocumentAggregator(input_dir, output_dir, AggregatorConfig())
    original = aggregator.output_path
    original.write_bytes(b"old-content")

    import doc_aggregator.controller as controller_module

    monkeypatch.setattr(controller_module, "FinalComposer", _ComposerStub)
    monkeypatch.setattr(controller_module, "insert_toc", lambda *_a, **_k: None)
    monkeypatch.setattr(controller_module, "sanitize_relationships", lambda *_a, **_k: [])

    with pytest.raises(RuntimeError):
        aggregator.compose_final([])

    assert original.read_bytes() == b"old-content"
