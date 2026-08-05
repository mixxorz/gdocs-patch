# Google Docs Native Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the approved mutable, typed Google Docs native data-model classes without implementing parsing, serialization, traversal, indexing, or API mutations.

**Architecture:** Implement ordinary hand-written classes in a semantic `gdocs_patch.models` package. A small base module owns shared object behavior, the `UNSET` sentinel, and cross-cutting values; document, paragraph, section, table, and list modules own complete semantic slices. Runtime tests cover only actual behavior and invariants, while Pyright checks the broad data-only class surface.

**Tech Stack:** Python 3.12, standard-library typing, pytest, Ruff, Pyright, uv.

## Global Constraints

- Use ordinary, hand-written mutable classes; do not use dataclasses, generated classes, Pydantic, attrs, or runtime class construction.
- Use explicit, fully typed, keyword-only constructors and idiomatic `snake_case` attributes.
- Use inline field-specific `Literal[...]` annotations; do not introduce global enums or literal aliases.
- Collection identity is not a public contract. Avoid defensive copies unless the model architecture requires rebuilding a collection.
- Require intrinsic collections; do not use mutable defaults or normalize collections through `None`.
- Use `UNSET` only where absence is meaningful; use approved proto defaults elsewhere.
- Use built-in `ValueError` for semantic invariant failures; do not duplicate Pyright with exhaustive runtime type checks.
- Keep parsing, serialization, traversal, dynamic index calculation, mutation generation, suggestion data, named ranges, and object resource maps out of scope.
- Do not add low-value tests that merely repeat constructor assignments or class declarations.

## File Structure

- Create `gdocs_patch/models/base.py`: `Model`, `UnsetType`, `UNSET`, `Dimension`, and `Color`.
- Create `gdocs_patch/models/document.py`: document structural base, table of contents, document style, and aggregate document/tab/segment classes.
- Create `gdocs_patch/models/paragraph.py`: paragraph, paragraph elements, links, text/paragraph styles, bullets, and named styles.
- Create `gdocs_patch/models/section.py`: section break and section style classes.
- Create `gdocs_patch/models/table.py`: table tree and table presentation classes.
- Create `gdocs_patch/models/list.py`: list definition and list-level classes.
- Create `gdocs_patch/models/__init__.py`: stable public re-export surface.
- Create focused behavioral tests under `tests/models/` only where runtime behavior exists.

---

### Task 1: Shared model behavior and values

**Files:**
- Create: `gdocs_patch/models/__init__.py`
- Create: `gdocs_patch/models/base.py`
- Create: `tests/models/test_base.py`

**Interfaces:**
- Produces: `Model`, `UnsetType`, `UNSET`, `Dimension`, and `Color` for every later model module.
- `Model` provides exact-class structural equality, readable representation, and unhashability.
- `Dimension(*, magnitude: float = 0, unit: Literal["UNIT_UNSPECIFIED", "PT"] = "UNIT_UNSPECIFIED")`.
- `Color(*, red: float = 0, green: float = 0, blue: float = 0)`.

- [ ] **Step 1: Write the failing behavioral tests**

Create `tests/models/test_base.py`:

```python
import pytest
from gdocs_patch.models.base import UNSET, Color, Dimension, UnsetType


def test_unset_is_a_singleton_with_readable_representation() -> None:
    assert UnsetType() is UNSET
    assert repr(UNSET) == "UNSET"


def test_models_compare_by_exact_class_and_attributes() -> None:
    assert Dimension(magnitude=12, unit="PT") == Dimension(
        magnitude=12,
        unit="PT",
    )
    assert Dimension(magnitude=12, unit="PT") != Dimension(
        magnitude=13,
        unit="PT",
    )
    assert Dimension() != Color()


def test_model_representation_and_unhashability() -> None:
    dimension = Dimension(magnitude=12, unit="PT")

    assert repr(dimension) == "Dimension(magnitude=12, unit='PT')"
    with pytest.raises(TypeError):
        hash(dimension)


def test_dimension_uses_proto_defaults() -> None:
    dimension = Dimension()

    assert dimension.magnitude == 0
    assert dimension.unit == "UNIT_UNSPECIFIED"


def test_color_uses_proto_defaults_and_accepts_boundaries() -> None:
    assert Color() == Color(red=0, green=0, blue=0)
    assert Color(red=0.0, green=0.5, blue=1.0) == Color(
        red=0.0,
        green=0.5,
        blue=1.0,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("red", -0.01),
        ("green", 1.01),
        ("blue", 2.0),
    ],
)
def test_color_rejects_components_outside_unit_interval(
    field: str,
    value: float,
) -> None:
    values = {"red": 0.0, "green": 0.0, "blue": 0.0}
    values[field] = value

    with pytest.raises(
        ValueError,
        match=rf"color {field} must be between 0.0 and 1.0",
    ):
        Color(**values)
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run:

```bash
uv run pytest tests/models/test_base.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'gdocs_patch.models'`.

- [ ] **Step 3: Implement the shared base module**

Create `gdocs_patch/models/base.py`:

```python
from __future__ import annotations

from typing import ClassVar, Literal


