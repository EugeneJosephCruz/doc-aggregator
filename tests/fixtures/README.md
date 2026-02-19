# Fixture Corpus

This directory holds a mini corpus for integration and edge-case tests.

## Layout

- `small/txt/` committed text fixtures (UTF-8, low-ASCII)
- `small/docx/`, `small/pdf/`, `small/images/` materialized by `generate_corpus.py`
- `edge/corrupted/` intentionally invalid files
- `edge/oversized/` generated large files for max-size enforcement tests
- `edge/duplicate_names/` duplicate basename samples across subdirectories
- `edge/symlink_cases/` symlink loop/alias samples (platform dependent)

## Generate binary fixtures

Run:

```bash
python tests/fixtures/generate_corpus.py
```

This creates small, deterministic binary files that are intentionally not hand-edited.

## Notes

- The generator is idempotent and safe to re-run.
- Some tests generate additional temporary fixtures in `tmp_path` to avoid mutating this corpus.
