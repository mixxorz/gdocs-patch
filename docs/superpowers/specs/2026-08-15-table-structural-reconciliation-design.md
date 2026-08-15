# Table Structural Reconciliation Design

## Problem

A retained table is matched by `table_key`, and its retained rows and cells are matched by their opaque keys. The compiler correctly classifies unmatched target rows and cells as additions and unmatched source rows and cells as removals. It then chooses structural operations from the net row or column count, however, so a single compilation cannot both delete removed structures and insert new ones.

For example, replacing two keyed placeholder rows with six keyless rows emits six row insertions but no row deletions. The placeholders survive at the end of the table. Column reconciliation has the same defect.

## Intended Semantics

The deserialized target XHTML is the desired complete document state. Within a retained table:

- A source key retained in the target identifies the same existing structure.
- A source key omitted from the target identifies a removed structure.
- A keyless target structure identifies a new structure.

Structural reconciliation must apply all differences identified by key matching, independently of the net table dimensions.

## Design

Keep matching and content compilation inside `generate_table_edits()`. Change only the structural reconciliation phases:

1. Match rows by `row_key` as today.
2. Delete every unmatched source row in descending source-index order so earlier indexes remain valid.
3. Insert every unmatched target row in ascending target-index order so each insertion can use the table shape produced by preceding operations.
4. Match cells by `cell_key` within retained rows as today.
5. Use the first retained target row as the column-identity reference, even when new rows precede it.
6. Delete every unmatched source column in descending source-index order.
7. Insert every unmatched target column in ascending target-index order.
8. If no row was retained, reconcile only the net column dimensions positionally because no shared cell keys exist.
9. Continue compiling cell content and table formatting against the target shape.

Deletion and insertion are independent phases rather than mutually exclusive net-count branches. The public compiler API, XHTML syntax, opaque-key generation, and lowering request types remain unchanged.

## Scope and Constraints

The change covers mixed row and column removal/addition within retained keyed tables. It does not add row or column reordering, change key stability, replace retained tables wholesale, or modify MCP behavior.

The implementation will remain within `gdocs_patch/compiler/edit_script.py` and follow the existing edit model and Google Docs request ordering.

## Testing

Add exactly two focused behavioral tests to `tests/compiler/test_table_edit_script.py`:

1. A mixed row test retains one keyed row, removes two keyed rows, adds three keyless rows, and expects two row deletions followed by three row insertions.
2. A mixed column test retains one keyed column, removes two keyed columns, adds three keyless columns, and expects two column deletions followed by three column insertions.

Existing tests continue to cover pure insertion, pure deletion, cell content, formatting, and lowering. No size-matrix parameterization or MCP-level duplicate tests will be added. The expected suite size is 198 tests.

## Success Criteria

- Mixed row reconciliation emits every required deletion and insertion.
- Mixed column reconciliation emits every required deletion and insertion.
- The reported replacement shape no longer leaves omitted rows or columns behind.
- Existing compiler behavior remains covered and all project checks pass.
