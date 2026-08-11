# SectionBreak Compilation Design

## Goal

Extend the compiler to normalize, reconcile, and lower Google Docs `SectionBreak` elements. Support retaining and styling an existing break, inserting a new break, and deleting a break. Correct the equivalent paragraph-boundary behavior for newly inserted tables at the same time.

Document models and normalized ContentStreams are valid by construction. The compiler does not add defensive validation for impossible model shapes.

## ContentStream representation

Add a frozen `SectionBreakUnit(ContentUnit)` containing its `SectionStyle`. Its UTF-16 width is one.

Normalization emits every SectionBreak, including the mandatory initial break at the beginning of a body. Body streams therefore begin at UTF-16 index zero. Remove the temporary `utf16_start_index=1` adjustment from `normalize_document`; the initial `SectionBreakUnit` now accounts for that width directly.

A SectionBreak's comparison value identifies it as a section break but excludes its style. SequenceMatcher can therefore align a retained break when only its formatting changes. Identical breaks remain interchangeable and are matched deterministically.

The compiler relies on valid normalized structure. In particular, a body has its initial SectionBreak, later breaks and tables occur in valid paragraph contexts, and every region has its required terminal paragraph boundary. Invalid-stream branches and tests are out of scope.

## Paragraph boundaries and structural insertion

Google's `insertTable` and `insertSectionBreak` requests both insert a newline before the new structure. The request location is therefore one UTF-16 unit before the structure's target start index.

Reconciliation records how the target boundary immediately before an inserted structure was matched:

```python
preceding_boundary: Literal["INSERTED", "RETAINED"]
```

`InsertTable` and `InsertSectionBreak` carry this value.

- `"INSERTED"` means the target opcode inserted `ParagraphBoundary + structure`. Google's newline realizes the target boundary, so lowering emits only the structural insertion.
- `"RETAINED"` means the target opcode inserted only the structure because its preceding boundary aligned with a source boundary. Google creates an additional boundary as an insertion side effect. Lowering emits the structural insertion and then removes the extra boundary at its legal post-insertion location.

This distinction handles all valid placements:

- Splitting a paragraph inserts `ParagraphBoundary + structure`; the original terminal boundary stays with the paragraph remainder.
- Inserting between existing paragraphs inserts only the structure; lowering removes the additional boundary after the structure.
- Inserting at the end inserts `ParagraphBoundary + structure`; the existing terminal boundary remains after the structure and is not deleted.

The cleanup deletion is a Google request detail and does not appear as a semantic `DeleteContent` edit. Lowering expands the structural insertion as needed. The target ContentStream never contains temporary or extra boundaries.

For a table inserted between paragraphs, cleanup runs immediately after Google creates the blank table and before cell content expands it. The blank table's known shape provides the temporary boundary's index. Existing direct table deletion remains unchanged because Google permits deleting a table's own range without either neighboring boundary.

## SectionBreak insertion

Add an `InsertSectionBreak` Edit carrying:

- the target SectionBreak start index;
- the concrete target `section_type`;
- the preceding-boundary state described above.

Lowering emits `insertSectionBreak` at `edit.index - 1`. For a retained preceding boundary, the inserted break is followed by one extra paragraph boundary; lowering removes that boundary. For an inserted preceding boundary, no cleanup is needed.

After content reaches the target shape, normal section-style formatting applies the new break's remaining writable properties.

## SectionBreak deletion

Google rejects deleting a SectionBreak's one-unit range by itself. Its preceding paragraph boundary must be removed in the same deletion. Deleting those two units directly and then reinserting a newline causes the following paragraph to inherit the preceding paragraph's style and bullet nesting.

Add a semantic `DeleteSectionBreak` Edit for the common case where the target removes the break but retains the paragraph boundary. Lowering expands it into a two-sided sentinel sequence:

1. Insert a temporary newline immediately before the break's preceding boundary. It inherits the preceding paragraph's formatting.
2. Insert another temporary newline immediately after the break. It inherits the following paragraph's formatting.
3. Delete the former preceding boundary and the SectionBreak together.
4. Delete the following-side empty paragraph.

The resulting document has one ordinary paragraph boundary where the target expects it. Live API testing confirmed that this sequence preserves text, list ID, different nesting levels, paragraph styles, bullet text styles, and newline text styles on both neighboring paragraphs.

The sentinels are lowering details and never appear in ContentStream or EditScript.

If the target intentionally removes both the preceding ParagraphBoundary and the SectionBreak to merge paragraphs, reconciliation uses the existing `DeleteContent` edit instead. No sentinel is needed because the target does not retain that boundary.

The mandatory initial SectionBreak remains aligned in valid source and target documents; no special corruption check is added.

## Section style behavior

Add `ApplySectionStyle`, containing the target break's one-unit range and target `SectionStyle`.

For retained breaks:

- `section_type` is compared separately because Google exposes it as output-only after insertion. A change raises `UnsupportedTransformation` rather than deleting and recreating the break.
- The six read-only header and footer IDs are observational metadata. They are ignored for comparison, never serialized, and never cause rejection when they differ.
- Writable fields are compared normally.
- A concrete source field becoming target `UNSET` raises `UnsupportedTransformation` when Google does not support clearing that field.
- Changed concrete target values produce `ApplySectionStyle`.

For newly inserted breaks, `section_type` is used by `InsertSectionBreak`; the other concrete writable values produce `ApplySectionStyle` after insertion.

Lowering serializes only concrete writable values and builds their field mask. It may resend unchanged concrete values for simplicity. It excludes read-only IDs and `section_type` from `updateSectionStyle`.

Writable properties are columns, column separator style, content direction, first-page header/footer use, page-orientation flipping, page-number start, and the top, bottom, left, right, header, and footer margins. Section styles use target UTF-16 indices after content edits have established the target shape.

## Errors

Raise `UnsupportedTransformation` when:

- a retained break changes `section_type`;
- a new break lacks a concrete insertable `section_type`;
- a concrete writable source field becomes `UNSET` and Google cannot clear it.

Read-only header and footer ID differences are ignored. The compiler does not validate malformed Document or ContentStream structure.

## Tests

Tests use hardcoded valid inputs and outputs and cover behavior rather than definitions or internal delegation.

- Update existing normalization tests to include initial and later `SectionBreakUnit` values and prove body streams now use origin zero.
- Add focused EditScript behavior for inserted and retained preceding-boundary modes, safe SectionBreak deletion, and retained-break style updates.
- Add one lowering test with hardcoded Google requests, including insertion cleanup and the four-request deletion sentinel sequence.
- Update an existing new-table insertion test to place the table between valid paragraphs and verify retained-boundary cleanup. This is regression coverage for the discovered table issue rather than a new standalone regression test.
- Extend the existing comprehensive `compile_document` test so insertion, deletion, and style updates appear in the complete batch.
- Do not test malformed streams, defensive validation, shared instances, serializers in isolation, or other implementation details.

After automated verification, live testing should exercise insertion, deletion, and style updates against the designated test document and compare the fetched normalized result with the target ContentStream.
