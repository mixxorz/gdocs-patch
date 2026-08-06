# Normalize Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize supported Google Docs model trees into the existing `ContentStream` representation.

**Architecture:** Add optional opaque keys to table model nodes, then implement `normalize_tree` as a direct recursive walk over the existing `TreeNode.children` API. Paragraphs emit their child units followed by a boundary; tables preserve nested cell streams.

**Tech Stack:** Python 3.12+, pytest, uv, Ruff, Fixit, Pyright

## Global Constraints

- Add exactly four `normalize_tree` tests: paragraph, complex table, opaque equation, and kitchen sink.
- Tests use hardcoded model inputs and hardcoded output assertions; they do not calculate expected output from inputs.
- Emit one `TextUnit` per Python character.
- Only the paragraph's final `"\n"` is represented by `ParagraphBoundary`; earlier newlines remain `TextUnit` objects.
- Use the existing `TreeNode.children` traversal API directly. Do not add a walker, visitor, registry, or private normalization helpers.
- Keep `Table`, `TableRow`, and `TableCell` keys optional and copy supplied opaque keys unchanged.
- Preserve `UNSET`, mutable hand-written model classes, keyword-only constructors, and explicit typing.
- Do not modify or commit `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json`.

---

### Task 1: Normalize supported tree content

**Files:**
- Modify: `gdocs_patch/models/table.py`
- Modify: `gdocs_patch/compiler/document.py`
- Create: `tests/compiler/test_document.py`

**Interfaces:**
- Consumes: existing `TreeNode.children`, `ContentStream`, `TextUnit`, `EquationUnit`, `ParagraphBoundary`, `TableUnit`, `TableRowUnit`, and `TableCellUnit` APIs.
- Produces: `normalize_tree(tree: TreeNode) -> ContentStream`; optional `table_key`, `row_key`, and `cell_key` constructor arguments and attributes.

- [ ] **Step 1: Add all four failing behavioral tests**

Create `tests/compiler/test_document.py` with exactly these four tests. The assertions are deliberately explicit so expected normalization is not derived from the input tree.

