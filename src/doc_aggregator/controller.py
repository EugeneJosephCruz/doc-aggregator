"""Main orchestration for document aggregation."""

from __future__ import annotations

from pathlib import Path

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.ingestion.docx_reader import process_docx_file
from doc_aggregator.ingestion.image_reader import process_image_file
from doc_aggregator.ingestion.pdf_reader import process_pdf_file
from doc_aggregator.ingestion.txt_reader import process_txt_file
from doc_aggregator.structuring.composer import FinalComposer
from doc_aggregator.structuring.pdf_composer import merge_pdfs
from doc_aggregator.structuring.sanitizer import sanitize_relationships
from doc_aggregator.structuring.toc import insert_toc
from doc_aggregator.utils.files import (
    PDF_ONLY_EXTENSIONS,
    ScannedFile,
    scan_supported_files,
    validate_file_unchanged,
)
from doc_aggregator.utils.logging import configure_logging
from doc_aggregator.utils.manifest import ManifestRecord, ManifestStore, compute_sha256


class DocumentAggregator:
    """Coordinates scan -> extract -> cache -> compose workflow."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        config: AggregatorConfig,
        *,
        resume: bool = False,
        log_file: Path | None = None,
    ) -> None:
        self.input_dir = input_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.config = config
        self.resume = resume

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.output_dir / self.config.output_name
        self.cache_dir = self.output_dir / ".cache"
        self.segment_dir = self.cache_dir / "segments"
        self.manifest_path = self.cache_dir / "manifest.jsonl"

        self.logger, self.log_path = configure_logging(
            self.output_dir,
            verbose=config.verbose,
            log_file=log_file,
            enable_file_logging=(config.output_format != "pdf" or log_file is not None),
        )

    def _ensure_docx_workspace(self) -> None:
        self.segment_dir.mkdir(parents=True, exist_ok=True)

    def _scan_excluded_paths(self) -> set[Path]:
        return {
            self.output_path.resolve(),
            self.output_path.with_suffix(".tmp").resolve(),
        }

    def _scan_files(self) -> list[ScannedFile]:
        extensions = PDF_ONLY_EXTENSIONS if self.config.output_format == "pdf" else None
        return scan_supported_files(
            self.input_dir,
            self.config,
            self.logger,
            extensions=extensions,
            exclude_paths=self._scan_excluded_paths(),
        )

    def load_or_create_manifest(self) -> ManifestStore:
        self._ensure_docx_workspace()
        if not self.resume and self.manifest_path.exists():
            self.manifest_path.unlink()
        return ManifestStore(self.manifest_path)

    def scan_and_validate(self, manifest: ManifestStore) -> list[ManifestRecord]:
        scanned = self._scan_files()
        records: list[ManifestRecord] = []

        for order, file_meta in enumerate(scanned):
            existing = manifest.get(file_meta.path)
            if (
                existing
                and existing.status == "done"
                and existing.metadata_matches(file_meta)
                and existing.segment
                and (self.cache_dir / existing.segment).exists()
            ):
                existing.order = order
                manifest.upsert(existing)
                records.append(existing)
                continue

            record = ManifestRecord.from_scanned(file_meta, order=order)
            manifest.upsert(record)
            records.append(record)

        manifest.flush()
        return records

    def validate_before_open(self, record: ManifestRecord) -> None:
        file_meta = ScannedFile(
            path=Path(record.path),
            relative_path=record.rel,
            display_name=record.display_name,
            size=record.size,
            mtime=record.mtime,
            inode=record.inode,
        )
        if not validate_file_unchanged(file_meta):
            raise RuntimeError(
                f"Source file changed between scan and processing: {record.path}"
            )

    def run(self) -> None:
        self.logger.info("Starting aggregation for %s", self.input_dir)
        if self.config.output_format == "pdf":
            self._run_pdf_merge()
            return

        manifest = self.load_or_create_manifest()
        records = self.scan_and_validate(manifest)

        for record in records:
            if record.status == "done":
                self.logger.info("Skipping already completed file %s", record.path)
                continue
            try:
                self.validate_before_open(record)
                sha256 = compute_sha256(Path(record.path))
                segment_rel = f"segments/{sha256}.docx"
                segment_path = self.cache_dir / segment_rel
                result = self._extract_to_segment(
                    Path(record.path),
                    display_name=record.display_name,
                    segment_path=segment_path,
                )
                record.mark_done(
                    sha256=sha256,
                    segment=segment_rel,
                    ocr_used=bool(result.get("ocr_used", False)),
                )
                self.logger.info("Processed %s", record.path)
            except Exception as exc:  # noqa: BLE001
                record.mark_error(str(exc))
                self.logger.error("Failed processing %s: %s", record.path, exc)
            finally:
                manifest.upsert(record)
                manifest.flush()

        segments = manifest.completed_segments(self.cache_dir)
        self.compose_final(segments)
        self._log_summary(manifest)

    def dry_run(self) -> None:
        scanned = self._scan_files()
        by_ext: dict[str, int] = {}
        for file_meta in scanned:
            suffix = file_meta.path.suffix.lower() or "<none>"
            by_ext[suffix] = by_ext.get(suffix, 0) + 1

        self.logger.info("Dry run summary")
        self.logger.info("Input directory: %s", self.input_dir)
        self.logger.info("Discovered supported files: %d", len(scanned))
        for ext, count in sorted(by_ext.items()):
            self.logger.info("  %s -> %d", ext, count)

    def _run_pdf_merge(self) -> None:
        scanned = self._scan_files()
        if not scanned:
            raise ValueError("No PDF files were discovered for merge")

        result = merge_pdfs(scanned, self.output_path, self.logger)
        self.logger.info("Output written to %s", self.output_path)
        self.logger.info(
            "Summary: merged=%d skipped=%d failed=%d total_pages=%d bookmarks=%d",
            result.merged_files,
            result.skipped_files,
            result.failed_files,
            result.total_pages,
            result.bookmarks,
        )
        if self.log_path is not None:
            self.logger.info("Log file: %s", self.log_path)

    def compose_final(self, segments: list[Path]) -> None:
        composer = FinalComposer(self.config)
        document = composer.merge_all(segments)
        if self.config.strip_external_relationships:
            removed = sanitize_relationships(document)
            if removed:
                self.logger.warning("Removed %d external relationships", len(removed))
        insert_toc(document)

        tmp_output = self.output_path.with_suffix(".tmp")
        document.save(str(tmp_output))
        tmp_output.replace(self.output_path)
        self.logger.info("Output written to %s", self.output_path)

    def _extract_to_segment(
        self,
        source_path: Path,
        *,
        display_name: str,
        segment_path: Path,
    ) -> dict[str, bool]:
        ext = source_path.suffix.lower()
        if ext == ".txt":
            return process_txt_file(
                source_path,
                display_name,
                segment_path,
                self.config,
                self.logger,
            )
        if ext == ".docx":
            return process_docx_file(source_path, display_name, segment_path, self.logger)
        if ext == ".pdf":
            return process_pdf_file(
                source_path,
                display_name,
                segment_path,
                self.config,
                self.logger,
            )
        if ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
            return process_image_file(
                source_path,
                display_name,
                segment_path,
                self.config,
                self.logger,
            )
        raise ValueError(f"Unsupported extension {ext}")

    def _log_summary(self, manifest: ManifestStore) -> None:
        done = 0
        failed = 0
        ocr = 0
        for record in manifest.records.values():
            if record.status == "done":
                done += 1
            elif record.status == "error":
                failed += 1
            if record.ocr_used:
                ocr += 1
        self.logger.info("Summary: processed=%d failed=%d with_ocr=%d", done, failed, ocr)
        if self.log_path is not None:
            self.logger.info("Log file: %s", self.log_path)
