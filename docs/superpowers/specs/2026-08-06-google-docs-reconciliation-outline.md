# Google Docs Reconciliation Outline

## Goal

Compare an independently produced target document tree with its source tree and produce Google Docs `batchUpdate` operations that transform the source into the target.

## Principles

- Match and reconcile the document hierarchy from roots toward leaves.
- Treat model-equal elements as equivalent and resolve ambiguous matches deterministically.
- Prefer retaining existing text and structure over replacing it, so comments have the best chance of surviving.
- Preserve elements that the API cannot create whenever the target still contains them.
- Reject a transformation only when the API cannot produce the target.
- Treat target `UNSET` fields as fields that should be reset to their default state.
- Use the fewest batches practical, adding a batch only when an earlier response is required.

## Work outline

1. **Map API capabilities**
   - Record which model elements and fields can be inserted, deleted, or updated.
   - Identify elements that can only be preserved or deleted.
   - Identify operations that return IDs needed by later operations.

2. **Represent reconciliation results**
   - Represent matched source/target nodes, source-only deletions, and target-only insertions.
   - Keep nested reconciliation results hierarchical.

3. **Match sibling collections**
   - Match retained provider IDs where available.
   - Align ID-less siblings using reconciliation cost.
   - Prioritize retaining content, then structure, then styles and other properties.
   - Resolve equal choices deterministically.

4. **Validate feasibility**
   - Prove that every target insertion and change is supported before producing requests.
   - Preserve matched non-creatable elements as anchors.
   - Report unsupported transformations without modifying the document.

5. **Reconcile textual content**
   - Diff text at character boundaries without treating text-run style boundaries as content changes.
   - Retain unchanged text spans and use localized insertions and deletions.
   - Reconcile supported non-text paragraph elements around preserved anchors.

6. **Reconcile document structure incrementally**
   - Start with paragraphs and body or segment content.
   - Add tables, rows, cells, and nested cell content.
   - Add sections, tabs, headers, footers, footnotes, and remaining supported structures.
   - Handle each model feature only when its Google API behavior is understood and tested.

7. **Track request-time document state**
   - Calculate each request against the state produced by preceding requests.
   - Keep a working tree synchronized with planned content and structural changes.
   - Use dynamic UTF-16 indices from that working tree.

8. **Reconcile styles and metadata**
   - Compare styles after content and structure have their target shape.
   - Produce field masks for updates and resets.
   - Apply bullets, structural styles, paragraph styles, and text styles in a safe order.

9. **Schedule requests and batches**
   - Order requests so index changes and API side effects remain valid.
   - Group independent operations into one atomic batch.
   - Split batches only for response-dependent IDs or other API requirements.

10. **Verify behavior**
    - Test each supported reconciliation behavior as it is introduced.
    - Cover ambiguous matching, unsupported changes, Unicode indices, best-effort comment preservation, nested tables, and style resets.
    - Validate complete request sequences against representative source and target documents.

## Implementation approach

Implement one narrow behavior at a time. For each behavior, agree on the model correspondence, expected Google operations, request ordering, and meaningful tests before expanding support. This outline intentionally leaves concrete APIs and algorithms open for iteration in code.