```python
from gdocs_patch.compiler import (
    ContentStream,
    EquationUnit,
    ParagraphBoundary,
    TableUnit,
    TextUnit,
    normalize_tree,
)
from gdocs_patch.models import (
    UNSET,
    Body,
    Bullet,
    Color,
    Dimension,
    Equation,
    Paragraph,
    ParagraphStyle,
    Table,
    TableCell,
    TableCellStyle,
    TableColumn,
    TableRow,
    TextRun,
    TextStyle,
)


def test_normalize_tree_normalizes_paragraph_text_styles_and_bullets() -> None:
    first_style = TextStyle(bold=True)
    final_style = TextStyle(italic=True)
    paragraph_style = ParagraphStyle(alignment="CENTER")
    bullet = Bullet(list_id="list-opaque", nesting_level=1)
    body = Body(
        content=[
            Paragraph(
                elements=[
                    TextRun(content="A\n", text_style=first_style),
                    TextRun(content="🌍\n", text_style=final_style),
                ],
                style=paragraph_style,
                bullet=bullet,
            )
        ]
    )

    stream = normalize_tree(body)

    assert len(stream.items) == 4
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "A"
    assert stream.items[0].text_style is first_style
    assert isinstance(stream.items[1], TextUnit)
    assert stream.items[1].content == "\n"
    assert stream.items[1].text_style is first_style
    assert isinstance(stream.items[2], TextUnit)
    assert stream.items[2].content == "🌍"
    assert stream.items[2].text_style is final_style
    assert isinstance(stream.items[3], ParagraphBoundary)
    assert stream.items[3].text_style is final_style
    assert stream.items[3].paragraph_style is paragraph_style
    assert stream.items[3].bullet is bullet


def test_normalize_tree_preserves_complex_table_shape_content_and_styles() -> None:
    header_style = TableCellStyle(
        column_span=2,
        background_color=Color(red=0.25, green=0.5, blue=0.75),
    )
    left_style = TableCellStyle(content_alignment="MIDDLE")
    fixed_column = TableColumn(
        width_type="FIXED_WIDTH",
        width=Dimension(magnitude=72, unit="PT"),
    )
    even_column = TableColumn(width_type="EVENLY_DISTRIBUTED")
    table = Table(
        table_key="table-abcdef",
        column_styles=[fixed_column, even_column],
        rows=[
            TableRow(
                row_key="row-header",
                min_height=Dimension(magnitude=24, unit="PT"),
                prevent_overflow=True,
                is_header=True,
                cells=[
                    TableCell(
                        cell_key="cell-header",
                        style=header_style,
                        content=[
                            Paragraph(elements=[TextRun(content="Head\n")])
                        ],
                    )
                ],
            ),
            TableRow(
                row_key="row-body",
                prevent_overflow=False,
                cells=[
                    TableCell(
                        cell_key="cell-left",
                        style=left_style,
                        content=[Paragraph(elements=[TextRun(content="L\n")])],
                    ),
                    TableCell(
                        cell_key="cell-right",
                        content=[
                            Paragraph(elements=[TextRun(content="R1\n")]),
                            Paragraph(elements=[TextRun(content="R2\n")]),
                        ],
                    ),
                ],
            ),
        ],
    )

    stream = normalize_tree(Body(content=[table]))

    assert len(stream.items) == 1
    table_unit = stream.items[0]
    assert isinstance(table_unit, TableUnit)
    assert table_unit.table_key == "table-abcdef"
    assert table_unit.column_properties == [fixed_column, even_column]
    assert len(table_unit.rows) == 2

    header_row = table_unit.rows[0]
    assert header_row.row_key == "row-header"
    assert header_row.min_height == Dimension(magnitude=24, unit="PT")
    assert header_row.prevent_overflow is True
    assert header_row.is_header is True
    assert len(header_row.cells) == 1
    assert header_row.cells[0].cell_key == "cell-header"
    assert header_row.cells[0].row_span == 1
    assert header_row.cells[0].column_span == 2
    assert header_row.cells[0].style is header_style
    assert len(header_row.cells[0].content.items) == 5
    assert isinstance(header_row.cells[0].content.items[0], TextUnit)
    assert header_row.cells[0].content.items[0].content == "H"
    assert isinstance(header_row.cells[0].content.items[4], ParagraphBoundary)

    body_row = table_unit.rows[1]
    assert body_row.row_key == "row-body"
    assert body_row.min_height is UNSET
    assert body_row.prevent_overflow is False
    assert body_row.is_header is UNSET
    assert len(body_row.cells) == 2
    assert body_row.cells[0].cell_key == "cell-left"
    assert body_row.cells[0].row_span == 1
    assert body_row.cells[0].column_span == 1
    assert body_row.cells[0].style is left_style
    assert len(body_row.cells[0].content.items) == 2
    assert isinstance(body_row.cells[0].content.items[0], TextUnit)
    assert body_row.cells[0].content.items[0].content == "L"
    assert isinstance(body_row.cells[0].content.items[1], ParagraphBoundary)
    assert body_row.cells[1].cell_key == "cell-right"
    assert body_row.cells[1].row_span == 1
    assert body_row.cells[1].column_span == 1
    assert body_row.cells[1].style is UNSET
    assert len(body_row.cells[1].content.items) == 6
    assert isinstance(body_row.cells[1].content.items[0], TextUnit)
    assert body_row.cells[1].content.items[0].content == "R"
    assert isinstance(body_row.cells[1].content.items[2], ParagraphBoundary)
    assert isinstance(body_row.cells[1].content.items[3], TextUnit)
    assert body_row.cells[1].content.items[3].content == "R"
    assert isinstance(body_row.cells[1].content.items[5], ParagraphBoundary)


def test_normalize_tree_normalizes_opaque_equations_in_paragraphs() -> None:
    final_style = TextStyle(underline=True)
    body = Body(
        content=[
            Paragraph(
                elements=[
                    TextRun(content="A"),
                    Equation(),
                    TextRun(content="B\n", text_style=final_style),
                ]
            )
        ]
    )

    stream = normalize_tree(body)

    assert len(stream.items) == 4
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "A"
    assert isinstance(stream.items[1], EquationUnit)
    assert isinstance(stream.items[2], TextUnit)
    assert stream.items[2].content == "B"
    assert stream.items[2].text_style is final_style
    assert isinstance(stream.items[3], ParagraphBoundary)
    assert stream.items[3].text_style is final_style


def test_normalize_tree_normalizes_kitchen_sink_body_in_document_order() -> None:
    bullet = Bullet(list_id="list-kitchen")
    table = Table(
        table_key="table-kitchen",
        rows=[
            TableRow(
                row_key="row-kitchen",
                cells=[
                    TableCell(
                        cell_key="cell-kitchen",
                        content=[Paragraph(elements=[TextRun(content="T\n")])],
                    )
                ],
            )
        ],
    )
    body = Body(
        content=[
            Paragraph(
                elements=[TextRun(content="Go\n")],
                bullet=bullet,
            ),
            table,
            Paragraph(
                elements=[TextRun(content="X"), Equation(), TextRun(content="\n")]
            ),
        ]
    )

    stream = normalize_tree(body)

    assert len(stream.items) == 7
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "G"
    assert isinstance(stream.items[1], TextUnit)
    assert stream.items[1].content == "o"
    assert isinstance(stream.items[2], ParagraphBoundary)
    assert stream.items[2].bullet is bullet
    assert isinstance(stream.items[3], TableUnit)
    assert stream.items[3].table_key == "table-kitchen"
    assert stream.items[3].rows[0].row_key == "row-kitchen"
    assert stream.items[3].rows[0].cells[0].cell_key == "cell-kitchen"
    assert isinstance(stream.items[3].rows[0].cells[0].content, ContentStream)
    assert len(stream.items[3].rows[0].cells[0].content.items) == 2
    assert isinstance(stream.items[3].rows[0].cells[0].content.items[0], TextUnit)
    assert stream.items[3].rows[0].cells[0].content.items[0].content == "T"
    assert isinstance(
        stream.items[3].rows[0].cells[0].content.items[1], ParagraphBoundary
    )
    assert isinstance(stream.items[4], TextUnit)
    assert stream.items[4].content == "X"
    assert isinstance(stream.items[5], EquationUnit)
    assert isinstance(stream.items[6], ParagraphBoundary)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run pytest tests/compiler/test_document.py -v
```

