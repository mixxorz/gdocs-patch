# EditScript Lowering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert every existing semantic `Edit` into ordered Google Docs `documents.batchUpdate` request dictionaries and wire that lowering into the complete document compiler.

**Architecture:** Add one explicit `compiler/lowering.py` module that serializes model values and matches each `Edit` without reflection or another IR. Most edits emit one request; nested bullets emit temporary-tab insertion followed by bullet creation, and table insertion translates the semantic table start to Google's preceding insertion location. `compile_document()` supplies tab/segment context and wraps the resulting request list.

**Tech Stack:** Python 3.12+, `uv`, pytest, Ruff, Fixit, Pyright, pre-commit.

## Global Constraints

- Work only in `/Users/mixxorz/Projects/gdocs_patch/.worktrees/feature-lowering` on branch `feature-lowering`; never modify `main` or `master`.
- Follow test-driven development: write each behavioral test first, run it, and confirm the expected failure before production changes.
- Keep models ordinary, mutable, hand-written, explicitly typed, and keyword-only.
- Keep ContentStream units as frozen dataclasses; `BulletPreset` becomes an ordinary model class shared by target documents and ContentStreams.
- Use explicit Google request dictionaries and explicit serializers; do not use reflection, automatic snake-case conversion, registries, runtime schema validation, another scheduling IR, or a Google API client dependency.
- Preserve EditScript order. Always include `tabId`; include `segmentId` only when non-`None`.
- Treat target `UNSET` style fields as resets: include writable fields in masks and omit `UNSET` values from payloads.
- Omit read-only paragraph heading/tab-stop fields and table-cell span fields from style payloads and masks.
- Tests must use hardcoded model/edit inputs and hardcoded expected dictionaries, not calculations that reproduce production logic.
- Add only the four agreed lowering tests: focused content/paragraph/bullets, focused tables, focused region context, and one comprehensive `compile_document()` stress test.
- Do not touch or commit `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json`.
- Commit each completed task. Write SDD reports under this worktree's `.superpowers/sdd/` directory.

---

### Task 1: Represent new bullet presets in target Documents

**Files:**
- Modify: `gdocs_patch/models/paragraph.py`
- Modify: `gdocs_patch/models/__init__.py`
- Modify: `gdocs_patch/compiler/content_stream.py`
- Modify: `tests/compiler/test_document.py`

**Interfaces:**
- Produces: `gdocs_patch.models.BulletPreset(*, preset: Literal[...], nesting_level: int = 0)`.
- Changes: `Paragraph.bullet` and `ParagraphBoundary.bullet` both accept `Bullet | BulletPreset | UnsetType`.
- Preserves: `from gdocs_patch.compiler import BulletPreset` through the compiler package's existing re-export.

- [ ] **Step 1: Change the existing paragraph normalization test to exercise target creation intent**

In `test_normalize_tree_normalizes_paragraph_text_and_bullet`, replace the existing `Bullet` input and expected boundary bullet with this hardcoded model:

```python
bullet = BulletPreset(
    preset="BULLET_DISC_CIRCLE_SQUARE",
    nesting_level=2,
)
```

Import `BulletPreset` from `gdocs_patch.models`. Keep this as the same existing test; do not add a fifth `normalize_tree` test.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
uv run pytest tests/compiler/test_document.py::test_normalize_tree_normalizes_paragraph_text_and_bullet -v
```

Expected: collection fails because `BulletPreset` is not exported by `gdocs_patch.models`.

- [ ] **Step 3: Add the ordinary model class and reuse it from ContentStream**

Move the exact preset literals currently declared by `compiler.content_stream.BulletPreset` into an ordinary class in `models/paragraph.py`:

```python
class BulletPreset(Model):
    def __init__(
        self,
        *,
        preset: Literal[
            "BULLET_GLYPH_PRESET_UNSPECIFIED",
            "BULLET_DISC_CIRCLE_SQUARE",
            "BULLET_DIAMONDX_ARROW3D_SQUARE",
            "BULLET_CHECKBOX",
            "BULLET_ARROW_DIAMOND_DISC",
            "BULLET_STAR_CIRCLE_SQUARE",
            "BULLET_ARROW3D_CIRCLE_SQUARE",
            "BULLET_LEFTTRIANGLE_DIAMOND_DISC",
            "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE",
            "BULLET_DIAMOND_CIRCLE_SQUARE",
            "NUMBERED_DECIMAL_ALPHA_ROMAN",
            "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
            "NUMBERED_DECIMAL_NESTED",
            "NUMBERED_UPPERALPHA_ALPHA_ROMAN",
            "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
            "NUMBERED_ZERODECIMAL_ALPHA_ROMAN",
        ],
        nesting_level: int = 0,
    ) -> None:
        self.preset = preset
        self.nesting_level = nesting_level
