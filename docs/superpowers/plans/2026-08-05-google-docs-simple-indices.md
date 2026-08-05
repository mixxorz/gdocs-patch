# Google Docs Simple Dynamic Indices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dynamic Google Docs UTF-16 indices to the existing simple content tree without custom collections, assignment interception, metadata fields, or cached state.

**Architecture:** `TreeNode` remains the complete tree implementation: public `parent`, public ordered `children`, `add_child()`, and adjacent sibling properties. A small `IndexedNode` subclass derives each position from its parent and previous sibling. Concrete semantic models define only their child origin and UTF-16 width.

**Tech Stack:** Python 3.12+, ordinary mutable classes, `uv`, Pytest, Ruff, Fixit, Pyright strict, pre-commit.

## Current implemented tree

The branch already contains and tests:

```python
class TreeNode(Model):
    __slots__ = ("parent",)

    def __init__(self) -> None:
        self.parent: TreeNode | None = None
        self.children: list[TreeNode] = []

    def add_child(self, child: TreeNode) -> None:
        child.parent = self
        self.children.append(child)

    @property
    def previous_sibling(self) -> TreeNode | None:
        if self.parent is None:
            return None
        previous = None
        for child in self.parent.children:
            if child is self:
                return previous
            previous = child
        return None

    @property
    def next_sibling(self) -> TreeNode | None:
        if self.parent is None:
            return None
        for index, child in enumerate(self.parent.children):
            if child is self and index + 1 < len(self.parent.children):
                return self.parent.children[index + 1]
        return None
```

The indexed content forest is:

```text
Body | Segment
└── StructuralElement
    ├── Paragraph
    │   └── ParagraphElement
    ├── Table
    │   └── TableRow
    │       └── TableCell
    │           └── StructuralElement
    ├── TableOfContents
    │   └── StructuralElement
    └── SectionBreak
```

Semantic collection properties are direct aliases of `children`:

- `Body.content`
- `Segment.content`
- `Paragraph.elements`
- `Table.rows`
- `TableRow.cells`
- `TableCell.content`
- `TableOfContents.content`

`Document`, `Tab`, `DocumentTab`, styles, lists, and references are not members of the indexed tree. Each `Body` and `Segment` is an independent root.

## Complexity guardrails

These requirements are binding:

- Do not add custom list, dictionary, descriptor, slot, registry, or ownership-container classes.
- Do not override `__setattr__`.
- Do not add `_tree_*` metadata, materialized paths, cached indices, cached widths, or invalidation logic.
- Do not intercept direct Python list mutation.
- Do not rename semantic constructor arguments or collection properties.
- Do not add general traversal, move, remove, detach, cycle detection, or ownership validation in this change.
- `add_child()` is the only operation that establishes a parent. Reordering already-attached children is allowed because their parent does not change.
- If the implementation appears to require another tree abstraction, stop and report rather than adding it.

## Index semantics

Only these classes have index properties:

- `StructuralElement` subclasses
- `ParagraphElement` subclasses
- `TableRow`
- `TableCell`

They expose:

```python
node.utf16_width
node.start_index
node.end_index
```

Each `Body`, header, footer, and footnote `Segment` begins at zero. Indices are absolute only within that root.

The first child starts at its parent's `children_start_index`. Every later child starts at its previous sibling's `end_index`. `end_index` is `start_index + utf16_width`. Accessing `start_index` or `end_index` on a detached indexed node raises `ValueError`; width remains available.

Child origins are:

```text
Body / Segment                 0
Paragraph                      paragraph.start_index
Table                          table.start_index + 1
TableRow                       row.start_index + 1
TableCell                      cell.start_index + 1
TableOfContents                table_of_contents.start_index + 1
```

Widths are:

```text
TextRun                        UTF-16 code units in content
Other ParagraphElement         1
Paragraph                      sum(element widths)
SectionBreak                   1
TableCell                      1 + sum(content widths)
TableRow                       1 + sum(cell widths)
Table                          2 + sum(row widths)
TableOfContents                1 + sum(content widths)
```

---

### Task 1: Indexed base, roots, paragraphs, and sections

