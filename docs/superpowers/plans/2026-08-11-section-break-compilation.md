# SectionBreak Compilation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile retained, inserted, deleted, and restyled Google Docs SectionBreaks while preserving valid paragraph boundaries and correcting the same insertion behavior for new tables.

**Architecture:** Normalize SectionBreaks as width-one ContentStream units. Reconciliation emits semantic section edits and records whether a structure's preceding paragraph boundary was inserted or retained; lowering alone expands those edits into Google's newline cleanup and deletion-sentinel requests. Section formatting remains in the target-index formatting phase.

**Tech Stack:** Python 3.12+, `uv`, pytest, Ruff, Fixit, Pyright, pre-commit, Google Docs API v1 request dictionaries.

## Global Constraints

- Work only in `/Users/mixxorz/Projects/gdocs_patch/.worktrees/exploratory-google-docs` on branch `exploratory-google-docs`.
- Treat valid Document and ContentStream structure as a precondition; add no runtime structural validation.
- Keep model classes ordinary, mutable, hand-written, explicitly typed, keyword-only, and snake_case.
- Keep ContentStream units and Edit operations frozen keyword-only dataclasses.
- Use inline `Literal` types rather than a global enum.
- Tests use hardcoded valid inputs and outputs and cover behavior, not definitions, defensive checks, or private delegation.
- Preserve intentional `UNSET` behavior and ignore SectionStyle's read-only header/footer IDs during compilation.
- Modify existing tests when they already cover the behavior; do not add a standalone regression test for the table issue.

---

### Task 1: Normalize SectionBreaks into ContentStream

**Files:**
- Modify: `gdocs_patch/compiler/content_stream.py`
- Modify: `gdocs_patch/compiler/document.py`
- Modify: `gdocs_patch/compiler/__init__.py`
- Modify: `tests/compiler/test_document.py`

**Interfaces:**
- Consumes: existing `SectionBreak`, `SectionStyle`, `ContentUnit`, and recursive `normalize_tree()` traversal.
- Produces: `SectionBreakUnit(style: SectionStyle)`, width-one comparison values, and body streams whose first unit starts at UTF-16 index zero.

- [ ] **Step 1: Update the existing normalization tests with hardcoded SectionBreak units**

Add an initial and a later break to `test_normalize_tree_normalizes_kitchen_sink_body_in_document_order` and include both in the expected object-level equality:

```python
initial_section_style = SectionStyle(
    content_direction="LEFT_TO_RIGHT",
    section_type="CONTINUOUS",
)
later_section_style = SectionStyle(
    content_direction="RIGHT_TO_LEFT",
    section_type="NEXT_PAGE",
)
body = Body(
    content=[
        SectionBreak(style=initial_section_style),
        Paragraph(elements=[TextRun(content="Go\n")], bullet=bullet),
        SectionBreak(style=later_section_style),
        table,
        Paragraph(elements=[TextRun(content="X"), Equation(), TextRun(content="\n")]),
    ]
)

assert normalize_tree(body) == ContentStream(
    items=[
        SectionBreakUnit(style=initial_section_style),
        TextUnit(content="G"),
        TextUnit(content="o"),
        ParagraphBoundary(bullet=bullet),
        SectionBreakUnit(style=later_section_style),
        TableUnit(
            table_key="table-kitchen",
            rows=[
                TableRowUnit(
                    row_key="row-kitchen",
                    cells=[
                        TableCellUnit(
                            cell_key="cell-kitchen",
                            content=ContentStream(
                                items=[
                                    TextUnit(content="T"),
                                    ParagraphBoundary(),
                                ]
                            ),
                        )
                    ],
                )
            ],
        ),
        TextUnit(content="X"),
        EquationUnit(),
        ParagraphBoundary(),
    ]
)
```

In `test_normalize_document_normalizes_every_loaded_tab_region`, put an initial `SectionBreak` in both loaded tab bodies and expect an initial `SectionBreakUnit`. Add the behavioral index assertion:

```python
assert content.tabs["root"].body.utf16_index(0) == 0
assert content.tabs["root"].body.utf16_index(1) == 1
```

Keep headers, footers, and footnotes unchanged; they do not contain SectionBreaks.

- [ ] **Step 2: Run the focused tests and confirm the missing behavior**

Run:

```bash
uv run pytest \
  tests/compiler/test_document.py::test_normalize_tree_normalizes_kitchen_sink_body_in_document_order \
  tests/compiler/test_document.py::test_normalize_document_normalizes_every_loaded_tab_region -v
```