```

Update `Paragraph.bullet` to `Bullet | BulletPreset | UnsetType`. Export the class from `models/__init__.py`. Delete the frozen compiler dataclass definition and import the model class into `content_stream.py`; retain the compiler package re-export unchanged.

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
uv run pytest tests/compiler/test_document.py -v
uv run pytest
```

Expected: all 96 existing tests pass; the number remains unchanged because an existing test was strengthened.

- [ ] **Step 5: Commit**

```bash
git add gdocs_patch/models/paragraph.py gdocs_patch/models/__init__.py \
  gdocs_patch/compiler/content_stream.py tests/compiler/test_document.py
git commit -m "feat: represent target bullet presets"
```

---

### Task 2: Lower text, paragraph, bullet, and region edits

**Files:**
- Create: `gdocs_patch/compiler/lowering.py`
- Create: `tests/compiler/test_lowering.py`

**Interfaces:**
- Consumes: every non-table `Edit` class from `compiler.edit_script`, model style values, `tab_id`, and optional `segment_id`.
- Produces: `lower_edit_script(*, edit_script: EditScript, tab_id: str, segment_id: str | None = None) -> list[dict[str, object]]` in `compiler.lowering`.
- Task 4 will wire this function into `compiler.document`; leave the existing stub in `document.py` during this task.

- [ ] **Step 1: Write the focused content/paragraph/bullet test**

Create `tests/compiler/test_lowering.py`. Construct one hardcoded `EditScript` containing, in this order:

```python
InsertText(index=4, text="new")
DeleteContent(start_index=8, end_index=11)
ApplyTextStyle(
    start_index=1,
    end_index=4,
    text_style=TextStyle(
        bold=True,
        italic=False,
        font_size=Dimension(magnitude=12, unit="PT"),
        font_family="Roboto",
        font_weight=500,
        foreground_color=Color(red=0.1, green=0.2, blue=0.3),
        background_color=None,
        link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-linked"),
    ),
)
ApplyTextStyle(start_index=4, end_index=5, text_style=UNSET)
ApplyParagraphStyle(
    start_index=0,
    end_index=12,
    paragraph_style=ParagraphStyle(
        named_style_type="HEADING_2",
        alignment="CENTER",
        space_above=Dimension(magnitude=6, unit="PT"),
        border_bottom=ParagraphBorder(
            color=Color(red=0.4, green=0.5, blue=0.6),
            width=Dimension(magnitude=1, unit="PT"),
            padding=Dimension(magnitude=2, unit="PT"),
            dash_style="SOLID",
        ),
        shading_color=None,
        heading_id="read-only-heading",
        tab_stops=[
            TabStop(
                offset=Dimension(magnitude=36, unit="PT"),
                alignment="START",
            )
        ],
    ),
)
ApplyParagraphStyle(start_index=12, end_index=13, paragraph_style=UNSET)
CreateParagraphBullets(
    start_index=13,
    end_index=20,
    bullet_preset=BulletPreset(
        preset="BULLET_DISC_CIRCLE_SQUARE",
        nesting_level=2,
    ),
)
DeleteParagraphBullets(start_index=20, end_index=27)
```

Call `compiler.lowering.lower_edit_script(..., tab_id="tab-1")`. Assert one hardcoded request list with:

- exact body locations/ranges containing `tabId` and no `segmentId`;
- full explicit text and paragraph field-mask strings from the design;
- `weightedFontFamily`, optional-color, bookmark, border, dimension, and shading payload shapes;
- no `headingId` or `tabStops` in the paragraph payload or mask;
- empty style payloads for whole-style `UNSET` resets;
- `insertText` of `"\t\t"` at index 13 immediately before bullet creation;
- bullet range `{startIndex: 13, endIndex: 22, tabId: "tab-1"}`;
- final bullet deletion at the original target indices.

Write the full dictionaries literally in the assertion. Do not generate masks, locations, colors, or expected requests with helper code.

- [ ] **Step 2: Write the focused region-context test**

In the same file, add one test that lowers:

```python
EditScript(edits=[InsertText(index=3, text="header")])
```

once with `tab_id="tab-2", segment_id="header-1"` and once with `tab_id="tab-2"`. Hardcode equality against:

