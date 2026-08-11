# Task 3 Report: Lower SectionBreak edits and structural boundary cleanup

## Status

Implemented the scoped lowering behavior on `exploratory-google-docs` in the requested worktree.

## Changes

- Updated the existing table lowering test for retained-boundary cleanup.
- Added exactly one SectionBreak lowering test covering insertion, retained-boundary cleanup, sentinel deletion, and writable SectionStyle serialization.
- Lowered `InsertSectionBreak`, `DeleteSectionBreak`, and `ApplySectionStyle` edits.
- Added retained-boundary cleanup after blank table insertion.
- Kept Google side-effect cleanup and deletion sentinel mechanics in lowering with explanatory comments.
- Serialized only concrete writable SectionStyle fields, excluding `sectionType` and header/footer IDs.

## TDD evidence

### Baseline

```text
$ uv run pytest tests/compiler/test_lowering.py -q
3 passed in 0.02s
```

### RED

After changing only the existing table test and adding the one specified SectionBreak test:

```text
$ uv run pytest tests/compiler/test_lowering.py -q
2 failed, 2 passed in 0.06s
```

Expected failures:

- `test_lowers_all_table_edits`: retained-boundary `deleteContentRange` was absent.
- `test_lowers_section_break_edits`: lowering raised `NotImplementedError: InsertSectionBreak`.

### GREEN

After the minimal lowering implementation:

```text
$ uv run pytest tests/compiler/test_lowering.py -q
4 passed in 0.03s
```

## Verification

```text
uv run ruff check .                                      PASS
uv run ruff format --check <changed Python files>        PASS (2 files)
uv run fixit lint .                                      PASS (60 files)
uv run pyright                                           PASS (0 errors)
uv run pre-commit run --all-files                        PASS
uv run pytest -q                                         FAIL (1 failed, 180 passed)
```

Repository-wide `ruff format --check .` also reports a pre-existing formatting finding in the committed Markdown plan `docs/superpowers/plans/2026-08-11-section-break-compilation.md`; both changed Python files pass formatting.

The single full-suite failure is `tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch`. Its hardcoded end-to-end request snapshot predates the newly required retained-boundary table cleanup request. It was not modified because the user explicitly constrained test changes to the existing table lowering test plus exactly one new SectionBreak lowering test.

## Scope check

Changed implementation: `gdocs_patch/compiler/lowering.py`.
Changed tests: only `tests/compiler/test_lowering.py`; exactly one test function was added.
