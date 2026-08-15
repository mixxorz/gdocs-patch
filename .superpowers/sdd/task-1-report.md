# Task 1 Report: Reconcile Removed and Added Rows Together

## Status

DONE_WITH_CONCERNS

## Implementation

Updated retained-table row structural reconciliation so unmatched source rows and unmatched target rows are handled independently rather than selected through a net row-count branch.

The row edit prefix now:

1. Deletes every unmatched source row from bottom to top.
2. Inserts every unmatched target row from top to bottom.

Row-key matching remains unchanged. Column reconciliation was not modified.

## Files

- `gdocs_patch/compiler/edit_script.py`
  - Replaced the mutually exclusive row-count branch with independent deletion and insertion loops.
- `tests/compiler/test_table_edit_script.py`
  - Added the requested behavior-focused, mock-free mixed row reconciliation test.
  - Imported `InsertTableRow` for structural edit assertions.
- `.superpowers/sdd/task-1-report.md`
  - Added this implementation and verification report.

## RED Evidence

Command:

```bash
uv run pytest -q tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows
```

The first invocation exposed a missing test import (`NameError: name 'InsertTableRow' is not defined`). After adding the required test-only import, the same command produced the intended behavioral RED:

```text
F                                                                        [100%]
=================================== FAILURES ===================================
____________ test_generate_edit_script_reconciles_mixed_table_rows _____________
...
E       assert [InsertTableR...t_below=True)] == [DeleteTableR...t_below=True)]
E
E         At index 0 diff: InsertTableRow(table_start_index=0, row_index=0, column_index=0, insert_below=True) != DeleteTableRow(table_start_index=0, row_index=2, column_index=0)
E         Right contains 2 more items, first extra item: InsertTableRow(table_start_index=0, row_index=1, column_index=0, insert_below=True)
E         Use -v to get more diff

 tests/compiler/test_table_edit_script.py:309: AssertionError
=========================== short test summary info ============================
FAILED tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows
1 failed in 0.05s
```

This confirmed the existing target-larger branch emitted insertions without the two required deletions.

## GREEN Evidence

Command:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_deletes_a_table_row \
  tests/compiler/test_edit_script.py::test_generate_edit_script_inserts_two_table_rows \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows
```

Output:

```text
...                                                                      [100%]
3 passed in 0.04s
```

## Full-Suite Evidence

Command:

```bash
uv run pytest -q
```

Output:

```text
........................................................................ [ 36%]
........................................................................ [ 73%]
.....................................................                    [100%]
197 passed in 2.44s
```

Additional verification:

```text
$ git diff --check
(exit 0)

$ uv run ruff check gdocs_patch/compiler/edit_script.py tests/compiler/test_table_edit_script.py
All checks passed!

$ uv run ruff format --check gdocs_patch/compiler/edit_script.py tests/compiler/test_table_edit_script.py
2 files already formatted

$ uv run fixit lint .
🧼 76 files clean 🧼

$ uv run pyright
0 errors, 0 warnings, 0 informations

$ uv run pre-commit run --all-files
ruff check...............................................................Passed
ruff format check........................................................Passed
pyright..................................................................Passed
Fixit - lint and apply autofixes.........................................Passed
Detect hardcoded secrets.................................................Passed
```

## Refactor and Self-Review

- The row phase has one explicit ordering rule: delete unmatched source rows bottom-up, then insert unmatched target rows top-down.
- No row behavior branches on net source/target row count.
- Existing row-key matching and source-row queue behavior are untouched.
- The implementation is the minimal change specified in the brief.
- The test asserts externally visible edit values and ordering using real compiler models, without mocks.
- No Task 2 column logic was changed.
- `git diff --check` passed.

## Concerns

A repository-wide direct Ruff format check (`uv run ruff format --check .`) reports a pre-existing formatting issue in `docs/superpowers/plans/2026-08-15-table-structural-reconciliation.md`. That file was not modified because it is outside Task 1 scope. Focused Ruff checks for both changed Python files and the repository's configured `pre-commit run --all-files` both pass.
