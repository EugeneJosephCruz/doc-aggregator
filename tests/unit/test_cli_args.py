from __future__ import annotations

from pathlib import Path

import pytest

from doc_aggregator.__main__ import build_parser, resolve_output_dir


@pytest.mark.unit
def test_cli_defaults_to_current_dir() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.input_dir == "."


@pytest.mark.unit
def test_cli_creates_timestamped_output_dir(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args([])
    output_dir = resolve_output_dir(args, tmp_path)

    assert output_dir.parent == tmp_path
    assert output_dir.name.startswith("_doc_aggregator_output_")
