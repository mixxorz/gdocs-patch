# EditScript Lowering Design

## Goal

Convert an ordered `EditScript` into the exact low-level request dictionaries accepted in the `requests` array of Google Docs `documents.batchUpdate`.

This work supports every existing `Edit` type. It does not schedule edits, create batches, reconcile documents, or validate transformations a second time.

## Public API

```python
lower_edit_script(
    *,
    edit_script: EditScript,
    tab_id: str,
    segment_id: str | None = None,
) -> list[dict[str, object]]
```

The returned list is ready to place under `{"requests": requests}`. `compile_document()` remains responsible for the outer batch body and `writeControl`.

Every request location and range includes `tabId`. `segmentId` is included for headers, footers, and footnotes and omitted for a tab body.

## Architecture

Add `gdocs_patch/compiler/lowering.py` and move the existing `lower_edit_script()` stub there. `document.py` imports it for the existing `compile_document()` pipeline.

Lowering walks `edit_script.edits` once in their existing order and explicitly matches each concrete `Edit` type. It emits one request for most edits and multiple requests only when Google-specific mechanics require them. There is no scheduling IR, reflection-based serializer, runtime schema validation, or batching layer.

Model values are converted with explicit serialization code in the lowering module. The code may be split later only if the module becomes genuinely difficult to follow.

## Request mapping

The semantic edits map to Google requests as follows:

| Edit | Request |
| --- | --- |
| `InsertText` | `insertText` |
| `DeleteContent` | `deleteContentRange` |
| `CreateParagraphBullets` | optional temporary-tab `insertText`, then `createParagraphBullets` |
| `DeleteParagraphBullets` | `deleteParagraphBullets` |
| `ApplyTextStyle` | `updateTextStyle` |
| `ApplyParagraphStyle` | `updateParagraphStyle` |
| `InsertTable` | `insertTable` |
| `InsertTableRow` | `insertTableRow` |
| `InsertTableColumn` | `insertTableColumn` |
| `DeleteTableRow` | `deleteTableRow` |
| `DeleteTableColumn` | `deleteTableColumn` |
| `MergeTableCells` | `mergeTableCells` |
| `UnmergeTableCells` | `unmergeTableCells` |
| `ApplyTableColumnProperties` | `updateTableColumnProperties` |
| `ApplyTableRowStyle` | `updateTableRowStyle` |
| `ApplyTableCellStyle` | `updateTableCellStyle` |

Row and column requests use `tableCellLocation`. Merge, unmerge, and cell-style requests use `tableRange`. Table property and row-style requests use `tableStartLocation`. All use the semantic `table_start_index` unchanged.

### Table insertion

`InsertTable.index` is the table's target start index in the `ContentStream`. Google inserts a newline before a new table and starts the table one UTF-16 code unit after the request location. Therefore only the `insertTable` request uses:

```python
location.index = edit.index - 1
```

Later cell-content and table-style requests continue using `edit.index` as the real table start. Lowering does not reject an invalid zero table index; a valid ContentStream and EditScript are preconditions.

### Nested bullets

Google derives paragraph nesting from leading tab characters and removes those tabs when `createParagraphBullets` executes. For nesting level `n > 0`, lowering emits:

1. `insertText` containing `"\t" * n` at the paragraph's start index;
2. `createParagraphBullets` with the original start index and `endIndex + n`.

The second request consumes the temporary tabs, returning indices to the target shape before the next edit. Nesting level zero emits only `createParagraphBullets` with the original range.

## Style serialization

A style edit describes the complete target state for every writable field represented by that style. Its field mask therefore lists all modeled writable fields. Non-`UNSET` values appear in the payload. `UNSET` values remain in the field mask but are omitted from the payload, which asks Google to reset them. A wholly `UNSET` style produces an empty payload with the full writable field mask.

The masks are explicit rather than generated:

- text: `bold`, `italic`, `underline`, `strikethrough`, `smallCaps`, `baselineOffset`, `fontSize`, `weightedFontFamily`, `foregroundColor`, `backgroundColor`, and `link`;
- paragraph: `namedStyleType`, `alignment`, `direction`, `lineSpacing`, `spacingMode`, `spaceAbove`, `spaceBelow`, `indentFirstLine`, `indentStart`, `indentEnd`, `keepLinesTogether`, `keepWithNext`, `avoidWidowAndOrphan`, `pageBreakBefore`, `borderBetween`, `borderTop`, `borderBottom`, `borderLeft`, `borderRight`, `shading`;
- table column: `widthType` and `width`;
- table row: `minRowHeight`, `preventOverflow`, and `tableHeader`;
- table cell: `backgroundColor`, `borderLeft`, `borderRight`, `borderTop`, `borderBottom`, `paddingLeft`, `paddingRight`, `paddingTop`, `paddingBottom`, and `contentAlignment`.

Read-only fields are excluded from both payloads and masks:

- `ParagraphStyle.heading_id`;
- `ParagraphStyle.tab_stops`;
- `TableCellStyle.row_span`;
- `TableCellStyle.column_span`.

Cell spans are already handled by merge and unmerge edits.

Explicit nested conversions include:

- `Dimension` to `{"magnitude": ..., "unit": ...}`;
- an opaque `Color` to `{"color": {"rgbColor": {"red": ..., "green": ..., "blue": ...}}}`;
- a transparent `None` optional color to `{}`;
- `font_family` and `font_weight` under `weightedFontFamily`;
- paragraph `shading_color` under `shading.backgroundColor`;
- URL, tab, bookmark, and heading links to their corresponding Google link shape;
- paragraph and table-cell borders to their complete nested request shapes;
- `TableRow.is_header` to `tableHeader`.

Serialization is explicit. It does not inspect `vars()`, automatically convert snake case, or maintain generic rename and exclusion registries.

## Ordering and errors

Lowering preserves the EditScript's order exactly. Temporary bullet tabs are inserted and consumed next to their semantic bullet edit, so they have no net effect on later indices.

Lowering assumes indices, table geometry, styles, and request ordering are already valid. It does not duplicate reconciliation or Google API validation. An unknown future `Edit` subtype raises `NotImplementedError` rather than being silently ignored.

An empty EditScript returns an empty request list.

## Tests

Tests use hardcoded edits, models, and expected request dictionaries. They test public behavior rather than serializer helpers or delegation.

1. A focused text, paragraph, and bullet test covers insertion, deletion, nested values, resets, temporary nesting tabs, adjusted bullet ranges, and bullet deletion.
2. A focused table test covers table insertion and its location adjustment, row and column insertion and deletion, merge and unmerge, and column, row, and cell styles.
3. A focused region test proves `tabId` is always present, `segmentId` is included for a segment, and `segmentId` is omitted for a body.
4. A comprehensive `compile_document()` stress test uses hardcoded source and target document models and a hardcoded final batch-update body. The transformation collectively emits and lowers every existing `Edit` subtype at least once across body and segment content, and includes revision `writeControl`.

There are no tests for private implementation details, empty scripts, defensive validation, or serializer delegation.