```python
[
    {
        "insertText": {
            "location": {
                "index": 3,
                "tabId": "tab-2",
                "segmentId": "header-1",
            },
            "text": "header",
        }
    }
]
```

and the same body request without `segmentId`.

- [ ] **Step 3: Run both tests and verify RED**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -v
```

Expected: collection fails because `gdocs_patch.compiler.lowering` does not exist.

- [ ] **Step 4: Implement explicit nested value serializers**

In `lowering.py`, define explicit typed functions for:

```python
serialize_dimension(value: Dimension) -> dict[str, object]
serialize_optional_color(value: Color | None) -> dict[str, object]
serialize_link(value: Link) -> dict[str, object]
serialize_paragraph_border(value: ParagraphBorder) -> dict[str, object]
serialize_text_style(value: TextStyle | UnsetType) -> dict[str, object]
serialize_paragraph_style(value: ParagraphStyle | UnsetType) -> dict[str, object]
```

Each function constructs exact Google camelCase dictionaries with direct `if value.field is not UNSET` statements. `serialize_link` explicitly matches `UrlLink`, `TabLink`, `BookmarkLink`, and `HeadingLink`; bookmark and heading wrappers include `tabId` only when their model value is not `UNSET`. Do not use `vars()`, generic recursion, snake-case conversion, metadata, or field registries.

Define these exact explicit mask strings:

```python
TEXT_STYLE_FIELDS = (
    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,"
    "weightedFontFamily,foregroundColor,backgroundColor,link"
)
PARAGRAPH_STYLE_FIELDS = (
    "namedStyleType,alignment,direction,lineSpacing,spacingMode,spaceAbove,"
    "spaceBelow,indentFirstLine,indentStart,indentEnd,keepLinesTogether,"
    "keepWithNext,avoidWidowAndOrphan,pageBreakBefore,borderBetween,borderTop,"
    "borderBottom,borderLeft,borderRight,shading"
)
```

Do not serialize `heading_id` or `tab_stops`.

- [ ] **Step 5: Implement the initial lowering loop**

Implement the public function and explicit match cases for `InsertText`, `DeleteContent`, `ApplyTextStyle`, `ApplyParagraphStyle`, `CreateParagraphBullets`, and `DeleteParagraphBullets`.

Build one context dictionary:

```python
context: dict[str, object] = {"tabId": tab_id}
if segment_id is not None:
    context["segmentId"] = segment_id
```

Use literal request dictionaries and `{**context}` for locations/ranges. Preserve edit order. For nested bullets, insert `"\t" * nesting_level`, increase only the bullet request's `endIndex`, and let level zero emit no temporary insertion. End the match with `raise NotImplementedError(type(edit).__name__)`; table edits remain deliberately unsupported in this task.

- [ ] **Step 6: Run focused tests and complete regression suite**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -v
uv run pytest
```

