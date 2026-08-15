# Table Temporary-Anchor Reconciliation Refactor Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace separate complete-replacement branches with one temporary-anchor axis reconciliation policy shared by rows and columns.

**Architecture:** Add one pure internal planner that orders table-axis deletions and insertions. It defers the first deletion only when every source structure is removed and nonempty replacements need an anchor; row and column code translate the neutral operations into their existing Google edit types.

**Tech Stack:** Python 3.12+, pytest, uv

## Global Constraints

- Work only in `/Users/mixxorz/Projects/gdocs_patch/.worktrees/fix-table-structural-reconciliation` on `fix/table-structural-reconciliation`.
- Preserve the public compiler API, XHTML semantics, key matching, column dimension fallback, and final document behavior.
- Add no tests; retain exactly four table reconciliation tests and 200 total tests.
- Use the existing mixed and complete-replacement tests as behavior coverage.
- Run pytest, Ruff lint/format, Fixit, Pyright, pre-commit, and `git diff --check` before completion.

---

### Task 1: Standardize Row and Column Reconciliation on a Temporary Anchor

**Files:**
- Modify: `gdocs_patch/compiler/edit_script.py`
- Modify: `tests/compiler/test_table_edit_script.py`
- Modify: `docs/superpowers/specs/2026-08-15-table-structural-reconciliation-design.md` only if needed to keep it consistent with the implementation

**Interfaces:**
- Produces: `_plan_table_axis_operations(*, source_count: int, deleted_source_indices: Sequence[int], new_target_indices: Sequence[int]) -> list[tuple[Literal["delete", "insert"], int]]`.
- Consumes: Existing sorted source deletion indices and ascending target insertion indices from row/cell key matching or column-dimension fallback.
- Preserves: Existing concrete `InsertTableRow`, `DeleteTableRow`, `InsertTableColumn`, and `DeleteTableColumn` edit types.

- [ ] **Step 1: Confirm the existing behavior baseline**

Run:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_columns \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor
```

Expected: `4 passed`.

- [ ] **Step 2: Add the pure temporary-anchor planner**

Add this internal helper near `match_content()`:

```python
TableAxisOperation = tuple[Literal["delete", "insert"], int]


def _plan_table_axis_operations(
    *,
    source_count: int,
    deleted_source_indices: Sequence[int],
    new_target_indices: Sequence[int],
) -> list[TableAxisOperation]:
    deleted_indices = list(deleted_source_indices)
    deferred_anchor = (
        source_count > 0
        and len(deleted_indices) == source_count
        and bool(new_target_indices)
    )
    if deferred_anchor:
        deleted_indices = deleted_indices[1:]

    operations: list[TableAxisOperation] = [
        ("delete", index) for index in reversed(deleted_indices)
    ]
    operations.extend(("insert", index) for index in new_target_indices)
    if deferred_anchor:
        operations.append(("delete", len(new_target_indices)))
    return operations
```

The key matcher supplies sorted deletion indices. During complete replacement index zero is the deferred source anchor. After all target insertions, that anchor sits immediately after the target sequence at `len(new_target_indices)`.

- [ ] **Step 3: Translate the row plan into concrete edits**

Replace the `replacing_all_rows` branch and duplicated loops with one loop over `_plan_table_axis_operations(...)`:

```python
edits: list[Edit] = []
for operation, row_index in _plan_table_axis_operations(
    source_count=len(source.rows),
    deleted_source_indices=[
        source_row_index for source_row_index, _source_row in available_source_rows
    ],
    new_target_indices=new_row_indices,
):
    if operation == "delete":
        edits.append(
            DeleteTableRow(
                table_start_index=source_table_start_index,
                row_index=row_index,
                column_index=0,
            )
        )
    else:
        edits.append(
            InsertTableRow(
                table_start_index=source_table_start_index,
                row_index=max(0, row_index - 1),
                column_index=0,
                insert_below=row_index > 0,
            )
        )
```

- [ ] **Step 4: Translate one column plan into concrete edits**

Keep first-retained-row selection and derive column inputs before planning:

```python
    column_delta = target.column_count - source.column_count
    if column_reference_row_index is not None:
        deleted_column_indices = deleted_cell_indices[column_reference_row_index]
        new_column_indices = [
            cell_index
            for row_index, cell_index, _cell in new_cells
            if row_index == column_reference_row_index
        ]
        column_location_row_index = column_reference_row_index
    else:
        deleted_column_indices = (
            list(range(target.column_count, source.column_count))
            if column_delta < 0
            else []
        )
        new_column_indices = (
            list(range(source.column_count, target.column_count))
            if column_delta > 0
            else []
        )
        column_location_row_index = 0
```

Then translate the shared plan:

```python
    for operation, column_index in _plan_table_axis_operations(
        source_count=source.column_count,
        deleted_source_indices=deleted_column_indices,
        new_target_indices=new_column_indices,
    ):
        if operation == "delete":
            edits.append(
                DeleteTableColumn(
                    table_start_index=source_table_start_index,
                    row_index=column_location_row_index,
                    column_index=column_index,
                )
            )
        else:
            edits.append(
                InsertTableColumn(
                    table_start_index=source_table_start_index,
                    row_index=column_location_row_index,
                    column_index=max(0, column_index - 1),
                    insert_right=column_index > 0,
                )
            )
```

- [ ] **Step 5: Observe and encode the intentional scheduling change**

Run the four focused tests. The two mixed tests should remain green; the complete-replacement tests should fail only because the safe operation order changed.

Update their hard-coded expectations to:

```python
# Complete row replacement
[
    DeleteTableRow(table_start_index=0, row_index=1, column_index=0),
    InsertTableRow(
        table_start_index=0,
        row_index=0,
        column_index=0,
        insert_below=False,
    ),
    InsertTableRow(
        table_start_index=0,
        row_index=0,
        column_index=0,
        insert_below=True,
    ),
    DeleteTableRow(table_start_index=0, row_index=2, column_index=0),
]

# Complete column replacement
[
    DeleteTableColumn(table_start_index=0, row_index=0, column_index=1),
    InsertTableColumn(
        table_start_index=0,
        row_index=0,
        column_index=0,
        insert_right=False,
    ),
    InsertTableColumn(
        table_start_index=0,
        row_index=0,
        column_index=0,
        insert_right=True,
    ),
    DeleteTableColumn(table_start_index=0, row_index=0, column_index=2),
]
```

Do not add tests or change mixed-case expectations.

- [ ] **Step 6: Verify GREEN and refactor quality**

Run:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_columns \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
git diff --check
```

Expected: four focused tests and all 200 suite tests pass; every static and pre-commit check exits successfully.

- [ ] **Step 7: Commit and report**

Commit the spec/plan documentation separately if useful, then commit the refactor and expectation updates. Keep the working tree clean and report exact commands/results.