Expected: FAIL because `SectionBreakUnit` is not defined/exported and normalization currently drops SectionBreaks.

- [ ] **Step 3: Add the unit and normalization branch**

In `content_stream.py`:

```python
from gdocs_patch.models import SectionStyle


@dataclass(frozen=True, kw_only=True)
class SectionBreakUnit(ContentUnit):
    style: SectionStyle

    @property
    def utf16_width(self) -> int:
        return 1
```

In `ContentStream.comparison_values()` add:

```python
elif isinstance(item, SectionBreakUnit):
    values.append(("section_break", ""))
```

In `document.py`, import `SectionBreak` and `SectionBreakUnit`, then add before the generic child traversal:

```python
if isinstance(tree, SectionBreak):
    return ContentStream(items=[SectionBreakUnit(style=tree.style)])
```

Remove the reconstruction that sets `normalized_body.utf16_start_index = 1`; use `normalize_tree(body, ...)` directly. Export `SectionBreakUnit` from `compiler/__init__.py`.

- [ ] **Step 4: Run the compiler document tests**

Run:

```bash
uv run pytest tests/compiler/test_document.py -q
```

Expected: PASS after updating any existing hardcoded normalized body that now includes its modeled initial SectionBreak.

- [ ] **Step 5: Commit the normalization slice**

```bash
git add gdocs_patch/compiler/content_stream.py gdocs_patch/compiler/document.py \
  gdocs_patch/compiler/__init__.py tests/compiler/test_document.py
git commit -m "feat: normalize section breaks into content streams"
```

---

### Task 2: Generate semantic SectionBreak and corrected table edits

**Files:**
- Modify: `gdocs_patch/compiler/edit_script.py`
- Modify: `gdocs_patch/compiler/__init__.py`
- Modify: `tests/compiler/test_edit_script.py`

**Interfaces:**
- Consumes: `SectionBreakUnit`, SequenceMatcher opcodes, source/target UTF-16 indices, and valid immediate boundary adjacency.
- Produces:
  - `InsertSectionBreak(index, section_type, preceding_boundary)`
  - `DeleteSectionBreak(index)`
  - `ApplySectionStyle(start_index, end_index, section_style)`
  - `InsertTable(..., preceding_boundary)`

- [ ] **Step 1: Add hardcoded reconciliation tests for the four behaviors**

Use an initial `SectionBreakUnit` in every body-shaped stream.

For a paragraph split, use:

```python
source = ContentStream(
    items=[
        SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
        TextUnit(content="A"),
        TextUnit(content="B"),
        ParagraphBoundary(),
    ]
)
target = ContentStream(
    items=[
        SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
        TextUnit(content="A"),
        ParagraphBoundary(),
        SectionBreakUnit(style=SectionStyle(section_type="NEXT_PAGE")),
        TextUnit(content="B"),
        ParagraphBoundary(),
    ]
)
assert generate_edit_script(source=source, target=target).edits == [
    InsertSectionBreak(
        index=3,
        section_type="NEXT_PAGE",
        preceding_boundary="INSERTED",
    )
]
```

For insertion between existing paragraphs, use source `initial, "A", boundary, "B", terminal boundary` and target `initial, "A", boundary, new break, "B", terminal boundary`. Expect:

```python
InsertSectionBreak(
    index=3,
    section_type="CONTINUOUS",
    preceding_boundary="RETAINED",
)
```

Use the inverse streams to expect:

```python
DeleteSectionBreak(index=3)
```

For retained style, compare an initial source break with `margin_left=72 PT`, `default_header_id="source-header"`, and a target break with `margin_left=90 PT`, `default_header_id="target-header"`. Expect only:

```python
ApplySectionStyle(
    start_index=0,
    end_index=1,
    section_style=target_style,
)
```

Add two concise error assertions: retained `CONTINUOUS -> NEXT_PAGE` raises `UnsupportedTransformation`, and concrete `margin_left -> UNSET` raises it. Do not add invalid ContentStream tests.

Replace `test_generate_edit_script_inserts_text_and_table_between_existing_tables` rather than adding a table regression test. Rename it `test_generate_edit_script_inserts_table_between_existing_paragraphs` and use these hardcoded streams:

```python
initial_section = SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS"))
empty_table = TableUnit(
    rows=[
        TableRowUnit(
            cells=[TableCellUnit(content=ContentStream(items=[ParagraphBoundary()]))]
        )
    ]
)
source = ContentStream(
    items=[
        initial_section,
        TextUnit(content="A"),
        ParagraphBoundary(),
        TextUnit(content="B"),
        ParagraphBoundary(),
    ]
)
target = ContentStream(
    items=[
        initial_section,
        TextUnit(content="A"),
        ParagraphBoundary(),
        empty_table,
        TextUnit(content="B"),
        ParagraphBoundary(),
    ]
)

assert generate_edit_script(source=source, target=target).edits == [
    InsertTable(
        index=3,
        rows=1,
        columns=1,
        preceding_boundary="RETAINED",
    )
]
```

- [ ] **Step 2: Run the focused edit-script tests**

Run the named SectionBreak tests and the modified table insertion test with `-v`.

Expected: FAIL because the new Edit types and boundary mode do not exist and SectionBreak insertion is unsupported.

- [ ] **Step 3: Add the Edit types and writable style projection**

Import `Literal`, `SectionStyle`, and `SectionBreakUnit`. Define:

```python
@dataclass(frozen=True, kw_only=True)
class InsertSectionBreak(Edit):
    index: int
    section_type: Literal[
        "SECTION_TYPE_UNSPECIFIED",
        "CONTINUOUS",
        "NEXT_PAGE",
    ]
    preceding_boundary: Literal["INSERTED", "RETAINED"]


@dataclass(frozen=True, kw_only=True)
class DeleteSectionBreak(Edit):
    index: int


@dataclass(frozen=True, kw_only=True)
class ApplySectionStyle(Edit):
    start_index: int
    end_index: int
    section_style: SectionStyle
```

Extend `InsertTable` with required:

```python
preceding_boundary: Literal["INSERTED", "RETAINED"]
```

Add one explicit `writable_section_style()` tuple containing only columns, separator, direction, first-page header/footer use, page orientation, page number, and six margins. Do not include `section_type` or header/footer IDs.

- [ ] **Step 4: Reconcile structural boundary pairs**

When building `target_paragraph_utf16_range_by_target_pos`, reset `paragraph_start_utf16_index` to the structural unit's end after either `TableUnit` or `SectionBreakUnit`. This keeps the following paragraph's range from including the preceding table or section break.

In the changed-content loop, when a target `ParagraphBoundary` is immediately followed within the same target opcode by a `TableUnit` or `SectionBreakUnit`, do not emit it through `InsertText`; advance to the structure and mark its `preceding_boundary="INSERTED"`.

When an inserted structure is not paired with a boundary in its target opcode, use `preceding_boundary="RETAINED"`.

Pass the mode into `compile_inserted_table()`. Add SectionBreak insertion using the same source/target offset calculation as tables:

```python
InsertSectionBreak(
    index=insertion_utf16_index + section_break_utf16_offset,
    section_type=target_section_unit.style.section_type,
    preceding_boundary=preceding_boundary,
)
```

Reject a new break whose `section_type is UNSET`.

When a delete/replace opcode removes a SectionBreak but retains its preceding boundary, emit `DeleteSectionBreak` at the source break index rather than a one-unit `DeleteContent`. When the source opcode includes both `ParagraphBoundary + SectionBreakUnit`, retain ordinary `DeleteContent` because the target intentionally removes the boundary too.

- [ ] **Step 5: Generate SectionStyle edits and errors**

In the formatting match, add `SectionBreakUnit` handling:

```python
case SectionBreakUnit() as target_section_unit:
    source_section_unit = (
        source_unit if isinstance(source_unit, SectionBreakUnit) else None
    )
```

For a retained break, reject a changed `section_type`. Compare writable tuples while ignoring IDs. Reject each source concrete/target `UNSET` transition. Emit `ApplySectionStyle` for a new break with concrete writable fields or a retained break whose writable tuple changed.

Add `ApplySectionStyle` to the formatting types so it runs after content and before text styles. Export all new public compiler types.

- [ ] **Step 6: Run edit-script and table tests**

Run:

```bash
uv run pytest tests/compiler/test_edit_script.py tests/compiler/test_table_edit_script.py -q
```

Expected: PASS. Update existing `InsertTable` expected values and constructors with the correct hardcoded boundary mode; do not add compatibility defaults merely to avoid test changes.

- [ ] **Step 7: Commit reconciliation**

```bash
git add gdocs_patch/compiler/edit_script.py gdocs_patch/compiler/__init__.py \
  tests/compiler/test_edit_script.py tests/compiler/test_table_edit_script.py
git commit -m "feat: reconcile section break edits"
```

