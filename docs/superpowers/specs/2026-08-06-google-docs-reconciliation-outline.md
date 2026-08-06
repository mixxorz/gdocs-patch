# Google Docs Reconciliation Outline

## Goal

Compare an independently produced target document tree with its source tree and produce Google Docs `batchUpdate` operations that transform the source into the target.

## Principles

- Keep the `documents.get` model focused on representing a retrieved document.
- Normalize source and target content into a representation based on editable Docs semantics.
- Reconcile the normalized hierarchy from roots toward leaves.
- Treat model-equivalent elements as interchangeable and resolve ambiguous matches deterministically.
- Prefer retaining existing text and structure over replacing it, so comments have the best chance of surviving.
- Preserve elements that the API cannot create whenever the target still contains them.
- Reject a transformation only when the API cannot produce the target.
- Treat target `UNSET` fields as fields that should be reset to their default state.
- Use the fewest batches practical, adding a batch only when an earlier response is required.

## Reconciliation pipeline

```text
documents.get model
        ↓ normalize
ContentStream
        ↓ reconcile
EditScript
        ↓ schedule and lower
batchUpdate requests
```

### ContentStream

`ContentStream` is a materialized, editable view of an indexed content region such as a body, segment, or table cell. Text and paragraph boundaries are sequential, while structures such as tables retain their nested hierarchy. A table cell owns another `ContentStream`.

The first vertical slice contains only text and paragraph boundaries. Representing a paragraph boundary explicitly allows paragraph splitting and merging to become localized newline insertion and deletion. Later slices add inline elements, tables, sections, and other structures without changing the retrieved-document model.

### EditScript

`EditScript` contains semantic edits such as inserting text, deleting content, and updating styles. Its edits refer to source or target content symbolically rather than embedding final integer indices.

Scheduling lowers the script to real Google requests. It calculates each request index from the document state produced by preceding requests and divides requests into batches only when required.

## Work outline

1. **Map API capabilities**
   - Record which model elements and fields can be inserted, deleted, or updated.
   - Identify elements that can only be preserved or deleted.
   - Identify operations that return IDs needed by later operations.

2. **Build ContentStream normalization**
   - Normalize each independently indexed content region.
   - Begin with text and paragraph boundaries.
   - Preserve links to source locations and target styles needed during lowering.
   - Add nested structural stream elements only as their vertical slices are implemented.

3. **Reconcile streams hierarchically**
   - Align ordered content within the same parent region.
   - Match retained provider IDs where available.
   - Align ID-less content using reconciliation cost.
   - Prioritize retaining content, then structure, then styles and other properties.
   - Resolve equal choices deterministically.

4. **Validate feasibility**
   - Prove that every target insertion and change is supported before producing requests.
   - Preserve matched non-creatable elements as anchors.
   - Report unsupported transformations without modifying the document.

5. **Produce an EditScript**
   - Retain unchanged text spans.
   - Represent localized insertions, deletions, splits, merges, and supported structural changes.
   - Add style and metadata edits after content and structure have their target shape.

6. **Reconcile document features incrementally**
   - Complete the text-run and paragraph vertical slice first.
   - Add supported inline paragraph elements.
   - Add tables, rows, cells, and nested cell streams.
   - Add sections, tabs, headers, footers, footnotes, and remaining supported structures.
   - Handle each feature only when its Google API behavior is understood and tested.

7. **Track request-time document state**
   - Schedule each edit against the state produced by preceding edits.
   - Keep a working content representation synchronized with planned changes.
   - Use dynamic UTF-16 indices when lowering edits to requests.

8. **Reconcile styles and metadata**
   - Compare styles after content and structure have their target shape.
   - Produce field masks for updates and resets.
   - Apply bullets, structural styles, paragraph styles, and text styles in a safe order.

9. **Schedule requests and batches**
   - Account for index changes and API side effects.
   - Group independent operations into one atomic batch.
   - Split batches only for response-dependent IDs or other API requirements.

10. **Verify behavior**
    - Test each supported reconciliation behavior as it is introduced.
    - Cover ambiguous matching, unsupported changes, Unicode indices, best-effort comment preservation, paragraph splits and merges, nested tables, and style resets.
    - Validate complete request sequences against representative source and target documents.

## Implementation approach

Implement one vertical slice at a time. For each behavior, agree on its `ContentStream` representation, matching behavior, resulting `EditScript`, lowering rules, and meaningful tests before expanding support. Concrete APIs and algorithms will be developed incrementally in code.