**Files:**
- Modify: `gdocs_patch/models/base.py`
- Modify: `gdocs_patch/models/document.py`
- Modify: `gdocs_patch/models/paragraph.py`
- Modify: `gdocs_patch/models/section.py`
- Modify: `gdocs_patch/models/__init__.py`
- Create: `tests/models/test_indices.py`

**Produces:** `IndexedNode`, root/paragraph child origins, paragraph-element widths, paragraph widths, and section-break widths.

- [ ] **Step 1: Write failing root and UTF-16 behavior tests**

Create `tests/models/test_indices.py`:

```python
import pytest

from gdocs_patch.models.document import Body, Segment
from gdocs_patch.models.paragraph import Equation, Paragraph, TextRun
from gdocs_patch.models.section import SectionBreak, SectionStyle


def test_body_indices_follow_utf16_widths_and_current_sibling_order() -> None:
    section = SectionBreak(style=SectionStyle())
    first = TextRun(content="A🌍")
    second = Equation()
    paragraph = Paragraph(elements=[first, second])
    following = Paragraph(elements=[TextRun(content="Z")])
    body = Body(content=[section, paragraph, following])

    assert body.parent is None
    assert (section.start_index, section.end_index) == (0, 1)
    assert (paragraph.start_index, paragraph.end_index) == (1, 5)
    assert (first.start_index, first.end_index) == (1, 4)
    assert (second.start_index, second.end_index) == (4, 5)
    assert following.start_index == 5

    paragraph.elements.reverse()

    assert second.start_index == 1
    assert first.start_index == 2
    assert following.start_index == 5

    first.content = "A"

    assert paragraph.end_index == 3
    assert following.start_index == 3


def test_each_segment_is_an_independent_zero_based_root() -> None:
    paragraph = Paragraph(elements=[TextRun(content="Header")])
    segment = Segment(segment_id="header", content=[paragraph])

    assert segment.parent is None
    assert paragraph.start_index == 0
    assert paragraph.end_index == 6


def test_detached_node_has_width_but_no_indices() -> None:
    run = TextRun(content="🌍")

    assert run.utf16_width == 2
    with pytest.raises(ValueError, match="not attached"):
        _ = run.start_index
    with pytest.raises(ValueError, match="not attached"):
        _ = run.end_index
```

- [ ] **Step 2: Run the tests and confirm RED**

```bash
uv run pytest tests/models/test_indices.py -q
```

Expected: collection or attribute failures because `IndexedNode`, widths, and indices do not exist.

- [ ] **Step 3: Add the small explicit index API**

In `gdocs_patch/models/base.py`, add only this new base and one explicit parent-origin property to `TreeNode`:

```python
class TreeNode(Model):
    # Existing implementation remains unchanged.

    @property
    def children_start_index(self) -> int:
        raise ValueError(f"{type(self).__name__} does not define child indices")


class IndexedNode(TreeNode):
    @property
    def utf16_width(self) -> int:
        raise NotImplementedError

    @property
    def start_index(self) -> int:
        if self.parent is None:
            raise ValueError(f"{type(self).__name__} is not attached")
        previous = self.previous_sibling
        if previous is None:
            return self.parent.children_start_index
        return cast("IndexedNode", previous).end_index

    @property
    def end_index(self) -> int:
        return self.start_index + self.utf16_width
```

Import `cast` from `typing`. Re-export `IndexedNode` from `gdocs_patch.models`.

- [ ] **Step 4: Apply explicit root and paragraph behavior**

Use direct inheritance and properties; do not add metadata:

```python
class StructuralElement(IndexedNode):
    pass


class Body(TreeNode):
    @property
    def children_start_index(self) -> int:
        return 0


class Segment(TreeNode):
    @property
    def children_start_index(self) -> int:
        return 0


class ParagraphElement(IndexedNode):
    @property
    def utf16_width(self) -> int:
        return 1


class TextRun(ParagraphElement):
    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


class Paragraph(StructuralElement):
    @property
    def children_start_index(self) -> int:
        return self.start_index

    @property
    def utf16_width(self) -> int:
        return sum(element.utf16_width for element in self.elements)


class SectionBreak(StructuralElement):
    @property
    def utf16_width(self) -> int:
        return 1
```