class Model:
    """Base behavior shared by mutable Google Docs model objects."""

    __hash__ = None

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and vars(self) == vars(other)

    def __repr__(self) -> str:
        fields = ", ".join(f"{name}={value!r}" for name, value in vars(self).items())
        return f"{type(self).__name__}({fields})"


class UnsetType:
    """Sentinel type for provider fields that were not supplied."""

    _instance: ClassVar[UnsetType | None] = None

    def __new__(cls) -> UnsetType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"


UNSET = UnsetType()


class Dimension(Model):
    """A Google Docs measurement and its unit."""

    def __init__(
        self,
        *,
        magnitude: float = 0,
        unit: Literal["UNIT_UNSPECIFIED", "PT"] = "UNIT_UNSPECIFIED",
    ) -> None:
        self.magnitude = magnitude
        self.unit = unit


class Color(Model):
    """An opaque RGB color with components in the unit interval."""

    def __init__(
        self,
        *,
        red: float = 0,
        green: float = 0,
        blue: float = 0,
    ) -> None:
        components = {"red": red, "green": green, "blue": blue}
        for name, value in components.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"color {name} must be between 0.0 and 1.0")
        self.red = red
        self.green = green
        self.blue = blue
```

- [ ] **Step 4: Create the model package initializer**

Create `gdocs_patch/models/__init__.py`:

```python
"""Google Docs native model classes."""
```

- [ ] **Step 5: Run the focused tests**

Run:

```bash
uv run pytest tests/models/test_base.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run focused static and style checks**

Run:

```bash
uv run ruff check gdocs_patch/models/base.py tests/models/test_base.py
uv run ruff format --check gdocs_patch/models/base.py tests/models/test_base.py
uv run pyright gdocs_patch/models/base.py
```

Expected: all commands succeed with no errors.

- [ ] **Step 7: Commit the foundations**

```bash
git add gdocs_patch/models/__init__.py gdocs_patch/models/base.py tests/models/test_base.py
git commit -m "Add shared Google Docs model values"
```

---

### Task 2: Structural document and section models

**Files:**
- Create: `gdocs_patch/models/document.py`
- Create: `gdocs_patch/models/section.py`

**Interfaces:**
- Consumes: `Model`, `UNSET`, `UnsetType`, `Dimension`, and `Color` from Task 1.
- Produces: `StructuralElement`, `TableOfContents`, `DocumentStyle`, `SectionBreak`, `SectionStyle`, and `SectionColumn`.
- No runtime tests are added: these classes introduce typed data shape but no new runtime behavior.

- [ ] **Step 1: Implement document structural types and document style**

Create `gdocs_patch/models/document.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import UNSET, Color, Dimension, Model, UnsetType


class StructuralElement(Model):
    """Base for document structures whose absolute indices are derived."""


class TableOfContents(StructuralElement):
    def __init__(self, *, content: list[StructuralElement]) -> None:
        self.content = content


class DocumentStyle(Model):
    def __init__(
        self,
        *,
        background_color: Color | None | UnsetType = UNSET,
        document_mode: Literal[
            "DOCUMENT_MODE_UNSPECIFIED",
            "PAGES",
            "PAGELESS",
        ]
        | UnsetType = UNSET,
        page_width: Dimension | UnsetType = UNSET,
        page_height: Dimension | UnsetType = UNSET,
        margin_top: Dimension | UnsetType = UNSET,
        margin_bottom: Dimension | UnsetType = UNSET,
        margin_left: Dimension | UnsetType = UNSET,
        margin_right: Dimension | UnsetType = UNSET,
        margin_header: Dimension | UnsetType = UNSET,
        margin_footer: Dimension | UnsetType = UNSET,
        default_header_id: str | UnsetType = UNSET,
        default_footer_id: str | UnsetType = UNSET,
        even_page_header_id: str | UnsetType = UNSET,
        even_page_footer_id: str | UnsetType = UNSET,
        first_page_header_id: str | UnsetType = UNSET,
        first_page_footer_id: str | UnsetType = UNSET,
        use_even_page_header_footer: bool | UnsetType = UNSET,
        use_first_page_header_footer: bool | UnsetType = UNSET,
        use_custom_header_footer_margins: bool | UnsetType = UNSET,
        flip_page_orientation: bool | UnsetType = UNSET,
        page_number_start: int | UnsetType = UNSET,
    ) -> None:
        self.background_color = background_color
        self.document_mode = document_mode
        self.page_width = page_width
        self.page_height = page_height
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_header = margin_header
        self.margin_footer = margin_footer
        self.default_header_id = default_header_id
        self.default_footer_id = default_footer_id
        self.even_page_header_id = even_page_header_id
        self.even_page_footer_id = even_page_footer_id
        self.first_page_header_id = first_page_header_id
        self.first_page_footer_id = first_page_footer_id
        self.use_even_page_header_footer = use_even_page_header_footer
        self.use_first_page_header_footer = use_first_page_header_footer
        self.use_custom_header_footer_margins = use_custom_header_footer_margins
        self.flip_page_orientation = flip_page_orientation
        self.page_number_start = page_number_start
```

