# Declarative XHTML Rewrite Task 7 Report

## Status

Completed the imperative codec cleanup while preserving the public XHTML codec behavior and diagnostics.

## Changes

- Removed dead imperative XML parsers, validators, constants, child extraction, whitespace handling, and number formatting from `gdocs_patch/xhtml/base.py`.
- Moved indentation into the explicit serialization boundary in `encoder.py` and moved tag decoding/error translation out of `_Decoder` into the explicit decode boundary in `decoder.py`.
- Removed the dead paragraph tag compatibility map from `decoder.py`.
- Changed declarative attributes to consume generic attribute mappings, leaving `ElementTree` access in `nodes.py`.
- Generalized child declarations with declarative error, forbidden-child, and positional-path metadata; removed all `ElementTree` overrides from `tags.py`.
- Confirmed `_Encoder` and `_Decoder` mapper classes contain no `ElementTree`, `.attrib`, `.text`, `.tail`, `.set()`, `SubElement`, or raw qualified-tag mechanics.
- Confirmed `tags.py` imports no model module and contains no Document-model mapping logic.
- Preserved module-qualified `models.X` and `tags.XTag` references in core mapper modules.
- Added structural regression tests enforcing the XML and model-layer boundaries.

## Line Counts

Measured against `HEAD` before Task 7 using physical lines and AST class spans:

| Area | Before | After | Change |
|---|---:|---:|---:|
| Core mapper classes (`_Encoder` + `_Decoder`) | 1,414 | 1,384 | -30 |
| Reusable infrastructure (`base.py`, `nodes.py`, `attributes.py`, `tags.py`) | 2,368 | 2,186 | -182 |
| Six codec implementation files | 3,987 | 3,842 | -145 |

The encoder/decoder *files* are 854 and 802 lines respectively because explicit render/security/decode boundary functions remain in those modules but are excluded from the core mapper-class measurement.

## Verification

- Baseline: `uv run pytest -q` — 286 passed.
- TDD red: `uv run pytest -q tests/xhtml/test_declarative_boundary.py` — 3 expected boundary-test failures before cleanup.
- Targeted XHTML suite: `uv run pytest -q tests/xhtml` — 189 passed.
- Full tests: `uv run pytest -q` — 289 passed.
- Ruff lint: `uv run ruff check .` — passed.
- Ruff format: `uv run ruff format --check .` — 74 files formatted.
- Fixit: `uv run fixit lint .` — 57 files clean.
- Pyright: `uv run pyright` — 0 errors, 0 warnings.
- Pre-commit: `uv run pre-commit run --all-files` — all hooks passed.

## Self-review

Reviewed the complete diff and performed AST audits of both mapper classes. `ElementTree` imports now occur only in `nodes.py`, `encoder.py`, and `decoder.py`; uses in encoder/decoder are confined to explicit parse/render/security boundary functions. Existing validation tests continue to assert exact error paths and messages, including positional auto-text paths, table-cell structural errors, duplicate metadata, empty document bodies, and forbidden nested sections.

## Concerns

No implementation concerns remain. A pre-existing unrelated modification to `.superpowers/sdd/declarative-task-2-report.md` was present before Task 7 and is intentionally excluded from this commit.
