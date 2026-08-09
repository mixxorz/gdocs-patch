# Compiler Support Outline

This is a current implementation roadmap, not an immutable specification. Items describe the intended behavior; suggested mechanisms are defaults that may change as simpler or more reliable designs emerge.

## Goal

Transform an independently produced target document tree into Google Docs `batchUpdate` requests while preserving existing content and opaque elements whenever possible.

## Current support

The compiler currently accepts manually constructed `ContentStream` objects and produces an `EditScript` for:

- text insertion, deletion, and replacement using UTF-16 indices;
- paragraph splitting and merging through paragraph boundaries;
- text and paragraph styles;
- basic paragraph bullet creation and deletion;
- equation preservation and deletion, while rejecting equation insertion;
- keyed table matching;
- table, row, and column insertion and deletion;
- table-cell merge and unmerge operations;
- reconciliation of existing table-cell content;
- table column properties, row styles, and cell styles.

The compiler does not yet normalize document models or lower an `EditScript` into real Google API requests.

## Next: complete the end-to-end path

### 1. Normalize document models into ContentStreams

Build `ContentStream` producers for independently indexed regions:

- tab bodies;
- headers and footers;
- footnotes;
- table cells.

Normalization should handle paragraphs, text runs, tables, and supported paragraph elements. It emits one `TextUnit` per character.

### 2. Carry compilation-region context

Each independently indexed region needs enough context to lower its edits:

- tab ID;
- segment ID when applicable;
- body, header, footer, footnote, or table-cell location.

Prefer keeping this context on the compilation region rather than repeating it on every content unit.

### 3. Define synthetic structural keys

Google does not return IDs for tables, rows, or cells. Define how source normalization assigns synthetic `table_key`, `row_key`, and `cell_key` values and how independently produced target trees retain those keys.

Missing target keys continue to mean newly created structures. Duplicate keys remain valid and are matched deterministically.

### 4. Lower EditScript operations

Convert semantic edits into concrete Google Docs requests, including:

- locations and ranges;
- tab and segment IDs;
- style payloads and field masks;
- `UNSET` resets;
- table locations and table ranges;
- bullet nesting mechanics;
- request payload serialization.

Start by lowering the existing numeric EditScript directly. Add another scheduling representation only if concrete ordering problems justify it.

### 5. Plan request batches

Keep independent requests in as few batches as practical. Split batches only when a later request requires an ID returned by an earlier request, such as a new tab, header, footer, or footnote.

### 6. Add an end-to-end compiler test

Exercise:

```text
source Document + target Document
    -> ContentStreams
    -> EditScript
    -> batchUpdate requests
```

Use a representative document rather than testing internal delegation.

## Complete existing content behavior

### Text and paragraph matching

- Normalize every character into its own `TextUnit`.
- Preserve unchanged text whenever possible.
- Retain paragraph split and merge behavior.
- Produce correct style resets and field masks.
- Validate UTF-16 behavior for non-BMP characters.

### Lists

- Change an existing paragraph from one list to another.
- Change nesting levels.
- Support creation from bullet presets.
- Translate nesting levels into Google’s required temporary leading-tab behavior.
- Decide the supported boundary for custom list definitions.

Existing list IDs should be preserved when source and target retain the same list membership.

Future list-planning improvements, outside the XHTML serializer/deserializer scope:

- Coalesce adjacent target paragraphs with the same `BulletPreset.preset` into one `createParagraphBullets` operation while preserving each paragraph's nesting level. The current compiler may emit redundant per-paragraph requests, which is acceptable for the XHTML work.
- Verify and document Google Docs inheritance behavior when newly inserted paragraphs target an existing `Bullet.list_id`; reject placements that cannot inherit the intended existing-list membership reliably.

### Tables

- Insert tables containing merged cells.
- Compile complete content and styles for newly inserted cells.
- Support tables nested inside newly inserted cells.
- Handle meaningful combinations of row, column, merge, content, and style edits.
- Decide how row and column reordering should behave when Google has no direct move operation.
- Verify local edit ordering against actual Google request behavior.

## Paragraph elements

### Directly creatable elements

Add ContentStream units, reconciliation, and EditScript operations for:

