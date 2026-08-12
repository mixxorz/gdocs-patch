# Page Break and Opaque Unit Compilation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve correct ContentStream indices around unsupported model elements and compile page-break edits into Google Docs requests.

**Architecture:** Normalization represents unsupported content as identity-and-width-only `OpaqueUnit` values, allowing existing content to align or be deleted without pretending it can be recreated. Page breaks receive a first-class `PageBreakUnit` and `InsertPageBreak` edit while reusing existing deletion and text-style behavior.

**Tech Stack:** Python 3.12, frozen dataclasses, `hashlib.sha256`, `difflib.SequenceMatcher`, pytest, Google Docs batchUpdate request dictionaries.

## Global Constraints

- Keep `OpaqueUnit` entirely inside the compiler; do not add opaque keys to document model or XHTML classes.
- Treat unsupported containers as one opaque unit and do not normalize their children.
- Derive opaque keys from model type and semantic representation, never from document index.
- Do not add validation or a general unsupported-element mutation API.
- Update existing behavior tests rather than creating additional low-value test functions.
- Use `uv` for every project command.

---

### Task 1: OpaqueUnit

**Files:**
- Modify: `gdocs_patch/compiler/content_stream.py`
- Modify: `gdocs_patch/compiler/document.py`
- Modify: `gdocs_patch/compiler/edit_script.py`
- Modify: `gdocs_patch/compiler/__init__.py`
- Test: `tests/compiler/test_document.py`
- Test: `tests/compiler/test_edit_script.py`

**Interfaces:**
- Produces: `OpaqueUnit(key: str, width: int, is_inline: bool)` with `utf16_width == width`.
- Produces: normalization in which unsupported paragraph elements are inline opaque units and unsupported structural elements are block opaque units.
- Produces: reconciliation that retains equal opaque keys, deletes source opaque units, and rejects opaque units in inserted or replaced target ranges.

- [ ] **Step 1: Expand the existing normalization tests and verify RED**

In `tests/compiler/test_document.py`, import `OpaqueUnit`, `ColumnBreak`, and `TableOfContents`. Expand `test_normalize_tree_normalizes_kitchen_sink_body_in_document_order` rather than adding a new test:

- Put `ColumnBreak()` between `TextRun(content="X")` and `Equation()` in the final paragraph.
- Put `TableOfContents(content=[Paragraph(elements=[TextRun(content="Hidden\n")])])` before the final paragraph.
- Hard-code the corresponding expected units in document order:

```python
OpaqueUnit(key="opaque-a20f6ae2", width=1, is_inline=True)
OpaqueUnit(key="opaque-" "982bf560", width=8, is_inline=False)
```

The key values are SHA-256 prefixes of `f"{type(node).__name__}:{node!r}"`; the table-of-contents width is its one-unit container overhead plus the seven UTF-16 units in `Hidden\n`.

Run:

```bash
uv run pytest tests/compiler/test_document.py::test_normalize_tree_normalizes_kitchen_sink_body_in_document_order -q
```

Expected: FAIL because `OpaqueUnit` is not exported and unsupported nodes are currently traversed or omitted.

- [ ] **Step 2: Add OpaqueUnit and opaque normalization**

In `gdocs_patch/compiler/content_stream.py`, add:

```python
@dataclass(frozen=True, kw_only=True)
class OpaqueUnit(ContentUnit):
    key: str
    width: int
    is_inline: bool

    @property
    def utf16_width(self) -> int:
        return self.width
```

Add `OpaqueUnit` to `ContentStream.comparison_values()` as `("opaque", item.key)` and export it from `gdocs_patch/compiler/__init__.py`.

In `gdocs_patch/compiler/document.py`, import `hashlib`, `ParagraphElement`, `Segment`, `TableCell`, and `OpaqueUnit`. Keep recursion only for `Body`, `Segment`, and `TableCell`. After all explicitly supported node cases, normalize every other node with:

```python
semantic_value = f"{type(tree).__name__}:{tree!r}"
return ContentStream(
    items=[
        OpaqueUnit(
            key=f"opaque-{hashlib.sha256(semantic_value.encode()).hexdigest()[:8]}",
            width=tree.utf16_width,
            is_inline=isinstance(tree, ParagraphElement),
        )
    ]
)
```

The generic child-recursion fallback must be removed so an unsupported container is represented as one unit.

Run the test from Step 1. Expected: PASS.

