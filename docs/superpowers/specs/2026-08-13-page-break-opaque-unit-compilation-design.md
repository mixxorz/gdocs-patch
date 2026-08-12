# Page Break and Opaque Unit Compilation

## Goal

Keep ContentStream UTF-16 indices correct when a document contains model elements the compiler does not yet understand, and add complete compiler support for page breaks.

## Content units

Add two frozen content-stream types:

```python
@dataclass(frozen=True, kw_only=True)
class PageBreakUnit(ContentUnit):
    text_style: TextStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class OpaqueUnit(ContentUnit):
    key: str
    width: int
    is_inline: bool

    @property
    def utf16_width(self) -> int:
        return self.width
```

`is_inline` exposes only the placement information the compiler needs. Inline opaque units remain part of the surrounding paragraph when calculating paragraph and bullet ranges. Block opaque units end the surrounding paragraph context.

## Normalization

`normalize_tree` continues to understand `TextRun`, `Equation`, `PageBreak`, `SectionBreak`, `Paragraph`, and `Table` explicitly. The transparent tree containers `Body`, `Segment`, and `TableCell` continue to normalize their children.

Any other node becomes one `OpaqueUnit`:

- Unsupported paragraph elements become inline opaque units.
- Unsupported structural elements, including an entire `TableOfContents`, become block opaque units.
- Unsupported containers are not traversed. Their complete UTF-16 width belongs to their single opaque unit.

An opaque key is a deterministic hash of the model type and semantic model representation. It does not contain the element index, so inserting text before an opaque element does not change its identity. Equivalent duplicate elements may share a key; `SequenceMatcher` may choose any deterministic equivalent match.

## Reconciliation

Content comparison uses distinct values for page breaks and opaque keys.

Page breaks can be retained, inserted, deleted, and text-styled. Add an `InsertPageBreak` edit containing its UTF-16 index. Lower it to Google Docs `insertPageBreak`, then use the existing `ApplyTextStyle` edit when the target page-break style must be applied.

Opaque units have deliberately limited behavior:

- Equal keys retain the source content and preserve its width in all index calculations.
- Removing an opaque unit uses the existing `DeleteContent` edit.
- Any opaque unit in an inserted or replaced target range raises `UnsupportedTransformation` before any edit script is returned, because the compiler cannot recreate unknown content. An opaque source unit may still be deleted while ordinary supported content is inserted in its place.

This behavior applies equally inside table cells because table reconciliation delegates cell content to `generate_edit_script`.

## Tests

Keep the test surface small by expanding existing behavior tests:

1. Expand the kitchen-sink normalization test with a styled page break, an unsupported inline element, and an opaque `TableOfContents`. Hard-code the complete expected stream.
2. Expand existing edit-script coverage to verify page-break insertion, deletion, retention/style application, plus opaque retention, deletion, and insertion rejection.
3. Expand the comprehensive document compilation test so its hard-coded batch includes `insertPageBreak` and the associated style behavior.
4. Run the full project checks.
5. Apply the supplied Claude XHTML to the live document again and fetch the result. Compare paragraph boundaries, named paragraph styles, and visible text around the original page-break location. Provider-generated heading IDs, positioned-object metadata, and equivalent text-run fragmentation are not required to match byte-for-byte.

No validation layer or general opaque-element mutation API will be added.