- `DateElement` via `insertDate`;
- `PersonReference` via `insertPerson`;
- `RichLink` via `insertRichLink`;
- `PageBreak` via `insertPageBreak`;
- `FootnoteReference` via `createFootnote`.

Creating a footnote is response-dependent because Google assigns its ID before its segment can be populated.

### Preserve-or-delete elements

Support deterministic matching, preservation, and deletion for elements that cannot be recreated from the current model:

- `AutoText`;
- `ColumnBreak`;
- `Equation`;
- `HorizontalRule`;
- `InlineObjectReference`;
- `TableOfContents`.

Fail before mutation when the target requires creating one of these elements. Inline images are insertable by Google, but the current model intentionally discards the URI and object resource data required to recreate them.

## Structural document features

### Sections

- Insert and delete section breaks.
- Reconcile section styles.
- Respect body-only restrictions for section operations.

### Headers and footers

- Create and delete segments.
- Compile their content.
- Reconcile document and section references to their generated IDs.

### Footnotes

- Preserve retained footnotes and their content.
- Delete removed references safely.
- Create new footnotes and populate their generated segments in a later batch.

### Tabs

- Add and delete tabs.
- Update titles, order, and hierarchy where supported.
- Compile every tab’s independently indexed content.
- Track IDs returned for newly created tabs.

### Table of contents

Treat a table of contents as an opaque, non-creatable structure unless API behavior proves that editing its nested content is safe.

## Document-level features

- Reconcile writable `DocumentStyle` fields.
- Reconcile named styles.
- Reconcile writable tab properties.
- Delete positioned objects that disappear from the target.
- Preserve positioned and inline objects that remain referenced.
- Add revision/write-control data to mutation execution.
- Treat document-title changes separately because Docs `batchUpdate` cannot rename the Drive file.

## Source-backed target materialization

The initial XHTML representation includes all currently modeled fields, including list definitions, named styles, and document style. Before reducing future XHTML representations for provider-owned or immutable data, define a source-backed target strategy:

- identify which definitions and resources are safe to omit and inherit from the parsed source `Document`;
- combine such omitted target data with the source before compilation when later compiler stages require it;
- distinguish omission meaning “inherit from source” from intentional deletion, reset, or replacement;
- ensure source-backed materialization occurs before feasibility checks and mutation planning.

Do not implement this optimization until the full XHTML syntax and source/target compilation behavior make the safe inheritance boundaries clear.

## XHTML token-count reduction

Keep the initial XHTML syntax explicit and attribute-based. Later, evaluate a Tailwind-like local token syntax for reducing LLM token usage without omitting model data:

- encode present booleans, enums, point dimensions, and colors as canonical tokens in one `g:format`-style attribute;
- preserve `UNSET`, explicit `false`, transparent colors, and all concrete values bijectively;
- define one fixed serialization order and reject unknown or duplicate tokens;
- retain ordinary XML attributes for arbitrary strings unless a simple unambiguous quoting scheme proves worthwhile;
- do not add selectors, inheritance, shared classes, or CSS semantics;
- compare actual model-token counts and editing clarity against the current syntax before adopting it;
- run an agent eval with equivalent document-editing tasks using the explicit and Tailwind-like syntaxes, measuring task success, edit correctness, token usage, and repair rate before deciding which representation performs better in practice.

This is a future size optimization; the current explicit representation is acceptable.

## Feasibility and preservation

Before producing requests:

- prove that every target insertion can be created;
- preserve matched opaque elements as anchors;
- reject transformations requiring unavailable resource data;
- avoid replacing unchanged text or structure;
- resolve ambiguous equivalent matches deterministically;
- ensure unsupported transformations fail before any batch is submitted.

## Suggested implementation order

1. Normalize bodies, paragraphs, text, and tables.
2. Resolve synthetic table, row, and cell key propagation.
3. Lower the existing EditScript operations into batchUpdate requests.
4. Add one complete document-to-requests integration test.
5. Complete table and list edge cases.
6. Add directly creatable paragraph elements.
7. Add sections and multiple indexed regions.
8. Add tabs, headers, footers, and footnotes with response-dependent batching.
9. Add preserve-or-delete opaque elements and document-level metadata.

Implement one vertical slice at a time. For each slice, agree on its ContentStream representation, matching behavior, EditScript operations, lowering behavior, and a small set of meaningful behavioral tests.