- [ ] **Step 3: Expand existing edit-script opaque behavior coverage and verify RED**

In `tests/compiler/test_edit_script.py`, change the source and target in `test_generate_edit_script_preserves_and_deletes_equations` to these hard-coded streams:

```python
source = ContentStream(
    items=[
        TextUnit(content="A"),
        OpaqueUnit(key="opaque-retained", width=2, is_inline=True),
        EquationUnit(),
        TextUnit(content="B"),
        OpaqueUnit(key="opaque-deleted", width=3, is_inline=False),
        EquationUnit(),
        TextUnit(content="C"),
        ParagraphBoundary(),
    ]
)
target = ContentStream(
    items=[
        TextUnit(content="A"),
        OpaqueUnit(key="opaque-retained", width=2, is_inline=True),
        EquationUnit(),
        TextUnit(content="B"),
        TextUnit(content="C"),
        ParagraphBoundary(),
    ]
)
```

Hard-code the expected output as `[DeleteContent(start_index=5, end_index=9)]`. The deleted source range contains the three-unit opaque element and the deleted equation, while the retained opaque element contributes two units to the deletion index.

Extend `test_generate_edit_script_rejects_equation_insertion` with a second assertion using source `[TextUnit("A"), TextUnit("B"), ParagraphBoundary()]` and target `[TextUnit("A"), OpaqueUnit(key="opaque-new", width=1, is_inline=True), TextUnit("B"), ParagraphBoundary()]`. Assert that it raises `UnsupportedTransformation` with `OpaqueUnit` in the message. Do not create a separate test.

Run:

```bash
uv run pytest tests/compiler/test_edit_script.py::test_generate_edit_script_preserves_and_deletes_equations tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_equation_insertion -q
```

Expected: the deletion assertion may pass from generic range deletion, but the insertion assertion FAILS because opaque insertion is not rejected explicitly.

- [ ] **Step 4: Implement opaque reconciliation**

In `gdocs_patch/compiler/edit_script.py`:

- Treat inline `OpaqueUnit` values as inline paragraph content in `is_inline_paragraph_unit`.
- Reset paragraph-range tracking after a block `OpaqueUnit`.
- Before generating edits, inspect every inserted or replaced target range and raise:

```python
UnsupportedTransformation("cannot insert OpaqueUnit content")
```

when the range contains an `OpaqueUnit`.
- Treat retained `OpaqueUnit` values as opaque in the formatting pass, alongside equations and tables.

Run:

```bash
uv run pytest tests/compiler/test_document.py tests/compiler/test_edit_script.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit OpaqueUnit support**

```bash
git add gdocs_patch/compiler/content_stream.py gdocs_patch/compiler/document.py gdocs_patch/compiler/edit_script.py gdocs_patch/compiler/__init__.py tests/compiler/test_document.py tests/compiler/test_edit_script.py
git commit -m "feat: preserve opaque content during compilation"
```

---

### Task 2: Page Break Handling

**Files:**
- Modify: `gdocs_patch/compiler/content_stream.py`
- Modify: `gdocs_patch/compiler/document.py`
- Modify: `gdocs_patch/compiler/edit_script.py`
- Modify: `gdocs_patch/compiler/lowering.py`
- Modify: `gdocs_patch/compiler/__init__.py`
- Test: `tests/compiler/test_document.py`
- Test: `tests/compiler/test_edit_script.py`
- Test: `tests/compiler/test_lowering.py`

**Interfaces:**
- Consumes: the ContentStream and opaque reconciliation behavior from Task 1.
- Produces: `PageBreakUnit(text_style: TextStyle | UnsetType = UNSET)` with UTF-16 width 1.
- Produces: `InsertPageBreak(index: int)`.
- Produces: Google request `{"insertPageBreak": {"location": {"index": ..., "tabId": ...}}}`.

- [ ] **Step 1: Expand existing normalization and edit-script tests and verify RED**

In `tests/compiler/test_document.py`, import `PageBreakUnit` and `PageBreak`. In the existing kitchen-sink paragraph, place:

```python
PageBreak(text_style=TextStyle(bold=True))
```

before its terminal text run, and hard-code this expected stream entry:

```python
PageBreakUnit(text_style=TextStyle(bold=True))
```

In `tests/compiler/test_edit_script.py`, extend the existing equation preservation/deletion test with one retained and one deleted `PageBreakUnit`, adjusting the hard-coded `DeleteContent` indices for their one-unit widths.

Extend `test_generate_edit_script_rejects_equation_insertion` with a supported page-break case using source `[TextUnit(content="A"), TextUnit(content="B"), ParagraphBoundary()]` and target `[TextUnit(content="A"), PageBreakUnit(text_style=TextStyle(bold=True)), TextUnit(content="B"), ParagraphBoundary()]`. Assert this complete edit script:

```python
[
    InsertPageBreak(index=1),
    ApplyTextStyle(
        start_index=1,
        end_index=2,
        text_style=TextStyle(bold=True),
    ),
]
```

Run the affected tests. Expected: FAIL because `PageBreakUnit` and `InsertPageBreak` do not exist.

- [ ] **Step 2: Implement page-break normalization and edit generation**

In `gdocs_patch/compiler/content_stream.py`, add:

```python
@dataclass(frozen=True, kw_only=True)
class PageBreakUnit(ContentUnit):
    text_style: TextStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1