---

### Task 3: Lower SectionBreak edits and structural boundary cleanup

**Files:**
- Modify: `gdocs_patch/compiler/lowering.py`
- Modify: `tests/compiler/test_lowering.py`

**Interfaces:**
- Consumes: the semantic edits from Task 2.
- Produces: exact Google Docs `insertSectionBreak`, `deleteContentRange`, and `updateSectionStyle` request dictionaries; corrected `insertTable` request sequences.

- [ ] **Step 1: Update the existing table lowering test**

Change its inserted table to:

```python
InsertTable(
    index=10,
    rows=2,
    columns=3,
    preceding_boundary="RETAINED",
)
```

Immediately after the expected `insertTable`, hardcode the cleanup request. A blank 2x3 table has width `2 + 2 * (1 + 2 * 3) == 16`, so the extra boundary is at `26..27`:

```python
{
    "deleteContentRange": {
        "range": {
            "startIndex": 26,
            "endIndex": 27,
            "tabId": "tab-table",
            "segmentId": "footer-1",
        }
    }
}
```

- [ ] **Step 2: Add one hardcoded SectionBreak lowering test**

Construct one `EditScript` containing:

```python
(
    InsertSectionBreak(
        index=10,
        section_type="NEXT_PAGE",
        preceding_boundary="INSERTED",
    ),
)
(
    InsertSectionBreak(
        index=20,
        section_type="CONTINUOUS",
        preceding_boundary="RETAINED",
    ),
)
(DeleteSectionBreak(index=30),)
(
    ApplySectionStyle(
        start_index=40,
        end_index=41,
        section_style=SectionStyle(
            columns=[
                SectionColumn(
                    width=Dimension(magnitude=240, unit="PT"),
                    padding_end=Dimension(magnitude=18, unit="PT"),
                )
            ],
            column_separator_style="BETWEEN_EACH_COLUMN",
            content_direction="RIGHT_TO_LEFT",
            section_type="CONTINUOUS",
            default_header_id="ignored-header",
            use_first_page_header_footer=True,
            flip_page_orientation=True,
            page_number_start=3,
            margin_left=Dimension(magnitude=72, unit="PT"),
            margin_right=Dimension(magnitude=72, unit="PT"),
        ),
    ),
)
```

Hardcode these request facts:

- inserted-boundary break: `insertSectionBreak.location.index == 9`, no cleanup;
- retained-boundary break: location `19`, then delete `21..22`;
- deletion sentinels for break index `30`: insert newline at `29`, insert newline at `32`, delete `30..32`, delete `30..31`;
- section update range `40..41`, payload excludes `sectionType` and `defaultHeaderId`, and fields are `columnProperties,columnSeparatorStyle,contentDirection,useFirstPageHeaderFooter,flipPageOrientation,pageNumberStart,marginLeft,marginRight`.

