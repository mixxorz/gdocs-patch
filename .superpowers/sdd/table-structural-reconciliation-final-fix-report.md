# Table Structural Reconciliation Final Fix Report

## Status

Implemented both final-review anchor fixes on branch `fix/table-structural-reconciliation` in the dedicated worktree. No live Google document was accessed or modified.

## Files

- `gdocs_patch/compiler/edit_script.py`
- `tests/compiler/test_table_edit_script.py`
- `docs/superpowers/specs/2026-08-15-table-structural-reconciliation-design.md`
- `docs/superpowers/plans/2026-08-15-table-structural-reconciliation.md`
- `.superpowers/sdd/table-structural-reconciliation-final-fix-report.md`

## Algorithm and Index Reasoning

### Complete row replacement

The insertion-first path is selected only when the source table has rows, every source row is unmatched, and the target has new rows. Target rows are inserted in ascending target order while an old row still anchors the table. If `T` target rows are inserted, old source row `S[i]` moves to index `T + i`; the compiler therefore deletes old rows in descending source order at those shifted indexes.

For the two-row boundary test, insertion creates `[T0, T1, S0, S1]`, then deletion indexes `3` and `2` remove `S1` and `S0`. Cases with any retained row preserve the existing descending-delete then ascending-insert order.

### Complete column replacement

Within the retained reference row, the insertion-first path is selected only when the source has columns, every source cell is unmatched, and the target has new columns. Target columns are inserted in ascending target order while an old column still anchors the table. If `T` columns are inserted, old source column `S[i]` moves to `T + i`; old columns are deleted in descending source order at those shifted indexes.

For the two-column boundary test, insertion creates `[T0, T1, S0, S1]`, then deletion indexes `3` and `2` remove `S1` and `S0`. Cases with any retained cell preserve the existing descending-delete then ascending-insert order. The no-retained-row positional fallback is unchanged.

## RED Evidence

Command:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor
```

Result before production changes: `2 failed in 0.07s`.

- Row failure: actual request index 0 was `DeleteTableRow(... row_index=1 ...)`; expected request index 0 was `InsertTableRow(... row_index=0, insert_below=False)`.
- Column failure: actual request index 0 was `DeleteTableColumn(... column_index=1)`; expected request index 0 was `InsertTableColumn(... column_index=0, insert_right=False)`.

Both failures directly demonstrated delete-first anchor destruction in complete replacement.

## GREEN Evidence

Focused four-test command covering both existing mixed cases and both new boundaries:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_columns \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor
```

Result: `4 passed in 0.04s`.

All table edit-script tests:

```text
uv run pytest -q tests/compiler/test_table_edit_script.py
12 passed in 0.04s
```

Relevant table compiler files:

```text
uv run pytest -q tests/compiler/test_table_edit_script.py tests/compiler/test_edit_script.py tests/compiler/test_lowering.py tests/compiler/test_document.py
38 passed in 0.05s
```

## Full Verification

- `uv run pytest -q` — `200 passed in 0.57s`
- `uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `103 files already formatted`
- `uv run fixit lint .` — `76 files clean`
- `uv run pyright` — `0 errors, 0 warnings, 0 informations`
- `uv run pre-commit run --all-files` — all five hooks passed
- `git diff --check` — exit 0
- Plan heading check — exactly two `### Task` headings
- Branch check — `fix/table-structural-reconciliation`

The request-index self-review confirmed insertion requests target the old row/column at index 0, subsequent insertions target the newly established preceding target structure, and shifted old structures are removed from highest to lowest index.

## Specification and Plan

The committed approved spec and plan now describe exactly four new tests and an expected 200-test suite. They document both complete-replacement anchor boundaries while retaining exactly two plan Task headings.

## Commits

- `0fb4048 fix: preserve table anchors during replacement`
- This report is committed separately after the implementation commit.

## Concerns

No remaining implementation concerns. Verification is repository-only; the supplied live Google Docs evidence was accepted as the external API reproduction and the live document was not accessed.
