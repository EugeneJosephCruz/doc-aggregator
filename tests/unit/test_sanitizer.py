from __future__ import annotations

import pytest

from doc_aggregator.structuring.sanitizer import sanitize_relationships


class _Rel:
    def __init__(self, is_external: bool, target_ref: str) -> None:
        self.is_external = is_external
        self.target_ref = target_ref


class _Part:
    def __init__(self) -> None:
        self.rels = {
            "rId1": _Rel(True, "http://example.com"),
            "rId2": _Rel(False, "internal"),
        }
        self.removed: list[str] = []

    def drop_rel(self, rel_id: str) -> None:
        self.removed.append(rel_id)
        self.rels.pop(rel_id, None)


class _Package:
    def __init__(self, part: _Part) -> None:
        self.parts = [part]


class _DocPart:
    def __init__(self, package: _Package) -> None:
        self.package = package


class _Doc:
    def __init__(self, package: _Package) -> None:
        self.part = _DocPart(package)


@pytest.mark.unit
def test_external_relationships_are_stripped() -> None:
    part = _Part()
    doc = _Doc(_Package(part))
    removed = sanitize_relationships(doc)  # type: ignore[arg-type]

    assert removed == ["http://example.com"]
    assert part.removed == ["rId1"]
