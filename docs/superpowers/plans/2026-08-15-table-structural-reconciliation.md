# Table Structural Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make retained-table compilation apply keyed removals and keyless additions together for rows and columns.

**Architecture:** Keep `generate_table_edits()` as the single table-reconciliation module. Preserve its existing key matching, but consume unmatched source and target structures in independent delete-then-insert phases; use a retained row as the column identity reference.

**Tech Stack:** Python 3.12+, pytest, uv

## Global Constraints

- Keep model classes ordinary, mutable, hand-written, and explicitly typed.
- Preserve intentional `UNSET` and proto-default behavior.
- Test meaningful behavior and invariants without duplicating MCP-level coverage.
- Add exactly two tests: one mixed row test and one mixed column test.
- Run pytest, Ruff lint/format, Fixit, Pyright, and pre-commit before completion.

---

### Task 1: Reconcile Removed and Added Rows Together

**Files:**
- Modify: `gdocs_patch/compiler/edit_script.py:420-478`
- Test: `tests/compiler/test_table_edit_script.py`

**Interfaces:**
- Consumes: Existing `generate_table_edits(*, source: TableUnit, target: TableUnit, ...) -> list[Edit]` row-key matching.
- Produces: A row structural edit prefix containing every `DeleteTableRow` for unmatched source rows, followed by every `InsertTableRow` for unmatched target rows.

- [ ] **Step 1: Add the focused mixed-row test**

Add this test after `test_generate_edit_script_deletes_a_table_row`:

```python
def test_generate_edit_script_reconciles_mixed_table_rows() -> None:
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            )
                        ],
                    ),
                    TableRowUnit(
                        row_key="removed-row-1",
                        cells=[TableCellUnit(content=empty_content)],
                    ),
                    TableRowUnit(
                        row_key="removed-row-2",
                        cells=[TableCellUnit(content=empty_content)],
                    ),
                ],
            )
        ]
    )
    target = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            )
                        ],
                    ),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableRow, InsertTableRow))
    ]

    assert structural_edits == [
        DeleteTableRow(table_start_index=0, row_index=2, column_index=0),
        DeleteTableRow(table_start_index=0, row_index=1, column_index=0),
        InsertTableRow(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_below=True,
        ),
        InsertTableRow(
            table_start_index=0,
            row_index=1,
            column_index=0,
            insert_below=True,
        ),
        InsertTableRow(
            table_start_index=0,
            row_index=2,
            column_index=0,
            insert_below=True,
        ),
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
uv run pytest -q tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows
```

Expected: FAIL because the current target-larger branch emits three insertions and no deletions.

- [ ] **Step 3: Make row removal and addition independent**

Replace the net row-count branch in `generate_table_edits()` with:

```python
    # Reconcile rows
    # --------------
    # Delete from the bottom so each source index remains valid, then insert from
    # the top so each target index exists before the next request is applied.
    edits: list[Edit] = []
    for row_index, _row in reversed(available_source_rows):
        edits.append(
            DeleteTableRow(
                table_start_index=source_table_start_index,
                row_index=row_index,
                column_index=0,
            )
        )
    for row_index in new_row_indices:
        edits.append(
            InsertTableRow(
                table_start_index=source_table_start_index,
                row_index=max(0, row_index - 1),
                column_index=0,
                insert_below=row_index > 0,
            )
        )
```

- [ ] **Step 4: Run row tests and verify GREEN**

Run:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_deletes_a_table_row \
  tests/compiler/test_edit_script.py::test_generate_edit_script_inserts_two_table_rows \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_rows
