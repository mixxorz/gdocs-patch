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
2. When at least one source row is retained, delete every unmatched source row in descending source-index order, then insert unmatched target rows in ascending target-index order.
3. When every source row is replaced by a nonempty target, insert all target rows while one old row still anchors the table, then delete the old rows at their target-row-count-shifted source indexes.
4. Match cells by `cell_key` within retained rows as today.
5. Use the first retained target row as the column-identity reference, even when new rows precede it.
6. When at least one source cell is retained in the reference row, delete unmatched source columns in descending source-index order, then insert unmatched target columns in ascending target-index order.
7. When every source cell in the retained reference row is replaced by nonempty target columns, insert all target columns while one old column still anchors the table, then delete the old columns at their target-column-count-shifted source indexes.
8. If no row was retained, reconcile only the net column dimensions positionally because no shared cell keys exist.
9. Continue compiling cell content and table formatting against the target shape.

Deletion and insertion remain independent rather than mutually exclusive net-count branches. Complete nonempty replacement reverses those phases only where deleting the final row or column would destroy the table anchor. The public compiler API, XHTML syntax, opaque-key generation, and lowering request types remain unchanged.

## Scope and Constraints

The change covers mixed row and column removal/addition within retained keyed tables. It does not add row or column reordering, change key stability, replace retained tables wholesale, or modify MCP behavior.

The implementation will remain within `gdocs_patch/compiler/edit_script.py` and follow the existing edit model and Google Docs request ordering.

## Testing

Add exactly four focused behavioral tests to `tests/compiler/test_table_edit_script.py`:

1. A mixed row test retains one keyed row, removes two keyed rows, adds three keyless rows, and expects two row deletions followed by three row insertions.
2. An all-row-replacement anchor test replaces every source row with nonempty target rows and expects insertion before deletion at shifted old-row indexes.
3. A mixed column test retains one keyed column, removes two keyed columns, adds three keyless columns, and expects two column deletions followed by three column insertions.
4. An all-column-replacement anchor test replaces every source column in a retained row with nonempty target columns and expects insertion before deletion at shifted old-column indexes.

Existing tests continue to cover pure insertion, pure deletion, cell content, formatting, and lowering. No size-matrix parameterization or MCP-level duplicate tests will be added. The expected suite size is 200 tests.

## Success Criteria

- Mixed row reconciliation emits every required deletion and insertion.
- Mixed column reconciliation emits every required deletion and insertion.
- The reported replacement shape no longer leaves omitted rows or columns behind.
- Complete nonempty row or column replacement preserves a valid table anchor until replacements exist.
- Existing compiler behavior remains covered and all project checks pass.
