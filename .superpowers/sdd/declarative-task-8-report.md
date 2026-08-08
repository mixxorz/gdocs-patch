# Declarative XHTML Rewrite Task 8 Report

## Status

**PASS.** The XHTML syntax reference is now organized and worded as user-facing documentation, and the design specification describes the completed declarative architecture rather than the earlier implementation plan.

## Changes

- Reworked `docs/xhtml-syntax.md` around format usage, canonical output, document structure, inline content, tables and lists, metadata and validation, the complete enum reference, and the public Python API.
- Preserved all syntax rules, normalization and omission behavior, validation and security limits, enum literals, and XML fragments.
- Reframed the former implementation-oriented model-mapping section as guidance for reading elements, attributes, and metadata.
- Moved the Python API to the end of the reference and retained the public exception and error behavior.
- Updated `docs/superpowers/specs/2026-08-07-xhtml-document-codec-design.md` to describe the final generic declarative tag decoder, declarative attribute codecs, private semantic mapper, and completed behavior-oriented test suite.

## Documentation probe

A direct `serialize_document()` probe for the guide's complete example revealed that the prior XML used readable but noncanonical start-tag wrapping and compact paragraph/anchor content. The example now exactly matches current serializer output, including attribute placement and indentation. This was a documentation discrepancy only; production behavior and tests were not changed.

A preservation probe compared the original and rewritten reference and found:

- no removed enum-like constants;
- the same 40 labeled XML fragments;
- the same 88 Markdown fence delimiters.

## Verification

All required checks passed:

- `uv sync --all-groups`
- `uv run pytest` — 291 passed
- `uv run ruff check .`
- `uv run ruff format --check .` — 74 files already formatted
- `uv run fixit lint .` — 57 files clean
- `uv run pyright` — 0 errors, 0 warnings, 0 informations
- `uv run pre-commit run --all-files` — all hooks passed
- `git diff --check`

## Self-review

- Confirmed the complete example against live serializer output.
- Confirmed every original enum-like literal remains present and the complete enum table is unchanged.
- Confirmed all normalization, error, ordering, unknown-syntax, XML security, character-limit, and depth-limit rules remain documented.
- Confirmed the design architecture matches `nodes.py`, `attributes.py`, `tags.py`, `encoder.py`, and `decoder.py`.
- Confirmed no production or test files changed.

## Concerns

None for Task 8. Two pre-existing modified reports, `.superpowers/sdd/declarative-task-2-report.md` and `.superpowers/sdd/declarative-task-7-report.md`, were intentionally left untouched and excluded from this task's commit.