All non-text paragraph elements inherit the one-unit width. Do not duplicate the property across their concrete classes.

- [ ] **Step 5: Run focused and full checks**

```bash
uv run pytest tests/models/test_indices.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add gdocs_patch/models tests/models/test_indices.py
git commit -m "feat: calculate paragraph content indices"
```

---

### Task 2: Tables and table-of-contents indices

**Files:**
- Modify: `gdocs_patch/models/document.py`
- Modify: `gdocs_patch/models/table.py`
- Modify: `tests/models/test_indices.py`

**Produces:** explicit table-family child origins and recursive widths.

- [ ] **Step 1: Add a failing nested table test**

Append:

```python
from gdocs_patch.models.document import TableOfContents
from gdocs_patch.models.table import Table, TableCell, TableRow


def test_table_boundaries_and_nested_content_are_derived_from_children() -> None:
    cell_paragraph = Paragraph(elements=[TextRun(content="x\n")])
    first_cell = TableCell(content=[cell_paragraph])
    second_cell = TableCell(content=[Paragraph(elements=[])])
    row = TableRow(cells=[first_cell, second_cell])
    table = Table(rows=[row])
    toc_paragraph = Paragraph(elements=[TextRun(content="T\n")])
    toc = TableOfContents(content=[toc_paragraph])
    following = Paragraph(elements=[TextRun(content="Z")])
    Body(content=[table, toc, following])

    assert (table.start_index, table.end_index) == (0, 7)
    assert (row.start_index, row.end_index) == (1, 6)
    assert (first_cell.start_index, first_cell.end_index) == (2, 5)
    assert cell_paragraph.start_index == 3
    assert (second_cell.start_index, second_cell.end_index) == (5, 6)
    assert (toc.start_index, toc.end_index) == (7, 10)
    assert toc_paragraph.start_index == 8
    assert following.start_index == 10
```

- [ ] **Step 2: Run and confirm RED**

```bash
uv run pytest tests/models/test_indices.py::test_table_boundaries_and_nested_content_are_derived_from_children -q
```

Expected: missing width/origin behavior.

- [ ] **Step 3: Implement explicit table behavior**

```python
class TableOfContents(StructuralElement):
    @property
    def children_start_index(self) -> int:
        return self.start_index + 1

    @property
    def utf16_width(self) -> int:
        return 1 + sum(element.utf16_width for element in self.content)


class TableCell(IndexedNode):
    @property
    def children_start_index(self) -> int:
        return self.start_index + 1

    @property
    def utf16_width(self) -> int:
        return 1 + sum(element.utf16_width for element in self.content)


class TableRow(IndexedNode):
    @property
    def children_start_index(self) -> int:
        return self.start_index + 1

    @property
    def utf16_width(self) -> int:
        return 1 + sum(cell.utf16_width for cell in self.cells)


class Table(StructuralElement):
    @property
    def children_start_index(self) -> int:
        return self.start_index + 1

    @property
    def utf16_width(self) -> int:
        return 2 + sum(row.utf16_width for row in self.rows)
```

Do not use spans, styles, column metadata, or API count fields in width calculations.

- [ ] **Step 4: Run verification and commit**

```bash
uv run pytest tests/models/test_indices.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run pyright
git add gdocs_patch/models/document.py gdocs_patch/models/table.py tests/models/test_indices.py
git commit -m "feat: calculate table content indices"
```

---

### Task 3: Maximal parser parity, documentation, and real-sample validation

**Files:**
- Modify: `tests/parsers/fixtures/maximal_document.json`
- Modify: `tests/parsers/test_document.py`
- Modify: `docs/superpowers/specs/2026-08-05-google-docs-native-model-design.md`

**Produces:** end-to-end evidence that parsers establish the simple parent tree and every supported retained index in the maximal document matches the calculated model index.

- [ ] **Step 1: Make the maximal fixture internally index-consistent**

Update all supported `startIndex` and `endIndex` values in `tests/parsers/fixtures/maximal_document.json` to these half-open ranges:

