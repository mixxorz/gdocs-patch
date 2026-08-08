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

## Review follow-up

Task 8 review identified documentation accuracy issues, all corrected without production or test changes:

- The design now assigns lexical, composite-attribute, child, cardinality, mixed-text, and syntax-level cross-field validation to declarative attributes, tags, and `Children`. Private model mappers are limited to semantic projections and model construction.
- Text-style fragments now place `g:font-size` before `g:font-family` and `g:font-weight`.
- The `DateElement` fragment now follows serializer order, with `datetime` after `g:time-zone-id`.
- The merged-cell fragment now places `g:cell-key` before `rowspan` and `colspan`.
- The design file map now assigns generated-tree checks, indentation, and rendering to `encoder.py`, and XML preflight, parsing, and public error-path adaptation to `decoder.py`.
- Mapper sketches are explicitly abridged and now preserve actual parameter order, including the decoder's required `path` parameter.

Focused serializer probes printed and checked these canonical forms:

```xml
<span g:font-size="12" g:font-family="Arial" g:font-weight="700">Styled text</span>
<time g:date-id="date-1" g:date-format="DATE_FORMAT_ISO8601" g:time-format="TIME_FORMAT_HOUR_MINUTE" g:display-text="2026-08-08" g:locale="en-US" g:time-zone-id="UTC" datetime="2026-08-08T12:00:00Z" g:bold="true" />
<td g:cell-key="cell-1" rowspan="2" colspan="3" />
```

The corresponding focused tests passed (3 passed): canonical text-style order, canonical styled-date order, and complete recursive-table serialization. Follow-up full verification also passed: 291 tests, Ruff lint/format, Fixit, Pyright, every pre-commit hook, and `git diff --check`.