```

Compare it as `("page_break", "")` and export it.

In `gdocs_patch/compiler/document.py`, normalize `PageBreak` to `PageBreakUnit` before the opaque fallback.

In `gdocs_patch/compiler/edit_script.py`, add and export:

```python
@dataclass(frozen=True, kw_only=True)
class InsertPageBreak(Edit):
    index: int
```

Treat `PageBreakUnit` as inline paragraph content. During insertion, calculate its source-coordinate request index with the same target-range UTF-16 offset used by other inserted units and emit `InsertPageBreak`. During formatting, compare its `text_style` like `TextUnit` and emit `ApplyTextStyle` when needed. Generic source-range deletion already handles page-break deletion.

Run:

```bash
uv run pytest tests/compiler/test_document.py tests/compiler/test_edit_script.py -q
```

Expected: PASS.

- [ ] **Step 3: Expand existing lowering coverage and verify RED**

In `tests/compiler/test_lowering.py`, import `InsertPageBreak` and add it to an existing mixed `EditScript` fixture. Add this hard-coded request at the corresponding position:

```python
{
    "insertPageBreak": {
        "location": {
            "index": 6,
            "tabId": "tab-1",
        }
    }
}
```

Run that existing test. Expected: FAIL with `NotImplementedError: InsertPageBreak`.

- [ ] **Step 4: Lower page breaks and expand comprehensive document compilation**

In `gdocs_patch/compiler/lowering.py`, import `InsertPageBreak` and add:

```python
case InsertPageBreak():
    requests.append(
        {
            "insertPageBreak": {
                "location": {"index": edit.index, **context},
            }
        }
    )
```

Then expand `test_compile_document_lowers_every_supported_edit_in_one_batch` in `tests/compiler/test_document.py` by adding a target-only page break with a concrete text style and hard-coding its `insertPageBreak` and `updateTextStyle` requests into the expected batch. Use the existing source and target documents in that test; do not add another comprehensive test.

Run:

```bash
uv run pytest tests/compiler/test_lowering.py tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -q
```

Expected: PASS.

- [ ] **Step 5: Run complete verification**

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
git diff --check
```

Expected: all 194 or more tests pass, all static checks pass, and `git diff --check` emits no output.

- [ ] **Step 6: Commit page-break support**

```bash
git add gdocs_patch/compiler/content_stream.py gdocs_patch/compiler/document.py gdocs_patch/compiler/edit_script.py gdocs_patch/compiler/lowering.py gdocs_patch/compiler/__init__.py tests/compiler/test_document.py tests/compiler/test_edit_script.py tests/compiler/test_lowering.py
git commit -m "feat: compile page break edits"
```

- [ ] **Step 7: Perform the live round-trip check**

Use the supplied Claude XHTML as the target for document `1p0HNaILtDeJ-UH_tbi_KX7IKG2o7KW3IyIdG27XbeYU`, then read the document back through the CLI. Compare paragraph tags and visible text around `Custom build` through the final `Open question` paragraph.

Expected:

- `Custom build` is its own `h2` paragraph.
- `These items will be purpose built...` is the following normal paragraph.
- All later heading and paragraph tags align with the target.
- `Open question...` is a normal paragraph.
- No compiler-created blank terminal paragraph remains beyond the target structure.
- Provider-generated heading IDs, positioned objects, and equivalent text-run fragmentation may differ.