Expected: both new lowering tests and all prior tests pass, for 98 total tests.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/compiler/lowering.py tests/compiler/test_lowering.py
git commit -m "feat: lower content and paragraph edits"
```

---

### Task 3: Lower every table edit

**Files:**
- Modify: `gdocs_patch/compiler/lowering.py`
- Modify: `tests/compiler/test_lowering.py`

**Interfaces:**
- Extends: `lower_edit_script(...)` with every existing table `Edit` subtype.
- Adds explicit serializers for `TableColumn`, `TableRowStyle` edit fields, `TableCellStyle`, and `TableCellBorder`.
- Preserves the content and region behavior implemented in Task 2.

- [ ] **Step 1: Write one focused all-table-operations test**

Add one test with a hardcoded `EditScript` containing, in this order:

```python
InsertTable(index=10, rows=2, columns=3)
InsertTableRow(
    table_start_index=10,
    row_index=0,
    column_index=1,
    insert_below=True,
)
InsertTableColumn(
    table_start_index=10,
    row_index=1,
    column_index=0,
    insert_right=False,
)
DeleteTableRow(table_start_index=10, row_index=2, column_index=1)
DeleteTableColumn(table_start_index=10, row_index=0, column_index=2)
MergeTableCells(
    table_start_index=10,
    row_index=0,
    column_index=0,
    row_span=2,
    column_span=2,
)
UnmergeTableCells(
    table_start_index=10,
    row_index=1,
    column_index=1,
    row_span=2,
    column_span=2,
)
ApplyTableColumnProperties(
    table_start_index=10,
    column_index=1,
    column_properties=TableColumn(
        width_type="FIXED_WIDTH",
        width=Dimension(magnitude=72, unit="PT"),
    ),
)
ApplyTableColumnProperties(
    table_start_index=10,
    column_index=2,
    column_properties=UNSET,
)
ApplyTableRowStyle(
    table_start_index=10,
    row_index=0,
    min_height=Dimension(magnitude=24, unit="PT"),
    prevent_overflow=True,
    is_header=False,
)
ApplyTableCellStyle(
    table_start_index=10,
    row_index=0,
    column_index=0,
    row_span=2,
    column_span=2,
    cell_style=TableCellStyle(
        row_span=2,
        column_span=2,
        background_color=Color(red=0.7, green=0.8, blue=0.9),
        border_left=TableCellBorder(
            color=Color(red=0.1, green=0.2, blue=0.3),
            width=Dimension(magnitude=1, unit="PT"),
            dash_style="DASH",
        ),
        padding_top=Dimension(magnitude=4, unit="PT"),
        content_alignment="MIDDLE",
    ),
)
ApplyTableCellStyle(
    table_start_index=10,
    row_index=2,
    column_index=2,
    row_span=1,
    column_span=1,
    cell_style=UNSET,
)
```

Lower with `tab_id="tab-table", segment_id="footer-1"`. Hardcode every expected Google request dictionary. The assertion must prove:

- `insertTable.location.index` is 9 while every `tableStartLocation.index` is 10;
- every location includes both `tabId` and `segmentId`;
- row/column edits use exact `tableCellLocation` shapes;
- merge/unmerge/cell style use exact `tableRange` shapes;
- table column mask is exactly `"widthType,width"`;
- row mask is exactly `"minRowHeight,preventOverflow,tableHeader"`;
- cell mask is exactly `"backgroundColor,borderLeft,borderRight,borderTop,borderBottom,paddingLeft,paddingRight,paddingTop,paddingBottom,contentAlignment"`;
- cell payload omits read-only `rowSpan` and `columnSpan`;
- whole-style/property `UNSET` produces `{}` with the full mask.

- [ ] **Step 2: Run the table test and verify RED**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -v
```

Expected: the new test fails with `NotImplementedError: InsertTable`.

- [ ] **Step 3: Add explicit table serializers**

Add:

```python
TABLE_COLUMN_FIELDS = "widthType,width"
TABLE_ROW_FIELDS = "minRowHeight,preventOverflow,tableHeader"
TABLE_CELL_STYLE_FIELDS = (
    "backgroundColor,borderLeft,borderRight,borderTop,borderBottom,paddingLeft,"
    "paddingRight,paddingTop,paddingBottom,contentAlignment"
)
```

Implement direct, typed serializers for `TableColumn | UnsetType`, `TableCellBorder`, and `TableCellStyle | UnsetType`. Build row payload directly from the three values carried by `ApplyTableRowStyle`. Omit every `UNSET` value. Never serialize table-cell `row_span` or `column_span` as style fields.

- [ ] **Step 4: Add every explicit table match case**

Extend the existing lowering loop with literal request shapes for all table edits. Use:

```python
{"index": edit.index - 1, **context}
```

only for `InsertTable.location`. Use `edit.table_start_index` unchanged everywhere else. Use singleton `columnIndices` and `rowIndices` lists for property/style edits. Preserve script order exactly.

- [ ] **Step 5: Run focused and complete tests**

Run:

```bash
uv run pytest tests/compiler/test_lowering.py -v
uv run pytest
```

Expected: all three lowering tests pass and the complete suite reports 99 passed.

- [ ] **Step 6: Commit**

```bash
git add gdocs_patch/compiler/lowering.py tests/compiler/test_lowering.py
git commit -m "feat: lower table edits"
```

---

### Task 4: Wire lowering into comprehensive document compilation

**Files:**
- Modify: `gdocs_patch/compiler/document.py`
- Modify: `gdocs_patch/compiler/__init__.py`
- Modify: `tests/compiler/test_document.py`

**Interfaces:**
- Consumes: `compiler.lowering.lower_edit_script` from Tasks 2 and 3.
- Produces: the existing `compile_document(*, source: Document, target: Document) -> dict[str, object]` with real low-level requests.
- Preserves: `from gdocs_patch.compiler import lower_edit_script` and `compile_document`.

- [ ] **Step 1: Write the comprehensive stress test with hardcoded Documents**

