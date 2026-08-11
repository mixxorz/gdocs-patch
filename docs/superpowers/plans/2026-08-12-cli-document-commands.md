# CLI Document Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JSON-over-stdin `read`, `write`, and `edit` commands that expose Google Docs as canonical XHTML and compile XHTML changes back to Google batch-update requests.

**Architecture:** Keep `cli.py` as the JSON/authentication/output boundary. Put each operation in its own semantic module under `gdocs_patch/commands/`; those modules compose the existing client, parser, XHTML codec, and compiler without wrapping them in command classes or another framework.

**Tech Stack:** Python 3.12+, `argparse`, standard-library `json`, Google Docs API client, existing parser/XHTML/compiler modules, pytest, Ruff, Fixit, Pyright, pre-commit.

## Global Constraints

- Work only in `/Users/mixxorz/Projects/gdocs_patch/.worktrees/feature-cli-commands` on branch `feature-cli-commands`.
- Consume exactly one JSON object from stdin; do not add JSON command-line arguments.
- Keep `auth login` behavior unchanged.
- Use camel-case names only at the JSON boundary and snake-case Python names internally.
- Reject unknown JSON fields, incorrect types, and booleans supplied as integer pagination values.
- Keep root XHTML identity metadata read-only and use the fetched source revision for writes.
- Keep bullet normalization disabled; preserve all existing compiler limitations and errors.
- Test public behavior with hardcoded inputs and outputs. Fake only `GoogleDocsClient`, the external HTTP boundary.
- Do not test helper calls, argparse declarations, parser/compiler delegation, or credential construction.
- Do not add tests beyond the read happy path, write happy path, edit happy path, JSON boundary behavior, and the agreed edit invariants.
- Use RED → GREEN → REFACTOR within each step and commit after each step.

## File map

```text
gdocs_patch/commands/__init__.py  # Explicit exports for document commands
gdocs_patch/commands/read.py      # Fetch, serialize, and line-slice XHTML
gdocs_patch/commands/write.py     # Deserialize, compile, and write complete XHTML
gdocs_patch/commands/edit.py      # Exact XHTML replacement and compilation
gdocs_patch/cli.py                # JSON stdin, validation, auth, output, errors
README.md                          # Agent-oriented command examples
tests/commands/support.py          # Hardcoded Google response and fake HTTP edge
tests/commands/test_read.py        # Read behavior
tests/commands/test_write.py       # Write behavior
tests/commands/test_edit.py        # Edit behavior and invariants
tests/test_cli.py                  # Small JSON boundary coverage
```

The hardcoded source response used by command tests represents one tab with an initial section break and one paragraph containing `Hello world\n` at revision `rev-1`. Its canonical XHTML is:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Example" g:revision-id="rev-1">
  <body>
    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">
      <g:document-tab>
        <g:body>
          <section>
            <g:section-style />
            <g:paragraph>
              <span>Hello world</span>
            </g:paragraph>
          </section>
        </g:body>
      </g:document-tab>
    </g:tab>
  </body>
