"""Native PDF merge composer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import fitz

from doc_aggregator.utils.files import ScannedFile, validate_file_unchanged


@dataclass(slots=True)
class PDFMergeResult:
    """Summary of a native PDF merge run."""

    merged_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    total_pages: int = 0
    bookmarks: int = 0


def merge_pdfs(
    sources: Sequence[ScannedFile],
    output_path: Path,
    logger,
    *,
    add_bookmarks: bool = True,
) -> PDFMergeResult:
    """Merge ordered PDF sources into a single output file."""
    if not sources:
        raise ValueError("No PDF files were provided for merge")

    result = PDFMergeResult()
    tmp_output = output_path.with_suffix(".tmp")
    if tmp_output.exists():
        tmp_output.unlink()

    merged = fitz.open()
    toc: list[list[int | str]] = []
    try:
        for source in sources:
            if source.path.suffix.lower() != ".pdf":
                raise ValueError(f"Non-PDF source passed to merge_pdfs: {source.path}")
            if not validate_file_unchanged(source):
                result.failed_files += 1
                logger.warning(
                    "Skipping changed PDF %s: source changed between scan and processing",
                    source.path,
                )
                continue

            try:
                with fitz.open(str(source.path)) as source_doc:
                    if source_doc.needs_pass:
                        result.skipped_files += 1
                        logger.warning("Skipping encrypted PDF %s", source.path)
                        continue
                    if source_doc.page_count <= 0:
                        result.skipped_files += 1
                        logger.warning("Skipping empty PDF %s", source.path)
                        continue

                    start_page = merged.page_count + 1
                    merged.insert_pdf(source_doc)
                    result.merged_files += 1
                    result.total_pages = merged.page_count
                    if add_bookmarks:
                        toc.append([1, source.display_name, start_page])
            except (fitz.FileDataError, ValueError, RuntimeError) as exc:
                result.failed_files += 1
                logger.warning("Skipping unreadable PDF %s: %s", source.path, exc)
            except Exception as exc:  # noqa: BLE001
                result.failed_files += 1
                logger.warning("Skipping PDF %s due to merge error: %s", source.path, exc)

        if result.merged_files == 0 or merged.page_count == 0:
            raise ValueError("No valid PDF files were merged")

        if add_bookmarks and toc:
            merged.set_toc(toc)
            result.bookmarks = len(toc)

        merged.save(str(tmp_output))
        tmp_output.replace(output_path)
        return result
    except Exception:
        if tmp_output.exists():
            tmp_output.unlink()
        raise
    finally:
        merged.close()