- [ ] **Step 2: Implement the section semantic slice**

Create `gdocs_patch/models/section.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import UNSET, Dimension, Model, UnsetType
from .document import StructuralElement


class SectionColumn(Model):
    def __init__(
        self,
        *,
        width: Dimension,
        padding_end: Dimension,
    ) -> None:
        self.width = width
        self.padding_end = padding_end


class SectionStyle(Model):
    def __init__(
        self,
        *,
        columns: list[SectionColumn] | UnsetType = UNSET,
        column_separator_style: Literal[
            "COLUMN_SEPARATOR_STYLE_UNSPECIFIED",
            "NONE",
            "BETWEEN_EACH_COLUMN",
        ]
        | UnsetType = UNSET,
        content_direction: Literal[
            "CONTENT_DIRECTION_UNSPECIFIED",
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
        ]
        | UnsetType = UNSET,
        section_type: Literal[
            "SECTION_TYPE_UNSPECIFIED",
            "CONTINUOUS",
            "NEXT_PAGE",
        ]
        | UnsetType = UNSET,
        default_header_id: str | UnsetType = UNSET,
        default_footer_id: str | UnsetType = UNSET,
        even_page_header_id: str | UnsetType = UNSET,
        even_page_footer_id: str | UnsetType = UNSET,
        first_page_header_id: str | UnsetType = UNSET,
        first_page_footer_id: str | UnsetType = UNSET,
        use_first_page_header_footer: bool | UnsetType = UNSET,
        flip_page_orientation: bool | UnsetType = UNSET,
        page_number_start: int | UnsetType = UNSET,
        margin_top: Dimension | UnsetType = UNSET,
        margin_bottom: Dimension | UnsetType = UNSET,
        margin_left: Dimension | UnsetType = UNSET,
        margin_right: Dimension | UnsetType = UNSET,
        margin_header: Dimension | UnsetType = UNSET,
        margin_footer: Dimension | UnsetType = UNSET,
    ) -> None:
        self.columns = columns
        self.column_separator_style = column_separator_style
        self.content_direction = content_direction
        self.section_type = section_type
        self.default_header_id = default_header_id
        self.default_footer_id = default_footer_id
        self.even_page_header_id = even_page_header_id
        self.even_page_footer_id = even_page_footer_id
        self.first_page_header_id = first_page_header_id
        self.first_page_footer_id = first_page_footer_id
        self.use_first_page_header_footer = use_first_page_header_footer
        self.flip_page_orientation = flip_page_orientation
        self.page_number_start = page_number_start
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_header = margin_header
        self.margin_footer = margin_footer


class SectionBreak(StructuralElement):
    def __init__(self, *, style: SectionStyle) -> None:
        self.style = style
```

- [ ] **Step 3: Run static and style verification**

Run:

```bash
uv run ruff check gdocs_patch/models/document.py gdocs_patch/models/section.py
uv run ruff format --check gdocs_patch/models/document.py gdocs_patch/models/section.py
uv run pyright gdocs_patch/models/base.py gdocs_patch/models/document.py gdocs_patch/models/section.py
```

Expected: all commands succeed with no errors.

- [ ] **Step 4: Commit the structural document slice**

```bash
git add gdocs_patch/models/document.py gdocs_patch/models/section.py
git commit -m "Add document structure and section models"
```

---

### Task 3: Paragraph, inline element, and style models

**Files:**
- Create: `gdocs_patch/models/paragraph.py`
- Create: `tests/models/test_paragraph.py`

**Interfaces:**
- Consumes: shared values from Task 1 and `StructuralElement` from Task 2.
- Produces: `Paragraph`, `Bullet`, `ParagraphStyle`, `ParagraphBorder`, `TabStop`, `ParagraphElement`, all eleven paragraph-element variants, `TextStyle`, the `Link` hierarchy, and `NamedStyle`.
- Paragraph-element offsets are relative and may be `UNSET`; structural elements store no absolute indices.

- [ ] **Step 1: Write the failing paragraph behavior tests**

Create `tests/models/test_paragraph.py`:

```python
from gdocs_patch.models.paragraph import Bullet, Paragraph


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_accepts_supplied_elements() -> None:
    elements = []

    paragraph = Paragraph(elements=elements)

    assert paragraph.elements == elements
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run:

```bash
uv run pytest tests/models/test_paragraph.py -v
```

Expected: collection fails with `ModuleNotFoundError` for `gdocs_patch.models.paragraph`.

- [ ] **Step 3: Implement paragraph values, styles, links, and elements**

Create `gdocs_patch/models/paragraph.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import UNSET, Color, Dimension, Model, UnsetType
from .document import StructuralElement


class Link(Model):
    """Base for mutually exclusive text-link targets."""


class UrlLink(Link):
    def __init__(self, *, url: str) -> None:
        self.url = url


class TabLink(Link):
    def __init__(self, *, tab_id: str) -> None:
        self.tab_id = tab_id