</html>
```

---

- [ ] **Step 1: Implement the `read` command and the common JSON stdin boundary**

  **Files:**
  - Create `gdocs_patch/commands/__init__.py`
  - Create `gdocs_patch/commands/read.py`
  - Create `tests/commands/__init__.py`
  - Create `tests/commands/support.py`
  - Create `tests/commands/test_read.py`
  - Create `tests/test_cli.py`
  - Modify `gdocs_patch/cli.py`
  - Modify `README.md`

  **Interfaces produced:**

  `read_document(*, client: GoogleDocsClient, doc_id: str, offset: int = 1, limit: int | None = None) -> str`

  `tests/commands/support.py` provides a `FakeGoogleDocsClient` that records document IDs and batch bodies while returning the hardcoded source response. It is a plain test fake, not a mock of parser/compiler internals.

  **RED:** Add one read behavior test with `offset=8` and `limit=4`. Hardcode this expected result:

  ```python
  assert result == (
      "            <g:section-style />\n"
      "            <g:paragraph>\n"
      "              <span>Hello world</span>\n"
      "            </g:paragraph>\n"
  )
  assert client.get_document_ids == ["doc-1"]
  ```

  Add one parameterized CLI-boundary test covering these hardcoded cases. It must call `main(["read"])`, assert exit code `1`, and require no credentials or client fake because validation happens first:

  | stdin | Expected stderr |
  |---|---|
  | `{` | `gdocs-patch: error: Input must contain one valid JSON object.\n` |
  | `[]` | `gdocs-patch: error: Input must be a JSON object.\n` |
  | `{"docId":"doc-1","extra":true}` | `gdocs-patch: error: Read command input has unknown field: extra.\n` |

  Run:

  ```bash
  uv run pytest tests/commands/test_read.py tests/test_cli.py -v
  ```

  Expected: FAIL because the command module and CLI command do not exist.

  **GREEN:** Implement `read_document` directly:

  ```python
  response = client.get_document(document_id=doc_id)
  document = document_parser.parse(response)
  lines = serialize_document(document).splitlines(keepends=True)
  start = offset - 1
  stop = None if limit is None else start + limit
  return "".join(lines[start:stop])
  ```

  Add the `read` argparse command. Add one JSON-object reader in `cli.py` that uses `json.load(sys.stdin)`, rejects malformed/multiple values and non-object values, and returns `dict[str, object]`. In the `read` branch, explicitly validate the exact field set `{docId, offset, limit}`, require a string `docId`, require `type(offset) is int and offset >= 1`, and require an omitted limit or `type(limit) is int and limit > 0`. Validate before calling `load_credentials()`.

  Construct `GoogleDocsClient(credentials=load_credentials())`, call `read_document`, and use `sys.stdout.write()` rather than `print()` so XHTML line endings remain unchanged. Catch expected input, authentication, and Google API errors and retain the existing no-traceback stderr convention.

  Add a README example using JSON stdin and document that `offset` is one-based lines, `limit` is a line count, and output is raw unnumbered XHTML.

  **REFACTOR AND VERIFY:** Keep a single meaningful JSON decoding helper; do not introduce field-reader helpers or request classes. Run:

  ```bash
  uv run pytest tests/commands/test_read.py tests/test_cli.py -v
  uv run ruff check gdocs_patch/cli.py gdocs_patch/commands/read.py tests/commands tests/test_cli.py
  uv run pyright
  ```

  Expected: all pass. Commit:

  ```bash
  git add gdocs_patch/commands gdocs_patch/cli.py tests/commands tests/test_cli.py README.md
  git commit -m "feat: add CLI read command"
  ```

---

- [ ] **Step 2: Implement the `write` command**

  **Files:**
  - Create `gdocs_patch/commands/write.py`
  - Create `tests/commands/test_write.py`
  - Modify `gdocs_patch/commands/__init__.py`
  - Modify `gdocs_patch/cli.py`
  - Modify `README.md`

  **Interfaces consumed:** `GoogleDocsClient`, `document_parser`, `deserialize_document`, and `compile_document`.

  **Interface produced:**

  `write_document(*, client: GoogleDocsClient, doc_id: str, content: str) -> None`

  **RED:** Add one test whose hardcoded target XHTML changes the paragraph to `Hello brave world` while deliberately using a different root `g:document-id` and `g:title`. Assert that the fake client fetches and writes `doc-1`, proving `doc_id` is authoritative. Hardcode this batch body:

  ```python
  {
      "requests": [
          {
              "insertText": {
                  "location": {"index": 7, "tabId": "tab-1"},
                  "text": "brave ",
              }
          },
          {
              "updateTextStyle": {
                  "range": {
                      "startIndex": 7,
                      "endIndex": 13,
                      "tabId": "tab-1",
                  },
                  "textStyle": {},
                  "fields": (
                      "bold,italic,underline,strikethrough,smallCaps,"
                      "baselineOffset,fontSize,weightedFontFamily,"
                      "foregroundColor,backgroundColor,link"
                  ),
              }
          },
      ],
      "writeControl": {"requiredRevisionId": "rev-1"},
  }
  ```

  Run `uv run pytest tests/commands/test_write.py -v`; expect FAIL because `write_document` does not exist.

  **GREEN:** In `write_document`, deserialize `content` before fetching Google, parse the fetched source, compile source to target, and call `batch_update(document_id=doc_id, body=batch)` only when `batch["requests"]` is non-empty. Do not copy XHTML root metadata into the source or add title handling; `compile_document` already takes write control from the source and does not compile root identity metadata.

  Add the `write` parser and CLI branch. Accept exactly `docId` and `content`, require both to be strings, validate before authentication, call `write_document`, and print:

  ```text
  Successfully wrote to doc-1.
  ```

  Present `XHTMLParseError`, `UnsupportedTransformation`, authentication errors, and Google API errors through the existing stderr path. Add a README `jq --rawfile` example so multiline XHTML reaches stdin without shell escaping or argv limits.

  **REFACTOR AND VERIFY:** Keep the write pipeline linear and in the semantic command file. Do not extract a one-use “compile and send” helper. Run:

  ```bash
  uv run pytest tests/commands/test_write.py -v
  uv run ruff check gdocs_patch/commands/write.py gdocs_patch/cli.py tests/commands/test_write.py
  uv run pyright
  ```

  Expected: all pass. Commit:

  ```bash
  git add gdocs_patch/commands gdocs_patch/cli.py tests/commands/test_write.py README.md
  git commit -m "feat: add CLI write command"
  ```

---

- [ ] **Step 3: Implement the `edit` command happy path**

  **Files:**
  - Create `gdocs_patch/commands/edit.py`
  - Create `tests/commands/test_edit.py`
  - Modify `gdocs_patch/commands/__init__.py`
  - Modify `gdocs_patch/cli.py`
  - Modify `README.md`

  **Interfaces produced:**

  ```python
  @dataclass(frozen=True, kw_only=True)
  class XhtmlEdit:
      old_text: str
      new_text: str
  ```

  `apply_xhtml_edits(*, xhtml: str, edits: Sequence[XhtmlEdit], document_id: str) -> str`

  `edit_document(*, client: GoogleDocsClient, doc_id: str, edits: Sequence[XhtmlEdit]) -> int`

  `apply_xhtml_edits` is the small, reusable exact-text editing operation; it is not a parser/compiler helper and is tested through its input/output contract in Step 4.

  **RED:** Add one command test replacing the unique block `world` with `brave world`. Assert a result count of `1`, one fetch, and this hardcoded batch body, confirming the real fetch → serialize → edit → deserialize → compile → batch-update pipeline:

  ```python
  {
      "requests": [
          {
              "insertText": {
                  "location": {"index": 7, "tabId": "tab-1"},
                  "text": "brave ",
              }
          },
          {
              "updateTextStyle": {
                  "range": {
                      "startIndex": 7,
                      "endIndex": 13,
                      "tabId": "tab-1",
                  },
                  "textStyle": {},
                  "fields": (
                      "bold,italic,underline,strikethrough,smallCaps,"
                      "baselineOffset,fontSize,weightedFontFamily,"
                      "foregroundColor,backgroundColor,link"
                  ),
              }
          },
      ],
      "writeControl": {"requiredRevisionId": "rev-1"},
  }
  ```

  Run `uv run pytest tests/commands/test_edit.py::test_edits_canonical_xhtml_and_updates_google_document -v`; expect FAIL because the edit module does not exist.

  **GREEN:** Implement the valid-input path. `apply_xhtml_edits` locates each old string in the original XHTML, records `(start, end, edit_index)`, and applies replacements in descending `start` order. It must not apply edits sequentially to a changing search string.

  `edit_document` fetches once, parses and serializes the source, calls `apply_xhtml_edits`, deserializes the result, compiles it against the already-fetched source, conditionally sends a non-empty batch, and returns `len(edits)`.

  Add the `edit` parser and CLI branch. Accept exactly `docId` and `edits`; require `edits` to be a JSON array; require every element to be an object with exactly string `oldText` and `newText`; then construct `XhtmlEdit` values. Print natural count wording:

  ```python
  noun = "block" if count == 1 else "blocks"
  print(f"Successfully replaced {count} {noun} in {doc_id}.")
  ```

  Add a README heredoc example with two edits and explain that matches are against canonical unnumbered XHTML returned by `read`.

  **REFACTOR AND VERIFY:** Ensure the command reads Google only once and that `apply_xhtml_edits` contains only replacement mechanics. Run:

  ```bash
  uv run pytest tests/commands/test_edit.py::test_edits_canonical_xhtml_and_updates_google_document -v
  uv run ruff check gdocs_patch/commands/edit.py gdocs_patch/cli.py tests/commands/test_edit.py
  uv run pyright
  ```

  Expected: all pass. Commit:

  ```bash
  git add gdocs_patch/commands gdocs_patch/cli.py tests/commands/test_edit.py README.md
  git commit -m "feat: add CLI edit command"
  ```

---

- [ ] **Step 4: Implement every exact-edit invariant, then run final verification**

  **Files:**
  - Modify `gdocs_patch/commands/edit.py`
  - Modify `tests/commands/test_edit.py`
  - Modify `gdocs_patch/cli.py` to present `XhtmlEditError`

  **Interface produced:**

  ```python
  class XhtmlEditError(Exception):
      """Raised when exact XHTML replacements cannot be applied safely."""
  ```

  **RED:** Add one hardcoded success test proving two disjoint replacements are both resolved against the original string regardless of edit order:

  ```python
  assert (
      apply_xhtml_edits(
          xhtml="alpha beta gamma",
          edits=[
              XhtmlEdit(old_text="gamma", new_text="G"),
              XhtmlEdit(old_text="alpha", new_text="A"),
          ],
          document_id="doc-1",
      )
      == "A beta G"
  )
  ```

  Add one parameterized public-behavior test with these hardcoded cases and messages:

  | XHTML | Edits | Expected message |
  |---|---|---|
  | `Hello world` | `[]` | `Edit command input is invalid. edits must contain at least one replacement.` |
  | `Hello world` | `oldText=""` | `edits[0].oldText must not be empty in doc-1.` |
  | `Hello world` | `oldText="missing"` | `Could not find the exact text for edits[0] in doc-1. The old text must match exactly including all whitespace and newlines.` |
  | `aaaa` | `oldText="aa"` | `Found 3 occurrences of the text for edits[0] in doc-1. The text must be unique. Please provide more context to make it unique.` |
  | `Hello world` | `oldText="Hello world"` plus `oldText="world"` | `edits[0] and edits[1] overlap in doc-1. Merge them into one edit or target disjoint regions.` |
  | `Hello world` | `oldText="world", newText="world"` | `No changes made to doc-1. The replacements produced identical content.` |

  The non-unique case deliberately uses overlapping textual occurrences; count occurrences by advancing the next search by one character rather than using `str.count()`.

  Run `uv run pytest tests/commands/test_edit.py -v`; expect the new invariant cases to FAIL.

  **GREEN:** Update `apply_xhtml_edits` in this obvious order:

  1. reject an empty edit sequence;
  2. for each edit, reject empty `old_text` and collect every occurrence start with repeated `xhtml.find(old_text, previous_start + 1)`;
  3. reject zero occurrences or more than one occurrence with the agreed indexed messages;
  4. sort `(start, end, edit_index)` tuples by source start and use `itertools.pairwise` to reject `right_start < left_end`;
  5. apply replacements from highest source start to lowest; and
  6. reject a final string equal to the original.

  Catch `XhtmlEditError` in the normal CLI expected-error path. Do not add runtime XHTML/XML validation to the replacement function; `edit_document` already deserializes the complete result immediately afterward.

  **REFACTOR:** Read the complete command implementation as a human-facing code review. Keep the three command files linear, retain only the shared JSON-object decoder in `cli.py`, avoid negative-condition mazes, and add comments only where the reason cannot be inferred from the code.

  **FINAL VERIFICATION:** Run every required project check:

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  uv run fixit lint .
  uv run pyright
  uv run pre-commit run --all-files
  git diff --check
  git status --short --branch
  ```

  Expected: 181 existing tests plus only the approved command/invariant cases pass; every static check passes; status contains only intended feature files. Also verify main did not receive feature commits:

  ```bash
  git -C /Users/mixxorz/Projects/gdocs_patch branch --show-current
  git -C /Users/mixxorz/Projects/gdocs_patch status --short --branch
  ```

  Expected: main remains on `main` with only the two intentional untracked sample document files.

  Commit:

  ```bash
  git add gdocs_patch/commands/edit.py gdocs_patch/cli.py tests/commands/test_edit.py
  git commit -m "feat: enforce exact XHTML edit invariants"
  ```