- [ ] **Step 3: Run the lowering tests and confirm failure**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -q
```

Expected: FAIL because the new semantic edits are not lowered and table cleanup is absent.

- [ ] **Step 4: Implement table cleanup in lowering**

After `insertTable`, only for `preceding_boundary == "RETAINED"`, calculate the blank table width inline:

```python
blank_table_utf16_width = 2 + edit.rows * (1 + 2 * edit.columns)
extra_boundary_start_index = edit.index + blank_table_utf16_width
```

Append `deleteContentRange` for that index through `+ 1`, using the same tab/segment context. Add a natural comment explaining that Google creates the table as a blank grid before cell content requests run.

- [ ] **Step 5: Implement SectionBreak insertion and sentinel deletion**

Lower `InsertSectionBreak` to location `edit.index - 1`. For `"RETAINED"`, append a cleanup deletion at `edit.index + 1 .. edit.index + 2`.

Lower `DeleteSectionBreak(index=s)` to exactly four requests:

```python
insertText("\n", index=s - 1)
insertText("\n", index=s + 2)
deleteContentRange(s, s + 2)
deleteContentRange(s, s + 1)
```

Use prose comments explaining that the temporary paragraphs inherit each neighboring paragraph's formatting and prevent list/style collapse.

- [ ] **Step 6: Serialize concrete SectionStyle fields**

Add explicit serialization for `SectionColumn` and SectionStyle. Map:

```text
columns                       -> columnProperties
column_separator_style        -> columnSeparatorStyle
content_direction             -> contentDirection
use_first_page_header_footer  -> useFirstPageHeaderFooter
flip_page_orientation         -> flipPageOrientation
page_number_start             -> pageNumberStart
margin_top                    -> marginTop
margin_bottom                 -> marginBottom
margin_left                   -> marginLeft
margin_right                  -> marginRight
margin_header                 -> marginHeader
margin_footer                 -> marginFooter
```

Serialize only concrete values and return the comma-joined mask in that order. Never serialize `section_type` or any header/footer ID. Lower `ApplySectionStyle` to `updateSectionStyle` with the edit's target range and tab context; valid models ensure it is body-only, so no special validation branch is needed.

- [ ] **Step 7: Run lowering tests**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit lowering**

```bash
git add gdocs_patch/compiler/lowering.py tests/compiler/test_lowering.py
git commit -m "feat: lower section break edits"
```

---

### Task 4: Exercise SectionBreaks through compile_document

**Files:**
- Modify: `tests/compiler/test_document.py`

**Interfaces:**
- Consumes: `normalize_document()`, `generate_edit_script()`, and `lower_edit_script()` completed in Tasks 1–3.
- Produces: hardcoded end-to-end evidence that one batch can insert, delete, and restyle sections while preserving all existing supported edits.

- [ ] **Step 1: Extend the existing comprehensive compile test**

In `test_compile_document_lowers_every_supported_edit_in_one_batch`:

- change the target initial SectionBreak to a concrete writable style such as `margin_left=72 PT` while retaining its source `section_type`;
- place one additional source `SectionBreak(section_type="CONTINUOUS")` between two existing paragraphs and omit it from the target to exercise `DeleteSectionBreak`;
- place one target-only `SectionBreak(section_type="NEXT_PAGE", margin_right=72 PT)` between two other existing paragraphs to exercise `InsertSectionBreak` and `ApplySectionStyle`;
- keep a terminal paragraph after every final table and maintain valid body structure;
- update the single existing hardcoded expected batch with the exact insertion, sentinel deletion, section-style, and corrected table-cleanup requests in emitted order.

Do not compute expected requests in the test. Keep the source, target, and expected request dictionaries literal.

- [ ] **Step 2: Run the comprehensive test**

Run:

```bash
uv run pytest \
  tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -v
```

Expected: PASS with the complete literal request list. If an index differs, verify it against the hardcoded source and target widths before correcting the expected value; do not derive expectations in test code.

- [ ] **Step 3: Run all compiler tests**

Run:

```bash
uv run pytest tests/compiler -q
```

Expected: PASS.

- [ ] **Step 4: Commit end-to-end coverage**

```bash
git add tests/compiler/test_document.py
git commit -m "test: compile section breaks end to end"
```

---

### Task 5: Verify automated and live behavior

**Files:**
- Modify only if a verification failure reveals a defect in the files already listed.
- Do not commit temporary live-test scripts.

**Interfaces:**
- Consumes: complete SectionBreak compiler behavior.
- Produces: repository-wide verification and fetched-document evidence.

- [ ] **Step 1: Run the full required automated checks**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: every command exits zero. Record the pytest pass count in the completion report.

- [ ] **Step 2: Run a live insertion and style round trip**

Using document `1h9BRMe8srmNYCqMI_tHrYNaP1PHjYNGZkrpCTtDl5xA`, use the real path:

```text
get_document -> parse -> assign opaque table keys -> copy target
-> compile_document -> batch_update -> get_document -> parse -> normalize_document
```

Insert a SectionBreak between existing paragraphs, set at least one writable style, and compare the fetched target region's hardcoded structural sequence, UTF-16 width, section type, and writable style with the target. Confirm recompiling fetched source to the same target emits no requests after assigning opaque provider keys.

- [ ] **Step 3: Run a live sentinel deletion round trip**

Delete the inserted break through `compile_document`, fetch again, and verify both neighboring paragraphs retain their original text, list IDs, nesting levels, paragraph styles, bullet text styles, and newline text styles. Confirm the normalized body has its original width and no extra paragraph boundary.

- [ ] **Step 4: Run a live table insertion round trip**

Insert a small table between two existing paragraphs through `compile_document`. Verify the fetched normalized sequence and width equal the target and no extra blank paragraph exists. Remove the table through the compiler and verify the original neighboring content and formatting return.

- [ ] **Step 5: Remove temporary artifacts and commit fixes if any**

Check:

```bash
git status --short
git diff --check
```

Remove any temporary live-test script. If live or automated verification required code changes, rerun all checks and commit those focused fixes. Leave the worktree clean.
