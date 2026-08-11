# CLI Document Commands Design

## Goal

Add `read`, `write`, and `edit` commands to `gdocs-patch`. They expose the existing Google Docs parser, XHTML codec, and compiler as an agent-friendly command-line interface.

Each command consumes exactly one JSON object from standard input. Results go to standard output, while expected failures go to standard error. The existing `auth` command remains unchanged.

## Command package

Document command behavior belongs in a semantic package rather than in `cli.py`:

```text
gdocs_patch/
└── commands/
    ├── __init__.py
    ├── read.py
    ├── write.py
    └── edit.py
```

Each command file exposes one typed operation for its command. The CLI remains a thin boundary that:

1. decodes one JSON object from standard input;
2. validates and translates its camel-case fields to typed Python arguments;
3. loads credentials and constructs `GoogleDocsClient`;
4. calls the corresponding command operation;
5. writes the result or success message; and
6. presents expected errors without a traceback.

There will be no command class hierarchy, generic command framework, or side-effect registration.

## `read`

### Input

```json
{
  "docId": "document-id",
  "offset": 1,
  "limit": 200
}
```

`docId` is required. `offset` and `limit` are optional. `offset` is one-based and defaults to `1`. An omitted `limit` selects all remaining lines. Both values refer to lines in the canonical serialized XHTML, not Google Docs UTF-16 indices.

When present, `offset` must be at least `1` and `limit` must be positive. An offset beyond the end of the document produces empty output.

### Behavior

```text
GoogleDocsClient.get_document(includeTabsContent=true)
    → document_parser
    → Document
    → serialize_document
    → select XHTML lines
    → stdout
```

Line selection preserves the serializer's text and line endings exactly. The result has no JSON wrapper and no added line numbers. With omitted pagination fields, the output is the complete canonical XHTML document.

## `write`

### Input

```json
{
  "docId": "document-id",
  "content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n..."
}
```

Both fields are required strings.

### Behavior

```text
content
    → deserialize_document
    → target Document

GoogleDocsClient.get_document(includeTabsContent=true)
    → document_parser
    → source Document

source + target
    → compile_document
    → GoogleDocsClient.batch_update
```

`docId` is authoritative: it identifies the Google document that is fetched and updated. Root XHTML identity metadata such as document ID, title, revision ID, and suggestions view mode is read-only for this command and is not written to Google. The source document's fetched revision controls the update.

“Completely replace” describes the intended final state of the content and styles supported by the compiler. It does not mean deleting all Google content and inserting it again. The normal compiler reconciliation preserves matching content, which is important for comments and other Google-managed associations.

The target must retain compatible existing tab and segment structure because the compiler cannot currently create or delete tabs, headers, footers, or footnotes. Other unsupported transformations continue to fail through `UnsupportedTransformation`; the CLI does not add a second set of compiler rules. Bullet normalization remains disabled because it is not part of this command's input contract.

If compilation produces requests, they are sent as one `batchUpdate` body. An already-equal document succeeds without sending an empty update.

Success output is:

```text
Successfully wrote to document-id.
```

## `edit`

### Input

```json
{
  "docId": "document-id",
  "edits": [
    {
      "oldText": "<span>Old text</span>",
      "newText": "<span>New text</span>"
    }
  ]
}
```

`docId` is required. `edits` must be a non-empty array. Every entry must contain string `oldText` and `newText` fields. `newText` may be empty, allowing a matched block to be deleted. `oldText` may not be empty.

### Behavior

```text
GoogleDocsClient.get_document(includeTabsContent=true)
    → source Document
    → serialize_document
    → canonical source XHTML
    → locate every edit in the original XHTML
    → apply disjoint replacements
    → deserialize_document
    → target Document
    → compile_document(source, target)
    → GoogleDocsClient.batch_update
```

The edit command fetches the Google document once. All matches are resolved against the same original canonical XHTML before any replacement is applied:

1. Each `oldText` must occur exactly once in the original XHTML.
2. The matched source ranges must not overlap.
3. Once all matches are accepted, replacements are applied from the end of the XHTML toward the beginning so earlier source positions remain stable.
4. The complete replacement result must differ from the original XHTML.
5. The complete result must deserialize as a valid XHTML document before compilation begins.

An edit does not see text produced by an earlier edit in the same command. This makes the array order irrelevant for disjoint replacements and prevents cascading replacements.

As with `write`, root identity metadata is read-only, existing tab and segment structure must remain compatible, unsupported compiler transformations fail normally, and an empty compiled request list is not sent.

Success output uses natural singular or plural wording:

```text
Successfully replaced 1 block in document-id.
Successfully replaced 2 blocks in document-id.
```

The count is the number of requested replacement blocks, since every accepted edit matches exactly once.

## JSON validation

All three commands require the top-level JSON value to be an object. Required fields, value types, and command-specific numeric constraints are checked before authentication or Google API access. Unknown fields are rejected so misspelled agent input cannot be silently ignored. JSON booleans do not count as integers for `offset` or `limit`.

Malformed JSON, multiple JSON values, an empty input stream, and an incorrect top-level type are input errors.

## Errors and exit status

Expected failures are printed to standard error with exit code `1` and no traceback:

```text
gdocs-patch: error: <message>
```

Edit failures identify the relevant array entry where applicable. Representative messages are:

```text
gdocs-patch: error: Edit command input is invalid. edits must contain at least one replacement.
```

```text
gdocs-patch: error: edits[1].oldText must not be empty in document-id.
```

```text
gdocs-patch: error: Could not find the exact text for edits[1] in document-id. The old text must match exactly including all whitespace and newlines.
```

```text
gdocs-patch: error: Found 3 occurrences of the text for edits[1] in document-id. The text must be unique. Please provide more context to make it unique.
```

```text
gdocs-patch: error: edits[0] and edits[2] overlap in document-id. Merge them into one edit or target disjoint regions.
```

```text
gdocs-patch: error: No changes made to document-id. The replacements produced identical content.
```

The CLI also presents authentication errors, XHTML parse errors, unsupported transformations, and Google API errors through the same stderr convention.

The compiler puts the revision fetched at the start of `write` or `edit` into `writeControl.requiredRevisionId`. If the document changes before `batchUpdate`, Google rejects the operation rather than applying edits compiled for stale indices. The CLI does not retry automatically; the caller must read the current document and try again.

## Testing

Tests cover public behavior, not delegation or internal structure:

- one behavioral happy-path test for each command;
- focused exact-replacement tests for empty match text, absent and non-unique matches, overlapping edits, an empty edit array, identical output, and simultaneous disjoint replacements;
- only small, valuable CLI-boundary coverage for JSON input and visible stdout/stderr behavior where it does not duplicate command tests.

Tests use hardcoded inputs and hardcoded expected output or batch requests. A small fake replaces Google only at the external transport boundary. The real parser, XHTML codec, and compiler remain in the command path. Tests do not assert helper calls, credential construction, argparse structure, or other implementation details.

Implementation follows red-green-refactor. Once tests pass, the command and CLI code are reviewed for unnecessary abstraction, duplicated input handling, and control flow that can be made more obvious without adding shallow helpers.
