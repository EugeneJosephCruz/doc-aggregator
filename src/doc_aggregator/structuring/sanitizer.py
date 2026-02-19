"""Security sanitization helpers for composed docx files."""

from __future__ import annotations

from docx.document import Document


def sanitize_relationships(document: Document) -> list[str]:
    """Remove external relationships from all parts and return stripped URLs."""
    removed_targets: list[str] = []
    package = document.part.package

    for part in package.parts:
        for rel_id, rel in list(part.rels.items()):
            if not rel.is_external:
                continue
            removed_targets.append(rel.target_ref)
            part.drop_rel(rel_id)
    return removed_targets