```

Expected: `3 passed`.

- [ ] **Step 5: Refactor review and commit**

Confirm the row phase has one obvious ordering rule, does not branch on net count, and leaves row matching unchanged. Then run `git diff --check` and commit:

```bash
git add gdocs_patch/compiler/edit_script.py tests/compiler/test_table_edit_script.py
git commit -m "fix: reconcile mixed table row changes"
```

---

### Task 2: Reconcile Removed and Added Columns Together

**Files:**
- Modify: `gdocs_patch/compiler/edit_script.py:480-540`
- Test: `tests/compiler/test_table_edit_script.py`

**Interfaces:**
- Consumes: `source_rows_by_target`, `new_cells`, and `deleted_cell_indices` produced by existing row/cell key matching.
- Produces: A column structural edit sequence containing every `DeleteTableColumn` for the retained reference row, followed by every `InsertTableColumn` for that row. If no row is retained, dimensions are reconciled positionally because no shared cell keys exist.

- [ ] **Step 1: Add the focused mixed-column test**

Add this test after `test_generate_edit_script_deletes_a_table_column`:

```python
def test_generate_edit_script_reconciles_mixed_table_columns() -> None:
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            ),
                            TableCellUnit(
                                cell_key="removed-cell-1",
                                content=empty_content,
                            ),
                            TableCellUnit(
                                cell_key="removed-cell-2",
                                content=empty_content,
                            ),
                        ],
                    )
                ],
            )
        ]
    )
    target = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            ),
                            TableCellUnit(content=empty_content),
                            TableCellUnit(content=empty_content),
                            TableCellUnit(content=empty_content),
                        ],
                    )
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableColumn, InsertTableColumn))
    ]

    assert structural_edits == [
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=2),
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=1),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_right=True,
        ),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=1,
            insert_right=True,
        ),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=2,
            insert_right=True,
        ),
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
uv run pytest -q tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_columns
```

Expected: FAIL because the current positive column delta emits three insertions and no deletions.

- [ ] **Step 3: Select a retained column-identity reference**

After cell matching, derive the first retained target row:

```python
    column_reference_row_index = next(iter(source_rows_by_target), None)
```

This uses target order because `source_rows_by_target` is populated while walking target rows. A retained row supplies meaningful source/target cell-key correspondence even when new rows precede it.

- [ ] **Step 4: Make keyed column removal and addition independent**

Replace the net column-count branch with:

```python
# Reconcile columns
# -----------------
# A retained row supplies the cell identities for table-wide column edits.
# Without one, only the source and target dimensions can be reconciled.
column_delta = target.column_count - source.column_count
if column_reference_row_index is not None:
    for column_index in reversed(deleted_cell_indices[column_reference_row_index]):
        edits.append(
            DeleteTableColumn(
                table_start_index=source_table_start_index,
                row_index=column_reference_row_index,
                column_index=column_index,
            )
        )
    for column_index in [
        cell_index
        for row_index, cell_index, _cell in new_cells
        if row_index == column_reference_row_index
    ]:
        edits.append(
            InsertTableColumn(
                table_start_index=source_table_start_index,
                row_index=column_reference_row_index,
                column_index=max(0, column_index - 1),
                insert_right=column_index > 0,
            )
        )
elif column_delta > 0:
    for column_index in range(source.column_count, target.column_count):
        edits.append(
            InsertTableColumn(
                table_start_index=source_table_start_index,
                row_index=0,
                column_index=max(0, column_index - 1),
                insert_right=column_index > 0,
            )
        )
elif column_delta < 0:
    for column_index in reversed(range(target.column_count, source.column_count)):
        edits.append(
            DeleteTableColumn(
                table_start_index=source_table_start_index,
                row_index=0,
                column_index=column_index,
            )
        )
```

- [ ] **Step 5: Run column tests and verify GREEN**

Run:

```bash
uv run pytest -q \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_inserts_a_table_column \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_deletes_a_table_column \
  tests/compiler/test_table_edit_script.py::test_generate_edit_script_reconciles_mixed_table_columns
```

Expected: `3 passed`.

- [ ] **Step 6: Refactor review, full verification, and commit**

Confirm column identity logic is contained in `generate_table_edits()`, request ordering is explicit, and no caller needs to understand the fallback. Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
git diff --check
```

Expected: 198 tests pass and every static/pre-commit check exits successfully. Then commit:

```bash
git add gdocs_patch/compiler/edit_script.py tests/compiler/test_table_edit_script.py
git commit -m "fix: reconcile mixed table column changes"
```