```text
body rich paragraph                    [0, 14)
  TextRun("Text")                      [0, 4)
  ten non-text paragraph elements      [4, 5) through [13, 14)
body section break                     [14, 15)
body table                             [15, 40)
  row                                  [16, 39)
    first cell                         [17, 38)
      Paragraph("Cell")                [18, 22)
      nested table                     [22, 37)
        nested row                     [23, 36)
          nested cell                  [24, 36)
            Paragraph("Nested cell")   [25, 36)
      nested table of contents         [37, 38)
        empty paragraph                [38, 38)
    second cell                        [38, 39)
      empty paragraph                  [39, 39)
body table of contents                 [40, 41)
  empty paragraph                      [41, 41)
header empty paragraph                 [0, 0)
footnote empty paragraph               [0, 0)
```

Add missing end values to these supported wrappers. Keep suggestion data and unsupported top-level legacy/range indices as ignored fixture data.

- [ ] **Step 2: Add a committed automated maximal-index test**

Add `test_maximal_document_indices_match_fixture()` to `tests/parsers/test_document.py`. This must be a normal committed Pytest test that runs in the full suite, not a one-off validation command.

The test loads `fixtures/maximal_document.json`, parses it with `document_parser`, and uses a test-local recursive comparison that walks the decoded fixture and parsed model in parallel.

It must compare every present supported `startIndex`, `endIndex`, and derived width on:

- structural-element wrappers;
- paragraph-element wrappers;
- table rows;
- table cells;
- recursively nested table-cell and table-of-contents content;
- body, header, footer, and footnote index spaces.

For every supported node, assert:

```python
assert node.start_index == raw["startIndex"]
assert node.end_index == raw["endIndex"]
assert node.utf16_width == raw["endIndex"] - raw["startIndex"]
```

The helper must return both the number of compared nodes and index values. The normalized maximal fixture contains 31 supported indexed nodes, each with both a start and end value, so assert:

```python
assert compared_nodes == 31
assert compared_index_values == 62
```

These exact assertions prevent a partial or accidentally empty traversal from passing. Do not compare unsupported top-level generic `range` data.

The same test must assert representative ownership:

```python
assert body.parent is None
assert body.content[0].parent is body
assert paragraph.elements[0].parent is paragraph
assert table.rows[0].parent is table
assert table.rows[0].cells[0].parent is table.rows[0]
assert table.rows[0].cells[0].content[0].parent is table.rows[0].cells[0]
```

This is behavior verification: the parser still discards provider indices, and the model independently recalculates values that must match them.

- [ ] **Step 3: Run maximal parser parity and full tests**

```bash
uv run pytest tests/parsers/test_document.py -q
uv run pytest -q
```

Expected: every retained maximal supported index matches and all tests pass without parser index context.

- [ ] **Step 4: Update current model documentation**

Update the native model design to state:

- `Body` is now an explicit root class.
- `Body` and each `Segment` are independent index roots.
- Indexed content uses the simple `TreeNode` API.
- Semantic collection properties alias `children`.
- Parent links are established only through constructors and `add_child()`.
- Direct collection mutation is not intercepted.
- Dynamic index formulas are the formulas in this plan.

Remove statements claiming tree traversal and index calculation are unimplemented. Do not document custom collections, mutation interception, metadata, paths, or caching.

- [ ] **Step 5: Validate the real sample**

Run a one-off script against the untracked `documents.get` sample. Recursively compare every present provider `startIndex` and `endIndex` for structural elements, paragraph elements, rows, and cells against the model properties. Whenever `endIndex` is present, also compare `utf16_width` with `endIndex - startIndex`, treating an omitted proto-default `startIndex` as zero. Do not copy or commit the sample.

Expected: nonzero comparisons and no assertion failures.

- [ ] **Step 6: Run all project checks**

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: all clean.

- [ ] **Step 7: Commit and request whole-branch review**

```bash
git add tests/parsers/fixtures/maximal_document.json \
  tests/parsers/test_document.py \
  docs/superpowers/specs/2026-08-05-google-docs-native-model-design.md
git commit -m "test: verify simple dynamic document indices"
```

The whole-branch reviewer must specifically confirm that the implementation contains no custom ownership collections, `__setattr__`, `_tree_*` metadata, path storage, or index caches.