Add one test named `test_compile_document_lowers_every_supported_edit_in_one_batch` to `tests/compiler/test_document.py`.

Build one source and target `Document` with the same tab and segment IDs and source revision `revision-stress`. Use ordinary hardcoded model constructors, opaque table/row/cell keys, and these regions:

1. **Body paragraphs:** localized text insertion, localized deletion, changed text style, reset text style, changed paragraph style, reset paragraph style, an existing bullet removed, and two new preset list items at nesting levels zero and two.
2. **A new 2x2 table:** target-only and followed by a paragraph boundary so normalization represents Google's table insertion shape.
3. **A keyed growth table:** source 2x2 and target 3x3, with one new keyed row and one new keyed column, text in every cell, changed column properties, changed row style, and changed cell style.
4. **A keyed shrink table:** source 3x3 and target 2x2 so row and column deletion are both emitted.
5. **A keyed merge table:** source contains separate keyed cells and target spans the matching head cell across a 2x2 rectangle.
6. **A keyed unmerge table:** source has a 2x2 spanning head cell and target contains separate keyed cells.
7. **Header, footer, and footnote segments:** retain the same IDs; include at least one text edit so the final requests prove segment routing for all three segment maps.

The combination must cause every existing concrete `Edit` class to appear at least once:

```text
InsertText, DeleteContent,
CreateParagraphBullets, DeleteParagraphBullets,
ApplyTextStyle, ApplyParagraphStyle,
InsertTable, InsertTableRow, InsertTableColumn,
DeleteTableRow, DeleteTableColumn,
MergeTableCells, UnmergeTableCells,
ApplyTableColumnProperties, ApplyTableRowStyle, ApplyTableCellStyle
```

Call `compile_document(source=source, target=target)` and assert equality with one fully literal dictionary containing the complete deterministic request list and `"writeControl": {"requiredRevisionId": "revision-stress"}`. Write every nested request directly in the assertion before running it. Do not derive expected indices, ranges, masks, payloads, locations, or requests with helper code. Manually check each literal index against the hardcoded source/target model widths and the focused lowering expectations.

- [ ] **Step 2: Run the stress test and verify RED**

Run:

```bash
uv run pytest tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -v
```

Expected: failure from the still-unimplemented `document.lower_edit_script` stub.

- [ ] **Step 3: Wire the implemented lowering function into the pipeline**

Delete the stub from `document.py` and import:

```python
from .lowering import lower_edit_script
```

Update `compiler/__init__.py` to import `lower_edit_script` from `.lowering` rather than indirectly from `.document`. Do not change `compile_document()` ordering, batching, tab/segment checks, or `writeControl` behavior.

- [ ] **Step 4: Run the stress test and address only real integration defects**

Run:

```bash
uv run pytest tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -v
```

Expected: PASS. If it reveals an actual normalization, reconciliation, or lowering defect, keep the hardcoded expected target behavior unchanged, make the smallest production correction, and rerun this test. Do not weaken the test or calculate its expectations.

- [ ] **Step 5: Run all compiler tests and the complete suite**

Run:

```bash
uv run pytest tests/compiler -v
uv run pytest
```

Expected: all four lowering tests pass and the complete suite reports 100 passed.

- [ ] **Step 6: Commit**

```bash
git add gdocs_patch/compiler/document.py gdocs_patch/compiler/__init__.py \
  tests/compiler/test_document.py
git commit -m "feat: lower document edits to batch requests"
```

---

### Task 5: Final verification and branch evidence

**Files:**
- Modify only if a verification tool reports a concrete issue in files changed by Tasks 1-4.

**Interfaces:**
- Produces: a verified feature branch ready for final review and integration.

- [ ] **Step 1: Confirm isolation and scope**

Run:

```bash
git branch --show-current
git status --short
git diff --stat main...HEAD
git -C /Users/mixxorz/Projects/gdocs_patch status --short --branch
```

Expected: current branch is `feature-lowering`; feature changes exist only in the worktree; main contains no lowering changes; the untracked sample JSON on main remains untouched.

- [ ] **Step 2: Run all required verification tools**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint
uv run pyright
uv run pre-commit run --all-files
```

Expected: 100 tests pass and every lint, format, codemod, type, and hook command exits successfully.

- [ ] **Step 3: Commit tool-required corrections, if any**

If and only if verification changed files or exposed a defect, rerun the covering command and commit the minimal correction:

```bash
git add gdocs_patch tests
git commit -m "fix: address lowering verification"
```

If no files changed, do not create an empty commit.
