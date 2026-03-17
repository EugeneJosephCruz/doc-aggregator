from __future__ import annotations

import logging
from pathlib import Path

import fitz
import pytest

import doc_aggregator.structuring.pdf_composer as pdf_composer
from doc_aggregator.structuring.pdf_composer import merge_pdfs
from doc_aggregator.utils.files import ScannedFile
from tests.conftest import create_multi_page_pdf, create_text_pdf


def _scanned_file(path: Path, root: Path, *, display_name: str | None = None) -> ScannedFile:
    stat = path.stat()
    return ScannedFile(
        path=path.resolve(),
        relative_path=str(path.relative_to(root)),
        display_name=display_name or path.name,
        size=stat.st_size,
        mtime=stat.st_mtime,
        inode=stat.st_ino,
    )


@pytest.mark.unit
def test_merge_preserves_total_page_count(tmp_path: Path) -> None:
    root = tmp_path / "input"
    first = create_multi_page_pdf(root / "one.pdf", ["one"])
    second = create_multi_page_pdf(root / "two.pdf", ["two-a", "two-b", "two-c"])
    third = create_multi_page_pdf(root / "three.pdf", ["three-a", "three-b"])
    output = tmp_path / "merged.pdf"

    result = merge_pdfs(
        [_scanned_file(first, root), _scanned_file(second, root), _scanned_file(third, root)],
        output,
        logging.getLogger("test_merge_preserves_total_page_count"),
    )

    with fitz.open(output) as merged:
        assert merged.page_count == 6
    assert result.total_pages == 6
    assert result.merged_files == 3


@pytest.mark.unit
def test_bookmarks_match_display_names(tmp_path: Path) -> None:
    root = tmp_path / "input"
    alpha = create_text_pdf(root / "alpha.pdf", "alpha")
    beta = create_text_pdf(root / "beta.pdf", "beta")
    gamma = create_text_pdf(root / "gamma.pdf", "gamma")
    output = tmp_path / "merged.pdf"

    merge_pdfs(
        [_scanned_file(alpha, root), _scanned_file(beta, root), _scanned_file(gamma, root)],
        output,
        logging.getLogger("test_bookmarks_match_display_names"),
    )

    with fitz.open(output) as merged:
        toc = merged.get_toc()
    assert [entry[1] for entry in toc] == ["alpha.pdf", "beta.pdf", "gamma.pdf"]
    assert [entry[2] for entry in toc] == [1, 2, 3]


@pytest.mark.unit
def test_duplicate_names_can_use_relative_titles(tmp_path: Path) -> None:
    root = tmp_path / "input"
    first = create_text_pdf(root / "a" / "same.pdf", "first")
    second = create_text_pdf(root / "b" / "same.pdf", "second")
    output = tmp_path / "merged.pdf"

    merge_pdfs(
        [
            _scanned_file(first, root, display_name="a/same.pdf"),
            _scanned_file(second, root, display_name="b/same.pdf"),
        ],
        output,
        logging.getLogger("test_duplicate_names_can_use_relative_titles"),
    )

    with fitz.open(output) as merged:
        toc = merged.get_toc()
    assert [entry[1] for entry in toc] == ["a/same.pdf", "b/same.pdf"]


@pytest.mark.unit
def test_empty_input_raises(tmp_path: Path) -> None:
    output = tmp_path / "merged.pdf"

    with pytest.raises(ValueError, match="No PDF files were provided"):
        merge_pdfs([], output, logging.getLogger("test_empty_input_raises"))

    assert not output.exists()


@pytest.mark.unit
def test_non_pdf_input_raises(tmp_path: Path) -> None:
    root = tmp_path / "input"
    root.mkdir()
    non_pdf = root / "notes.txt"
    non_pdf.write_text("not a pdf", encoding="utf-8")
    output = tmp_path / "merged.pdf"

    with pytest.raises(ValueError, match="Non-PDF source"):
        merge_pdfs(
            [_scanned_file(non_pdf, root)],
            output,
            logging.getLogger("test_non_pdf_input_raises"),
        )

    assert not output.exists()


@pytest.mark.unit
def test_corrupted_pdf_is_skipped_without_partial_failure(tmp_path: Path) -> None:
    root = tmp_path / "input"
    valid_one = create_text_pdf(root / "one.pdf", "one")
    corrupted = root / "broken.pdf"
    corrupted.write_bytes(b"not a pdf")
    valid_two = create_text_pdf(root / "two.pdf", "two")
    output = tmp_path / "merged.pdf"

    result = merge_pdfs(
        [
            _scanned_file(valid_one, root),
            _scanned_file(corrupted, root),
            _scanned_file(valid_two, root),
        ],
        output,
        logging.getLogger("test_corrupted_pdf_is_skipped_without_partial_failure"),
    )

    with fitz.open(output) as merged:
        assert merged.page_count == 2
    assert result.merged_files == 2
    assert result.failed_files == 1


@pytest.mark.unit
def test_zero_valid_sources_raises(tmp_path: Path) -> None:
    root = tmp_path / "input"
    corrupted = root / "broken.pdf"
    corrupted.parent.mkdir(parents=True, exist_ok=True)
    corrupted.write_bytes(b"not a pdf")
    output = tmp_path / "merged.pdf"

    with pytest.raises(ValueError, match="No valid PDF files were merged"):
        merge_pdfs(
            [_scanned_file(corrupted, root)],
            output,
            logging.getLogger("test_zero_valid_sources_raises"),
        )

    assert not output.exists()


class _SaveFailDoc:
    def __init__(self, real_open) -> None:
        self._doc = real_open()

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def insert_pdf(self, source_doc) -> None:  # noqa: ANN001
        self._doc.insert_pdf(source_doc)

    def set_toc(self, toc) -> None:  # noqa: ANN001
        self._doc.set_toc(toc)

    def save(self, *_args, **_kwargs) -> None:
        raise RuntimeError("intentional save failure")

    def close(self) -> None:
        self._doc.close()


@pytest.mark.unit
def test_atomic_write_cleans_tmp_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_open = fitz.open
    root = tmp_path / "input"
    source = create_text_pdf(root / "one.pdf", "one")
    output = tmp_path / "merged.pdf"
    tmp_output = output.with_suffix(".tmp")

    def fail_on_merged_open(*args, **kwargs):  # noqa: ANN002, ANN003
        if not args and not kwargs:
            return _SaveFailDoc(real_open)
        return real_open(*args, **kwargs)

    monkeypatch.setattr(pdf_composer.fitz, "open", fail_on_merged_open)

    with pytest.raises(RuntimeError, match="intentional save failure"):
        merge_pdfs(
            [_scanned_file(source, root)],
            output,
            logging.getLogger("test_atomic_write_cleans_tmp_on_failure"),
        )

    assert not output.exists()
    assert not tmp_output.exists()
