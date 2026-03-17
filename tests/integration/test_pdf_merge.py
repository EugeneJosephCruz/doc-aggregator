from __future__ import annotations

import logging
import os
from pathlib import Path

import fitz
import pytest

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.controller import DocumentAggregator
from doc_aggregator.utils.files import PDF_ONLY_EXTENSIONS, scan_supported_files
from tests.conftest import create_multi_page_pdf, create_text_pdf, create_txt


def _pdf_config(output_name: str = "aggregated.pdf") -> AggregatorConfig:
    config = AggregatorConfig(output_format="pdf", output_name=output_name)
    config.validate()
    return config


@pytest.mark.integration
def test_pdf_mode_merges_generated_fixture_set(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_text_pdf(input_dir / "one.pdf", "one")
    create_multi_page_pdf(input_dir / "two.pdf", ["two-a", "two-b"])
    create_multi_page_pdf(input_dir / "three.pdf", ["three-a", "three-b", "three-c"])

    output_dir = tmp_path / "out"
    aggregator = DocumentAggregator(input_dir, output_dir, _pdf_config())
    aggregator.run()

    with fitz.open(aggregator.output_path) as merged:
        assert merged.page_count == 6


@pytest.mark.integration
def test_pdf_mode_skips_output_file_on_rerun(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_text_pdf(input_dir / "one.pdf", "one")
    create_text_pdf(input_dir / "two.pdf", "two")

    config = _pdf_config()
    first = DocumentAggregator(input_dir, input_dir, config)
    first.run()

    second = DocumentAggregator(input_dir, input_dir, config)
    second.run()

    with fitz.open(second.output_path) as merged:
        assert merged.page_count == 2


@pytest.mark.integration
def test_pdf_mode_does_not_create_cache_or_manifest(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_text_pdf(input_dir / "one.pdf", "one")
    create_text_pdf(input_dir / "two.pdf", "two")
    before = {path.name for path in input_dir.iterdir()}

    aggregator = DocumentAggregator(input_dir, input_dir, _pdf_config())
    aggregator.run()

    after = {path.name for path in input_dir.iterdir()}
    assert after - before == {"aggregated.pdf"}
    assert not (input_dir / ".cache").exists()
    assert not (input_dir / "manifest.jsonl").exists()
    assert not (input_dir / "processing.log").exists()


@pytest.mark.integration
def test_pdf_mode_skips_broken_pdf_and_logs_warning(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_text_pdf(input_dir / "good.pdf", "good")
    (input_dir / "broken.pdf").write_bytes(b"not a real pdf")

    output_dir = tmp_path / "out"
    log_file = tmp_path / "run.log"
    aggregator = DocumentAggregator(input_dir, output_dir, _pdf_config(), log_file=log_file)
    aggregator.run()

    with fitz.open(aggregator.output_path) as merged:
        assert merged.page_count == 1
    assert "Skipping unreadable PDF" in log_file.read_text(encoding="utf-8")


@pytest.mark.integration
def test_pdf_mode_overwrite_is_stable(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_text_pdf(input_dir / "one.pdf", "one")
    create_text_pdf(input_dir / "two.pdf", "two")
    output_path = input_dir / "aggregated.pdf"
    output_path.write_bytes(b"old invalid content")

    aggregator = DocumentAggregator(input_dir, input_dir, _pdf_config())
    aggregator.run()

    with fitz.open(output_path) as merged:
        assert merged.page_count == 2


@pytest.mark.integration
def test_existing_docx_mode_still_produces_docx(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    create_txt(input_dir / "notes.txt", "hello world")

    output_dir = tmp_path / "out"
    aggregator = DocumentAggregator(input_dir, output_dir, AggregatorConfig())
    aggregator.run()

    assert (output_dir / "aggregated.docx").exists()


@pytest.mark.integration
def test_local_pdf_corpus_acceptance(tmp_path: Path) -> None:
    corpus = os.environ.get("DOC_AGGREGATOR_LOCAL_PDF_CORPUS")
    if not corpus:
        pytest.skip("DOC_AGGREGATOR_LOCAL_PDF_CORPUS is not set")

    input_dir = Path(corpus).expanduser().resolve()
    if not input_dir.exists():
        pytest.skip("Local PDF corpus path does not exist")

    output_dir = tmp_path / "out"
    config = _pdf_config("milestone-b-aggregated.pdf")
    aggregator = DocumentAggregator(input_dir, output_dir, config)
    aggregator.run()

    with fitz.open(aggregator.output_path) as merged:
        toc = merged.get_toc()
        assert merged.page_count == 16
        assert len(toc) == 16

    scanned = scan_supported_files(
        input_dir,
        config,
        logging.getLogger("test_local_pdf_corpus_acceptance"),
        extensions=PDF_ONLY_EXTENSIONS,
        exclude_paths={aggregator.output_path},
    )
    expected_titles = [item.display_name for item in scanned]
    assert [entry[1] for entry in toc] == expected_titles

    output_size = aggregator.output_path.stat().st_size
    input_sizes = [path.stat().st_size for path in input_dir.glob("*.pdf")]
    assert output_size > max(input_sizes)
    assert output_size < sum(input_sizes) * 2