Expected: all four tests fail because `normalize_tree` raises `NotImplementedError` or keyed table constructor arguments are not yet accepted. Failures must be caused by missing normalization behavior, not import or syntax errors.

- [ ] **Step 3: Add optional opaque keys to table model nodes**

Update the constructors in `gdocs_patch/models/table.py` without changing their existing child attachment behavior:

```python
class TableCell(IndexedNode):
    def __init__(
        self,
        *,
        content: list[StructuralElement],
        style: TableCellStyle | UnsetType = UNSET,
        cell_key: str | None = None,
    ) -> None:
        super().__init__()
        for child in content:
            self.add_child(child)
        self.style = style
        self.cell_key = cell_key
```

```python
class TableRow(IndexedNode):
    def __init__(
        self,
        *,
        cells: list[TableCell],
        min_height: Dimension | UnsetType = UNSET,
        prevent_overflow: bool | UnsetType = UNSET,
        is_header: bool | UnsetType = UNSET,
        row_key: str | None = None,
    ) -> None:
        super().__init__()
        for child in cells:
            self.add_child(child)
        self.min_height = min_height
        self.prevent_overflow = prevent_overflow
        self.is_header = is_header
        self.row_key = row_key
```

```python
class Table(StructuralElement):
    def __init__(
        self,
        *,
        rows: list[TableRow],
        column_styles: list[TableColumn] | UnsetType = UNSET,
        table_key: str | None = None,
    ) -> None:
        super().__init__()
        for child in rows:
            self.add_child(child)
        self.column_styles = column_styles
        self.table_key = table_key
```

- [ ] **Step 4: Implement the direct recursive normalization walk**

Replace the `normalize_tree` stub in `gdocs_patch/compiler/document.py`. Extend its imports to include the existing model and content-stream types used below. Do not introduce helper functions or another traversal API.

```python
from gdocs_patch.models import (
    UNSET,
    Body,
    Document,
    DocumentTab,
    Equation,
    Paragraph,
    Tab,
    Table,
    TableCellStyle,
    TextRun,
    TextStyle,
    TreeNode,
    UnsetType,
)

from .content_stream import (
    ContentStream,
    ContentUnit,
    EquationUnit,
    ParagraphBoundary,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
)
```

```python
def normalize_tree(tree: TreeNode) -> ContentStream:
    if isinstance(tree, TextRun):
        return ContentStream(
            items=[
                TextUnit(content=character, text_style=tree.text_style)
                for character in tree.content
            ]
        )

    if isinstance(tree, Equation):
        return ContentStream(items=[EquationUnit()])

    if isinstance(tree, Paragraph):
        items: list[ContentUnit] = []
        for child in tree.children:
            items.extend(normalize_tree(child).items)

        boundary_text_style: TextStyle | UnsetType = UNSET
        if (
            items
            and isinstance(items[-1], TextUnit)
            and items[-1].content == "\n"
        ):
            boundary_text_style = items.pop().text_style

        items.append(
            ParagraphBoundary(
                text_style=boundary_text_style,
                paragraph_style=tree.style,
                bullet=tree.bullet,
            )
        )
        return ContentStream(items=items)

    if isinstance(tree, Table):
        rows: list[TableRowUnit] = []
        for row in tree.rows:
            cells: list[TableCellUnit] = []
            for cell in row.cells:
                if isinstance(cell.style, TableCellStyle):
                    row_span = cell.style.row_span
                    column_span = cell.style.column_span
                else:
                    row_span = 1
                    column_span = 1
                cells.append(
                    TableCellUnit(
                        cell_key=cell.cell_key,
                        content=normalize_tree(cell),
                        row_span=row_span,
                        column_span=column_span,
                        style=cell.style,
                    )
                )
            rows.append(
                TableRowUnit(
                    row_key=row.row_key,
                    cells=cells,
                    min_height=row.min_height,
                    prevent_overflow=row.prevent_overflow,
                    is_header=row.is_header,
                )
            )
        return ContentStream(
            items=[
                TableUnit(
                    table_key=tree.table_key,
                    rows=rows,
                    column_properties=tree.column_styles,
                )
            ]
        )

    items: list[ContentUnit] = []
    for child in tree.children:
        items.extend(normalize_tree(child).items)
    return ContentStream(items=items)
```

Allow Ruff to reformat the multiline terminal-newline condition if needed. Keep the control flow and existing-tree traversal semantics unchanged.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```bash
uv run pytest tests/compiler/test_document.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Run the complete project checks**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: all tests and checks pass with no errors.

- [ ] **Step 7: Review and commit**

Confirm only the intended model, compiler, test, spec, and plan files are tracked on `feature-normalize-tree`, and confirm `main` still contains none of these changes. Then commit:

```bash
git add gdocs_patch/models/table.py gdocs_patch/compiler/document.py tests/compiler/test_document.py
git commit -m "feat: normalize document trees"
```
