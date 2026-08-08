# Declarative XHTML Rewrite Task 3 Report

## Status

Implemented Task 3 on `feature/xhtml-document-codec`.

## Changes

- Added declarative body, section, complete section-style, columns, header/footer/footnote collection and item, table-of-contents, and structural boundary tags in `gdocs_patch/xhtml/tags.py`.
- Added lazy structural child declarations for paragraph variants, lists, tables, table-of-contents, and body-only sections.
- Changed body encoding to group each `SectionBreak` and following structures into a `SectionTag`; decoding flattens sections back to model order.
- Changed region encoding/decoding to preserve absent versus empty wrappers and keep dictionary keys independent from `Segment.segment_id`.
- Changed recursive structural dispatch to consume and produce declarative `Tag` objects, including recursive table-of-contents content.
- Removed the Task 2 body/segment wrapper rendering bridges and superseded section/segment/structural ElementTree dispatch code.
- Retained opaque, model-agnostic paragraph/list/table payload boundaries for later vocabulary tasks; section, region, and TOC mapper methods no longer construct or parse XML directly.
- Preserved validation ordering and useful paths, including repeated span indices and section-only body diagnostics.

## Verification

- `uv run pytest -q` — 258 passed.
- `uv run ruff check . && uv run ruff format --check gdocs_patch tests` — passed; 54 files formatted.
- `uv run pyright && uv run fixit lint .` — 0 errors/warnings; 57 files clean.
- `uv run pre-commit run --all-files` — all five hooks passed.
- `git diff --check` — passed.

## Self-review

- Confirmed mapper imports follow `from gdocs_patch import models` / `from . import tags` and module-qualified bindings.
- Confirmed `tags.py` imports no model classes.
- Confirmed absent and empty region/column wrappers remain distinct.
- Confirmed section styles can appear in any valid child order while encoding remains canonical.
- Confirmed the pre-existing uncommitted `.superpowers/sdd/declarative-task-2-report.md` change is unrelated and excluded from this task commit.

## Concerns

No known functional concerns. Paragraph/list/table internals intentionally remain opaque declarative boundary payloads pending their dedicated migration tasks.

## Review Fixes

- Tightened `DocumentBodyTag` to declaratively require one or more `SectionTag` children and removed the decoder's unchecked section cast.
- Added child-cardinality preflight so duplicate wrappers are reported before malformed nested wrapper content without weakening the body grammar.
- Changed `TableOfContentsTag` to exclude `SectionTag` from its declared alternatives while preserving the established body-only-section diagnostic.
- Converted unknown opaque table-cell structures to contextual `XHTMLParseError` failures instead of leaking `KeyError`.
- Removed obsolete section enum constants from the mapper modules.
- Added two focused public malformed-input regressions for the prior `AttributeError` and `KeyError` leaks.

Review verification:

- Focused XHTML validation/document/structure suite: 89 passed.
- Full pytest suite: 260 passed.
- Ruff lint/format, Fixit, Pyright, and all pre-commit hooks passed.
