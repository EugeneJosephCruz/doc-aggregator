"""CLI entry point for doc-aggregator."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from doc_aggregator.config import AggregatorConfig
from doc_aggregator.controller import DocumentAggregator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doc-aggregator")
    parser.add_argument("input_dir", nargs="?", default=".")
    parser.add_argument("-o", "--output-dir", default=None)
    parser.add_argument("-n", "--output-name", default=None)
    parser.add_argument("--pdf", action="store_true", help="Merge PDFs directly into a PDF")

    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open")

    parser.add_argument("--ocr-dpi", type=int, default=None)
    parser.add_argument("--max-file-size-mb", type=float, default=None)
    parser.add_argument("--no-strip-external", action="store_true")

    parser.add_argument("--log-file", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def resolve_output_dir(args: argparse.Namespace, input_dir: Path) -> Path:
    if args.output_dir:
        return Path(args.output_dir).expanduser().resolve()

    if args.resume:
        existing = sorted(input_dir.glob("_doc_aggregator_output*"))
        if existing:
            return existing[-1].resolve()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    return (input_dir / f"_doc_aggregator_output_{timestamp}").resolve()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = resolve_output_dir(args, input_dir)
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else None

    config = AggregatorConfig.from_cli(args)
    aggregator = DocumentAggregator(
        input_dir=input_dir,
        output_dir=output_dir,
        config=config,
        resume=args.resume,
        log_file=log_file,
    )

    if args.dry_run:
        aggregator.dry_run()
    else:
        aggregator.run()
        if config.auto_open and aggregator.output_path.exists():
            try:
                subprocess.run(["open", str(aggregator.output_path)], check=False)
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    main()
