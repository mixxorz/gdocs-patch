# Normalize Tree Design

## Goal

Implement `normalize_tree(tree: TreeNode) -> ContentStream` so the compiler can turn supported document-tree content into the existing one-dimensional content-stream representation.

## Model identity

`Table`, `TableRow`, and `TableCell` gain optional `table_key`, `row_key`, and `cell_key` attributes respectively. The keys are opaque identities assigned by higher-level code. Normalization copies them unchanged into `TableUnit`, `TableRowUnit`, and `TableCellUnit`.

## Traversal

`normalize_tree` uses the existing `TreeNode.children` API recursively. It does not add another walker, registry, visitor, or set of private normalization helpers.

- Generic containers, including `Body`, `Segment`, and `TableCell`, normalize their children in order and concatenate the resulting units.
- A `TextRun` emits one `TextUnit` per Python character and preserves its `TextStyle` on every emitted unit.
- An `Equation` emits one `EquationUnit`.
- A `Paragraph` normalizes its element children in order, then emits one `ParagraphBoundary` carrying the paragraph style and bullet.
- If the paragraph's final character is `"\n"`, that character is represented only by the `ParagraphBoundary`. Earlier newline characters remain ordinary `TextUnit(content="\n")` entries. The boundary receives the final newline's `TextStyle`.
- A `Table` emits one `TableUnit`. Its rows and cells retain their nested shape, and each cell's content is recursively normalized into its own `ContentStream` rather than flattened into the outer stream.

Table normalization copies column properties, row properties, cell style, and cell row/column spans into the existing content-stream classes. When cell style is `UNSET`, its row and column spans are both `1`.

## Scope

This slice normalizes only content already represented by the current content-stream types:

- text;
- paragraph boundaries and bullets;
- equations;
- tables, rows, cells, and their supported properties.

It does not add new content-unit types, lower edit scripts, or normalize unsupported structural and paragraph elements.

## Tests

Add exactly four behavioral tests for `normalize_tree`, using explicitly constructed model trees and hardcoded expected content-stream values:

1. A paragraph test covering multiple text runs, text and paragraph styles, UTF-16 characters, an internal newline, the terminal newline, and a bullet.
2. A table test using a sufficiently complex keyed table with at least two rows and two columns, cell spans, nested paragraph content, column properties, row properties, and cell styles.
3. An opaque-object test covering equations surrounded by text in a paragraph.
4. A kitchen-sink body combining every currently supported content-stream unit in document order.

The tests must not calculate expected output from the inputs or reproduce the normalization algorithm. Existing unrelated tests remain unchanged.