class BookmarkLink(Link):
    def __init__(
        self,
        *,
        bookmark_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.bookmark_id = bookmark_id
        self.tab_id = tab_id


class HeadingLink(Link):
    def __init__(
        self,
        *,
        heading_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.heading_id = heading_id
        self.tab_id = tab_id


class TextStyle(Model):
    def __init__(
        self,
        *,
        bold: bool | UnsetType = UNSET,
        italic: bool | UnsetType = UNSET,
        underline: bool | UnsetType = UNSET,
        strikethrough: bool | UnsetType = UNSET,
        small_caps: bool | UnsetType = UNSET,
        baseline_offset: Literal[
            "BASELINE_OFFSET_UNSPECIFIED",
            "NONE",
            "SUPERSCRIPT",
            "SUBSCRIPT",
        ]
        | UnsetType = UNSET,
        font_size: Dimension | UnsetType = UNSET,
        font_family: str | UnsetType = UNSET,
        font_weight: int | UnsetType = UNSET,
        foreground_color: Color | None | UnsetType = UNSET,
        background_color: Color | None | UnsetType = UNSET,
        link: Link | UnsetType = UNSET,
    ) -> None:
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strikethrough = strikethrough
        self.small_caps = small_caps
        self.baseline_offset = baseline_offset
        self.font_size = font_size
        self.font_family = font_family
        self.font_weight = font_weight
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.link = link


class Bullet(Model):
    def __init__(
        self,
        *,
        list_id: str,
        nesting_level: int = 0,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.list_id = list_id
        self.nesting_level = nesting_level
        self.text_style = text_style


class ParagraphBorder(Model):
    def __init__(
        self,
        *,
        color: Color | None,
        width: Dimension,
        padding: Dimension,
        dash_style: Literal[
            "DASH_STYLE_UNSPECIFIED",
            "SOLID",
            "DOT",
            "DASH",
        ],
    ) -> None:
        self.color = color
        self.width = width
        self.padding = padding
        self.dash_style = dash_style


class TabStop(Model):
    def __init__(
        self,
        *,
        offset: Dimension,
        alignment: Literal[
            "TAB_STOP_ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
        ],
    ) -> None:
        self.offset = offset
        self.alignment = alignment


class ParagraphStyle(Model):
    def __init__(
        self,
        *,
        named_style_type: Literal[
            "NAMED_STYLE_TYPE_UNSPECIFIED",
            "NORMAL_TEXT",
            "TITLE",
            "SUBTITLE",
            "HEADING_1",
            "HEADING_2",
            "HEADING_3",
            "HEADING_4",
            "HEADING_5",
            "HEADING_6",
        ]
        | UnsetType = UNSET,
        alignment: Literal[
            "ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
            "JUSTIFIED",
        ]
        | UnsetType = UNSET,
        direction: Literal[
            "CONTENT_DIRECTION_UNSPECIFIED",
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
        ]
        | UnsetType = UNSET,
        line_spacing: float | UnsetType = UNSET,
        spacing_mode: Literal[
            "SPACING_MODE_UNSPECIFIED",
            "NEVER_COLLAPSE",
            "COLLAPSE_LISTS",
        ]
        | UnsetType = UNSET,
        space_above: Dimension | UnsetType = UNSET,
        space_below: Dimension | UnsetType = UNSET,
        indent_first_line: Dimension | UnsetType = UNSET,
        indent_start: Dimension | UnsetType = UNSET,
        indent_end: Dimension | UnsetType = UNSET,
        keep_lines_together: bool | UnsetType = UNSET,
        keep_with_next: bool | UnsetType = UNSET,
        avoid_widow_and_orphan: bool | UnsetType = UNSET,
        page_break_before: bool | UnsetType = UNSET,
        heading_id: str | UnsetType = UNSET,
        border_between: ParagraphBorder | UnsetType = UNSET,
        border_top: ParagraphBorder | UnsetType = UNSET,
        border_bottom: ParagraphBorder | UnsetType = UNSET,
        border_left: ParagraphBorder | UnsetType = UNSET,
        border_right: ParagraphBorder | UnsetType = UNSET,
        shading_color: Color | None | UnsetType = UNSET,
        tab_stops: list[TabStop] | UnsetType = UNSET,
    ) -> None:
        self.named_style_type = named_style_type
        self.alignment = alignment
        self.direction = direction
        self.line_spacing = line_spacing
        self.spacing_mode = spacing_mode
        self.space_above = space_above
        self.space_below = space_below
        self.indent_first_line = indent_first_line
        self.indent_start = indent_start
        self.indent_end = indent_end
        self.keep_lines_together = keep_lines_together
        self.keep_with_next = keep_with_next
        self.avoid_widow_and_orphan = avoid_widow_and_orphan
        self.page_break_before = page_break_before
        self.heading_id = heading_id
        self.border_between = border_between
        self.border_top = border_top
        self.border_bottom = border_bottom
        self.border_left = border_left
        self.border_right = border_right
        self.shading_color = shading_color
        self.tab_stops = tab_stops


class ParagraphElement(Model):
    def __init__(
        self,
        *,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
    ) -> None:
        self.start_offset = start_offset
        self.end_offset = end_offset


class TextRun(ParagraphElement):
    def __init__(
        self,
        *,
        content: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.content = content
        self.text_style = text_style


class AutoText(ParagraphElement):
    def __init__(
        self,
        *,
        auto_text_type: Literal[
            "TYPE_UNSPECIFIED",
            "PAGE_NUMBER",
            "PAGE_COUNT",
        ],
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.auto_text_type = auto_text_type
        self.text_style = text_style


class ColumnBreak(ParagraphElement):
    def __init__(
        self,
        *,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.text_style = text_style


class DateElement(ParagraphElement):
    def __init__(
        self,
        *,
        date_id: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        date_format: Literal[
            "DATE_FORMAT_UNSPECIFIED",
            "DATE_FORMAT_CUSTOM",
            "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
            "DATE_FORMAT_MONTH_DAY_FULL",
            "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
            "DATE_FORMAT_ISO8601",
        ]
        | UnsetType = UNSET,
        display_text: str | UnsetType = UNSET,
        locale: str | UnsetType = UNSET,
        time_format: Literal[
            "TIME_FORMAT_UNSPECIFIED",
            "TIME_FORMAT_DISABLED",
            "TIME_FORMAT_HOUR_MINUTE",
            "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
        ]
        | UnsetType = UNSET,
        time_zone_id: str | UnsetType = UNSET,
        timestamp: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.date_id = date_id
        self.date_format = date_format
        self.display_text = display_text
        self.locale = locale
        self.time_format = time_format
        self.time_zone_id = time_zone_id
        self.timestamp = timestamp
        self.text_style = text_style


class Equation(ParagraphElement):
    def __init__(
        self,
        *,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)


class FootnoteReference(ParagraphElement):
    def __init__(
        self,
        *,
        footnote_id: str,
        footnote_number: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.footnote_id = footnote_id
        self.footnote_number = footnote_number
        self.text_style = text_style


class HorizontalRule(ParagraphElement):
    def __init__(
        self,
        *,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.text_style = text_style


class InlineObjectReference(ParagraphElement):
    def __init__(
        self,
        *,
        inline_object_id: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.inline_object_id = inline_object_id
        self.text_style = text_style


class PageBreak(ParagraphElement):
    def __init__(
        self,
        *,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.text_style = text_style


class PersonReference(ParagraphElement):
    def __init__(
        self,
        *,
        person_id: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        email: str | UnsetType = UNSET,
        name: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.person_id = person_id
        self.email = email
        self.name = name
        self.text_style = text_style


class RichLink(ParagraphElement):
    def __init__(
        self,
        *,
        rich_link_id: str,
        uri: str,
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        title: str | UnsetType = UNSET,
        mime_type: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__(start_offset=start_offset, end_offset=end_offset)
        self.rich_link_id = rich_link_id
        self.uri = uri
        self.title = title
        self.mime_type = mime_type
        self.text_style = text_style


class Paragraph(StructuralElement):
    def __init__(
        self,
        *,
        elements: list[ParagraphElement],
        style: ParagraphStyle | UnsetType = UNSET,
        bullet: Bullet | UnsetType = UNSET,
        positioned_object_ids: list[str] | UnsetType = UNSET,
    ) -> None:
        self.elements = elements
        self.style = style
        self.bullet = bullet
        self.positioned_object_ids = positioned_object_ids


class NamedStyle(Model):
    def __init__(
        self,
        *,
        named_style_type: Literal[
            "NAMED_STYLE_TYPE_UNSPECIFIED",
            "NORMAL_TEXT",
            "TITLE",
            "SUBTITLE",
            "HEADING_1",
            "HEADING_2",
            "HEADING_3",
            "HEADING_4",
            "HEADING_5",
            "HEADING_6",
        ],
        text_style: TextStyle | UnsetType = UNSET,
        paragraph_style: ParagraphStyle | UnsetType = UNSET,
    ) -> None:
        self.named_style_type = named_style_type
        self.text_style = text_style
        self.paragraph_style = paragraph_style
```

- [ ] **Step 4: Run the focused paragraph tests**

Run:

```bash
uv run pytest tests/models/test_paragraph.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Run static and style checks**

Run:

```bash
uv run ruff check gdocs_patch/models/paragraph.py tests/models/test_paragraph.py
uv run ruff format --check gdocs_patch/models/paragraph.py tests/models/test_paragraph.py
uv run pyright gdocs_patch/models/base.py gdocs_patch/models/document.py gdocs_patch/models/paragraph.py
```

Expected: all commands succeed with no errors.

- [ ] **Step 6: Commit the paragraph slice**

```bash
git add gdocs_patch/models/paragraph.py tests/models/test_paragraph.py
git commit -m "Add paragraph and inline content models"
```

---

### Task 4: Table models and invariants

**Files:**
- Create: `gdocs_patch/models/table.py`
- Create: `tests/models/test_table.py`

**Interfaces:**
- Consumes: shared values from Task 1 and `StructuralElement` from Task 2.
- Produces: `Table`, `TableRow`, `TableCell`, `TableCellStyle`, `TableCellBorder`, and `TableColumn`.
- Table row/cell offsets are relative to their containing `Table`; `Table` stores no absolute indices or stored row/column counts.

- [ ] **Step 1: Write the failing table invariant tests**

Create `tests/models/test_table.py`:

```python
import pytest
from gdocs_patch.models.base import Dimension
from gdocs_patch.models.table import TableCellStyle, TableColumn


def test_table_cell_style_defaults_spans_to_one() -> None:
    style = TableCellStyle()

    assert style.row_span == 1
    assert style.column_span == 1


@pytest.mark.parametrize(
    ("row_span", "column_span", "message"),
    [
        (0, 1, "row_span must be positive"),
        (1, 0, "column_span must be positive"),
        (-1, 1, "row_span must be positive"),
    ],
)
def test_table_cell_style_rejects_non_positive_spans(
    row_span: int,
    column_span: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        TableCellStyle(row_span=row_span, column_span=column_span)


def test_fixed_width_table_column_requires_width() -> None:
    with pytest.raises(
        ValueError,
        match="width must be set when width_type is FIXED_WIDTH",
    ):
        TableColumn(width_type="FIXED_WIDTH")


def test_non_fixed_table_column_rejects_width() -> None:
    with pytest.raises(
        ValueError,
        match="width must be unset unless width_type is FIXED_WIDTH",
    ):
        TableColumn(
            width_type="EVENLY_DISTRIBUTED",
            width=Dimension(magnitude=72, unit="PT"),
        )


def test_valid_fixed_width_table_column() -> None:
    width = Dimension(magnitude=72, unit="PT")

    column = TableColumn(width_type="FIXED_WIDTH", width=width)

    assert column.width is width
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run:

```bash
uv run pytest tests/models/test_table.py -v
```

Expected: collection fails with `ModuleNotFoundError` for `gdocs_patch.models.table`.

- [ ] **Step 3: Implement the complete table semantic slice**

Create `gdocs_patch/models/table.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import UNSET, Color, Dimension, Model, UnsetType
from .document import StructuralElement


class TableCellBorder(Model):
    def __init__(
        self,
        *,
        color: Color | None,
        width: Dimension,
        dash_style: Literal[
            "DASH_STYLE_UNSPECIFIED",
            "SOLID",
            "DOT",
            "DASH",
        ],
    ) -> None:
        self.color = color
        self.width = width
        self.dash_style = dash_style


class TableCellStyle(Model):
    def __init__(
        self,
        *,
        row_span: int = 1,
        column_span: int = 1,
        background_color: Color | None | UnsetType = UNSET,
        border_left: TableCellBorder | UnsetType = UNSET,
        border_right: TableCellBorder | UnsetType = UNSET,
        border_top: TableCellBorder | UnsetType = UNSET,
        border_bottom: TableCellBorder | UnsetType = UNSET,
        padding_left: Dimension | UnsetType = UNSET,
        padding_right: Dimension | UnsetType = UNSET,
        padding_top: Dimension | UnsetType = UNSET,
        padding_bottom: Dimension | UnsetType = UNSET,
        content_alignment: Literal[
            "CONTENT_ALIGNMENT_UNSPECIFIED",
            "CONTENT_ALIGNMENT_UNSUPPORTED",
            "TOP",
            "MIDDLE",
            "BOTTOM",
        ]
        | UnsetType = UNSET,
    ) -> None:
        if row_span <= 0:
            raise ValueError("row_span must be positive")
        if column_span <= 0:
            raise ValueError("column_span must be positive")
        self.row_span = row_span
        self.column_span = column_span
        self.background_color = background_color
        self.border_left = border_left
        self.border_right = border_right
        self.border_top = border_top
        self.border_bottom = border_bottom
        self.padding_left = padding_left
        self.padding_right = padding_right
        self.padding_top = padding_top
        self.padding_bottom = padding_bottom
        self.content_alignment = content_alignment


class TableCell(Model):
    def __init__(
        self,
        *,
        content: list[StructuralElement],
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        style: TableCellStyle | UnsetType = UNSET,
    ) -> None:
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.content = content
        self.style = style


class TableRow(Model):
    def __init__(
        self,
        *,
        cells: list[TableCell],
        start_offset: int | UnsetType = UNSET,
        end_offset: int | UnsetType = UNSET,
        min_height: Dimension | UnsetType = UNSET,
        prevent_overflow: bool | UnsetType = UNSET,
        is_header: bool | UnsetType = UNSET,
    ) -> None:
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.cells = cells
        self.min_height = min_height
        self.prevent_overflow = prevent_overflow
        self.is_header = is_header


class TableColumn(Model):
    def __init__(
        self,
        *,
        width_type: Literal[
            "WIDTH_TYPE_UNSPECIFIED",
            "EVENLY_DISTRIBUTED",
            "FIXED_WIDTH",
        ],
        width: Dimension | UnsetType = UNSET,
    ) -> None:
        if width_type == "FIXED_WIDTH" and width is UNSET:
            raise ValueError("width must be set when width_type is FIXED_WIDTH")
        if width_type != "FIXED_WIDTH" and width is not UNSET:
            raise ValueError("width must be unset unless width_type is FIXED_WIDTH")
        self.width_type = width_type
        self.width = width


class Table(StructuralElement):
    def __init__(
        self,
        *,
        rows: list[TableRow],
        column_styles: list[TableColumn] | UnsetType = UNSET,
    ) -> None:
        self.rows = rows
        self.column_styles = column_styles
```

- [ ] **Step 4: Run focused table tests**

Run:

```bash
uv run pytest tests/models/test_table.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run static and style checks**

Run:

```bash
uv run ruff check gdocs_patch/models/table.py tests/models/test_table.py
uv run ruff format --check gdocs_patch/models/table.py tests/models/test_table.py
uv run pyright gdocs_patch/models/base.py gdocs_patch/models/document.py gdocs_patch/models/table.py
```

Expected: all commands succeed with no errors.

- [ ] **Step 6: Commit the table slice**

```bash
git add gdocs_patch/models/table.py tests/models/test_table.py
git commit -m "Add table models and invariants"
```

---

### Task 5: List models and glyph invariant

**Files:**
- Create: `gdocs_patch/models/list.py`
- Create: `tests/models/test_list.py`

**Interfaces:**
- Consumes: `Dimension` and `TextStyle`.
- Produces: `ListDefinition` and `ListLevel`.
- `ListLevel` permits exactly one of `glyph_type` and `glyph_symbol`.

- [ ] **Step 1: Write the failing list behavior tests**

Create `tests/models/test_list.py`:

```python
import pytest
from gdocs_patch.models.list import ListLevel


def test_list_level_accepts_a_symbol_glyph() -> None:
    level = ListLevel(glyph_format="%0", glyph_symbol="●")

    assert level.alignment == "BULLET_ALIGNMENT_UNSPECIFIED"
    assert level.start_number == 0


def test_list_level_accepts_a_numbered_glyph() -> None:
    level = ListLevel(glyph_format="%0.", glyph_type="DECIMAL")

    assert level.glyph_type == "DECIMAL"


def test_list_level_rejects_missing_glyph_representation() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one of glyph_type and glyph_symbol must be set",
    ):
        ListLevel(glyph_format="%0")


def test_list_level_rejects_both_glyph_representations() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one of glyph_type and glyph_symbol must be set",
    ):
        ListLevel(
            glyph_format="%0",
            glyph_type="DECIMAL",
            glyph_symbol="●",
        )
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run:

```bash
uv run pytest tests/models/test_list.py -v
```

Expected: collection fails with `ModuleNotFoundError` for `gdocs_patch.models.list`.

- [ ] **Step 3: Implement list models**

Create `gdocs_patch/models/list.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import UNSET, Dimension, Model, UnsetType
from .paragraph import TextStyle


class ListLevel(Model):
    def __init__(
        self,
        *,
        glyph_format: str,
        glyph_type: Literal[
            "GLYPH_TYPE_UNSPECIFIED",
            "NONE",
            "DECIMAL",
            "ZERO_DECIMAL",
            "UPPER_ALPHA",
            "ALPHA",
            "UPPER_ROMAN",
            "ROMAN",
        ]
        | UnsetType = UNSET,
        glyph_symbol: str | UnsetType = UNSET,
        alignment: Literal[
            "BULLET_ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
        ] = "BULLET_ALIGNMENT_UNSPECIFIED",
        indent_first_line: Dimension | UnsetType = UNSET,
        indent_start: Dimension | UnsetType = UNSET,
        start_number: int = 0,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        if (glyph_type is UNSET) == (glyph_symbol is UNSET):
            raise ValueError("exactly one of glyph_type and glyph_symbol must be set")
        self.glyph_format = glyph_format
        self.glyph_type = glyph_type
        self.glyph_symbol = glyph_symbol
        self.alignment = alignment
        self.indent_first_line = indent_first_line
        self.indent_start = indent_start
        self.start_number = start_number
        self.text_style = text_style


class ListDefinition(Model):
    def __init__(self, *, levels: list[ListLevel]) -> None:
        self.levels = levels
```

- [ ] **Step 4: Run focused list tests**

Run:

```bash
uv run pytest tests/models/test_list.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run static and style checks**

Run:

```bash
uv run ruff check gdocs_patch/models/list.py tests/models/test_list.py
uv run ruff format --check gdocs_patch/models/list.py tests/models/test_list.py
uv run pyright gdocs_patch/models
```

Expected: all commands succeed with no errors.

- [ ] **Step 6: Commit the list slice**

```bash
git add gdocs_patch/models/list.py tests/models/test_list.py
git commit -m "Add Google Docs list models"
```

---

### Task 6: Document aggregates and public model API

**Files:**
- Modify: `gdocs_patch/models/document.py`
- Modify: `gdocs_patch/models/__init__.py`

**Interfaces:**
- Consumes: every model class from Tasks 1–5.
- Produces: `Segment`, `DocumentTab`, `Tab`, and `Document`, plus the stable `gdocs_patch.models` re-export surface.
- No runtime tests are added because this task adds data-only aggregate definitions and imports; Pyright and the complete test suite verify integration.

- [ ] **Step 1: Add document aggregate imports and classes**

Replace `from typing import Literal` in `gdocs_patch/models/document.py` with:

```python
from typing import TYPE_CHECKING, Literal
```

Then add this guarded import block immediately after the `.base` import:

```python
if TYPE_CHECKING:
    from .list import ListDefinition
    from .paragraph import NamedStyle
```

- [ ] **Step 2: Add document aggregate classes**

Append these classes to `gdocs_patch/models/document.py`:

```python
class Segment(Model):
    def __init__(
        self,
        *,
        segment_id: str,
        content: list[StructuralElement],
    ) -> None:
        self.segment_id = segment_id
        self.content = content


class DocumentTab(Model):
    def __init__(
        self,
        *,
        body: list[StructuralElement] | UnsetType = UNSET,
        headers: dict[str, Segment] | UnsetType = UNSET,
        footers: dict[str, Segment] | UnsetType = UNSET,
        footnotes: dict[str, Segment] | UnsetType = UNSET,
        document_style: DocumentStyle | UnsetType = UNSET,
        named_styles: list[NamedStyle] | UnsetType = UNSET,
        lists: dict[str, ListDefinition] | UnsetType = UNSET,
    ) -> None:
        self.body = body
        self.headers = headers
        self.footers = footers
        self.footnotes = footnotes
        self.document_style = document_style
        self.named_styles = named_styles
        self.lists = lists


class Tab(Model):
    def __init__(
        self,
        *,
        tab_id: str,
        title: str,
        index: int,
        children: list[Tab],
        nesting_level: int = 0,
        parent_tab_id: str | UnsetType = UNSET,
        icon_emoji: str | UnsetType = UNSET,
        content: DocumentTab | UnsetType = UNSET,
    ) -> None:
        self.tab_id = tab_id
        self.title = title
        self.index = index
        self.nesting_level = nesting_level
        self.parent_tab_id = parent_tab_id
        self.icon_emoji = icon_emoji
        self.content = content
        self.children = children


class Document(Model):
    def __init__(
        self,
        *,
        document_id: str,
        title: str,
        tabs: list[Tab],
        revision_id: str | UnsetType = UNSET,
        suggestions_view_mode: Literal[
            "DEFAULT_FOR_CURRENT_ACCESS",
            "SUGGESTIONS_INLINE",
            "PREVIEW_SUGGESTIONS_ACCEPTED",
            "PREVIEW_WITHOUT_SUGGESTIONS",
        ]
        | UnsetType = UNSET,
        legacy_tab: DocumentTab | UnsetType = UNSET,
    ) -> None:
        self.document_id = document_id
        self.title = title
        self.revision_id = revision_id
        self.suggestions_view_mode = suggestions_view_mode
        self.tabs = tabs
        self.legacy_tab = legacy_tab
```

- [ ] **Step 3: Create the stable public re-export surface**

Replace the contents of `gdocs_patch/models/__init__.py` with:

```python
from .base import UNSET, Color, Dimension, Model, UnsetType
from .document import (
    Document,
    DocumentStyle,
    DocumentTab,
    Segment,
    StructuralElement,
    Tab,
    TableOfContents,
)
from .list import ListDefinition, ListLevel
from .paragraph import (
    AutoText,
    BookmarkLink,
    Bullet,
    ColumnBreak,
    DateElement,
    Equation,
    FootnoteReference,
    HeadingLink,
    HorizontalRule,
    InlineObjectReference,
    Link,
    NamedStyle,
    PageBreak,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
    PersonReference,
    RichLink,
    TabLink,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
)
from .section import SectionBreak, SectionColumn, SectionStyle
from .table import (
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableRow,
)

__all__ = [
    "UNSET",
    "AutoText",
    "BookmarkLink",
    "Bullet",
    "Color",
    "ColumnBreak",
    "DateElement",
    "Dimension",
    "Document",
    "DocumentStyle",
    "DocumentTab",
    "Equation",
    "FootnoteReference",
    "HeadingLink",
    "HorizontalRule",
    "InlineObjectReference",
    "Link",
    "ListDefinition",
    "ListLevel",
    "Model",
    "NamedStyle",
    "PageBreak",
    "Paragraph",
    "ParagraphBorder",
    "ParagraphElement",
    "ParagraphStyle",
    "PersonReference",
    "RichLink",
    "SectionBreak",
    "SectionColumn",
    "SectionStyle",
    "Segment",
    "StructuralElement",
    "Tab",
    "TabLink",
    "TabStop",
    "Table",
    "TableCell",
    "TableCellBorder",
    "TableCellStyle",
    "TableColumn",
    "TableOfContents",
    "TableRow",
    "TextRun",
    "TextStyle",
    "UnsetType",
    "UrlLink",
]
```

- [ ] **Step 4: Run full verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Expected: all tests pass and all static/style checks exit successfully.

- [ ] **Step 5: Confirm scope boundaries in the implementation**

Run:

```bash
rg -n "from_dict|to_dict|from_json|to_json|start_index|end_index|suggested_|named_ranges|inline_objects|positioned_objects" gdocs_patch/models
```

Expected: no matches. `start_offset` and `end_offset` are expected and are not included in this search.

- [ ] **Step 6: Commit the integrated public model package**

```bash
git add gdocs_patch/models
git commit -m "Expose Google Docs native model package"
```
