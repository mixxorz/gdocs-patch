# Google Docs Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse modern, already-decoded Google Docs API v1 `documents.get(includeTabsContent=true)` responses into the hand-written native model tree through `ModelClass.gdoc_parser.parse(...)`.

**Architecture:** Add an explicit stateless parser for each of the 41 concrete API-backed model classes, grouped in a semantic `gdocs_patch/parsers/` package. Containing parsers unwrap Google wrappers and dispatch tagged unions inline; concrete child parsers receive inner payloads and recursively construct the tree. Parsers validate consumed fields, ignore extras, normalize approved omissions, and report the first failure through a path-aware `GDocParseError`.

**Tech Stack:** Python 3.12+, ordinary hand-written classes, recursive decoded-JSON type aliases, Pytest, Ruff, Fixit, Pyright strict mode, pre-commit, and `uv` for all commands.

## Global Constraints

- Work only in `/Users/mixxorz/Projects/gdocs_patch/.worktrees/feature-google-docs-parser` on branch `feature-google-docs-parser`; never modify `main` or the original checkout.
- Follow `docs/superpowers/specs/2026-08-05-google-docs-parser-design.md` and the amended native-model spec.
- Do not add runtime dependencies or generated code.
- Do not use `from __future__ import annotations` or imports inside runtime function/class bodies; repository Fixit codemods reject both.
- Keep models and parsers ordinary, mutable/explicit, hand-written, keyword-only where they have constructor fields, and fully typed under Pyright strict mode.
- Every concrete parser is a shared stateless instance attached as `Class.gdoc_parser`; do not add a registry, descriptor, metaclass, reflection-based constructor, abstract-union parser, parse context, parent pointer, traversal API, or index state.
- Input is a decoded `JsonValue`; do not decode text, read files, or mutate caller input.
- Required consumed fields must exist and have valid types/literals; optional absence maps to `UNSET`; unknown fields are ignored; empty intrinsic collections normalize to `[]`.
- Ignore every `startIndex` and `endIndex`, suggestions, legacy top-level tab content, derived table counts, named ranges, and object resource maps.
- Tests assert input-to-model behavior only. Do not test singleton identity, parser delegation/call counts, annotations, or class/field existence.
- Each implementation task must run its focused tests plus Ruff and Pyright, verify `git branch --show-current` remains `feature-google-docs-parser`, and commit its work before review.

---

## File structure

### Production files

- Modify `gdocs_patch/__init__.py`: initialize the parser package; later semantic modules join initialization through `parsers.__init__`.
- Modify `gdocs_patch/models/base.py`: typed parser attributes for `Dimension` and `Color`.
- Modify `gdocs_patch/models/document.py`: remove `legacy_tab`; add typed parser attributes for six concrete document models.
- Modify `gdocs_patch/models/paragraph.py`: remove all offsets and add typed parser attributes for 22 concrete paragraph models.
- Modify `gdocs_patch/models/section.py`: add typed parser attributes for three concrete section models.
- Modify `gdocs_patch/models/table.py`: remove row/cell offsets and add typed parser attributes for six concrete table models.
- Modify `gdocs_patch/models/list.py`: add typed parser attributes for two concrete list models.
- Create `gdocs_patch/parsers/__init__.py`: public base exports and eager semantic-module initialization.
- Create `gdocs_patch/parsers/base.py`: JSON aliases, parser base, parse exception, validation/path helpers, optional-color normalization, `DimensionParser`, and `ColorParser`.
- Create `gdocs_patch/parsers/paragraph.py`: links, styles, paragraph elements, paragraph, and named-style parsers.
- Create `gdocs_patch/parsers/section.py`: section parsers.
- Create `gdocs_patch/parsers/table.py`: table parsers.
- Create `gdocs_patch/parsers/list.py`: list parsers.
- Create `gdocs_patch/parsers/document.py`: document hierarchy, segment, TOC, and structural dispatch.

### Test files

- Create `tests/parsers/test_base.py`
- Create `tests/parsers/test_paragraph.py`
- Create `tests/parsers/test_section.py`
- Create `tests/parsers/test_table.py`
- Create `tests/parsers/test_list.py`
- Create `tests/parsers/test_document.py`
- Create `tests/parsers/fixtures/maximal_document.json`
- Create `tests/parsers/maximal_document.py`: manually constructs the complete expected model for the maximal fixture.

---

### Task 1: Align models and build parser foundations

**Files:**
- Modify: `gdocs_patch/__init__.py`
- Modify: `gdocs_patch/models/base.py`
- Modify: `gdocs_patch/models/document.py`
- Modify: `gdocs_patch/models/paragraph.py`
- Modify: `gdocs_patch/models/section.py`
- Modify: `gdocs_patch/models/table.py`
- Modify: `gdocs_patch/models/list.py`
- Create: `gdocs_patch/parsers/base.py`
- Create: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_base.py`

**Interfaces:**
- Produces: `JsonValue`, `JsonObject`, `GDocParser[T]`, `GDocParseError`, validation/path helpers, `parse_optional_color`, `DimensionParser`, and `ColorParser`.
- Produces: typed `ClassVar[GDocParser[ConcreteClass]]` declarations on all 41 concrete API-backed models, allowing later parser modules to reference child parser attributes under strict typing.
- Produces: offset-free paragraph/table models, modern-only `Document`, and root-package initialization of every parser module currently exposed by `parsers.__init__`.

- [ ] **Step 1: Write failing public parser tests**

Create tests that use the model-facing API, not helper internals:

```python
import pytest

from gdocs_patch.models import Color, Dimension
from gdocs_patch.parsers import GDocParseError


def test_dimension_parser_normalizes_proto_defaults() -> None:
    assert Dimension.gdoc_parser.parse({}) == Dimension()
    assert Dimension.gdoc_parser.parse(
        {"magnitude": 12, "unit": "PT", "ignored": True}
    ) == Dimension(magnitude=12.0, unit="PT")


def test_color_parser_absorbs_rgb_color() -> None:
    assert Color.gdoc_parser.parse(
        {"rgbColor": {"red": 0.25, "green": 0.5, "blue": 1}}
    ) == Color(red=0.25, green=0.5, blue=1.0)


def test_constructor_error_is_wrapped_and_chained() -> None:
    with pytest.raises(GDocParseError) as caught:
        Color.gdoc_parser.parse({"rgbColor": {"red": 2}})

    assert isinstance(caught.value.__cause__, ValueError)
```

- [ ] **Step 2: Run the tests and verify the missing parser API failure**

Run: `uv run pytest tests/parsers/test_base.py -v`

Expected: collection or execution fails because `gdocs_patch.parsers` and `gdoc_parser` do not exist.

- [ ] **Step 3: Revise model shapes and declare parser attributes**

Apply these exact model changes:

```text
Document.__init__: delete legacy_tab parameter and assignment
ParagraphElement: delete its offset constructor entirely
All 11 ParagraphElement subclasses: delete start_offset/end_offset parameters,
  delete super().__init__(...) offset calls, retain only real payload/style fields
TableRow: delete start_offset/end_offset parameters and assignments
TableCell: delete start_offset/end_offset parameters and assignments
```

For every concrete API-backed model, add a type-only `GDocParser` import and a class variable matching this pattern:

```python
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from gdocs_patch.parsers.base import GDocParser


class Dimension(Model):
    gdoc_parser: ClassVar["GDocParser[Dimension]"]
```

Declare this attribute on exactly the 41 classes enumerated in the parser design. Do not declare it on `Model`, `UnsetType`, `StructuralElement`, `ParagraphElement`, or `Link`.

- [ ] **Step 4: Implement the parser foundation and base-value parsers**

`gdocs_patch/parsers/base.py` must expose these exact responsibilities and signatures:

```python
from abc import ABC, abstractmethod
from typing import Literal

from gdocs_patch.models.base import UNSET, Color, Dimension, UnsetType


type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type JsonObject = dict[str, JsonValue]


class GDocParseError(ValueError):
    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


class GDocParser[T](ABC):
    @abstractmethod
    def parse(self, data: JsonValue, *, path: str = "$") -> T:
        raise NotImplementedError
```

Implement typed helpers for these operations, always raising `GDocParseError(path, ...)`:

```text
object_value(value, path) -> JsonObject
array_value(value, path) -> list[JsonValue]
string_value(value, path) -> str
boolean_value(value, path) -> bool
integer_value(value, path) -> int       # reject bool
number_value(value, path) -> float      # accept int/float, reject bool
literal_value(value, allowed, path) -> allowed literal type
required_field(object, key, path) -> JsonValue
optional_string/object/array/boolean/integer/literal field helpers -> value | UNSET
field_path(parent, key) -> "{parent}.{key}"
index_path(parent, index) -> "{parent}[{index}]"
map_key_path(parent, key) -> an unambiguous bracketed path
parse_optional_color(value, path) -> Color | None
```

`parse_optional_color` validates an `OptionalColor` object, returns `None` for `{}`, and otherwise calls `Color.gdoc_parser.parse(value["color"], path=field_path(path, "color"))`.

Implement and attach:

```text
DimensionParser: object; magnitude defaults to 0; unit defaults to
  UNIT_UNSPECIFIED; allowed units are UNIT_UNSPECIFIED and PT.
ColorParser: object; rgbColor defaults to {}; red/green/blue each default to 0;
  call Color and wrap its ValueError as GDocParseError at the Color path.
```

`gdocs_patch/parsers/__init__.py` initially re-exports only the base public API and imports `base` so these first two attachments occur. Initialize parsers from `gdocs_patch/__init__.py` with the top-level side-effect import `from . import parsers as _parsers`. As later tasks add semantic imports to `parsers.__init__`, every fresh process initializes the newly available attachments automatically.

- [ ] **Step 5: Run focused and regression checks**

Run:

```bash
uv run pytest tests/parsers/test_base.py tests/models -v
uv run ruff check gdocs_patch tests
uv run ruff format --check gdocs_patch tests
uv run pyright
```

Expected: all commands pass; existing suite remains at least 21 passing tests plus the new base parser tests.

- [ ] **Step 6: Verify branch isolation and commit**

```bash
test "$(git branch --show-current)" = "feature-google-docs-parser"
git status --short
git add gdocs_patch/__init__.py gdocs_patch/models gdocs_patch/parsers tests/parsers/test_base.py
git commit -m "Add Google Docs parser foundations"
```

---

### Task 2: Parse links and paragraph presentation models

**Files:**
- Create: `gdocs_patch/parsers/paragraph.py`
- Modify: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_paragraph.py`

**Interfaces:**
- Consumes: all Task 1 JSON validators, path helpers, `parse_optional_color`, and parser class attributes.
- Produces: parsers for `UrlLink`, `TabLink`, `BookmarkLink`, `HeadingLink`, `TextStyle`, `Bullet`, `ParagraphBorder`, `TabStop`, and `ParagraphStyle`.
- Leaves the same file ready for Task 3 to add paragraph element, paragraph, and named-style parsers.

- [ ] **Step 1: Write nine direct happy-path cases**

Use a parameterized public-API test table with one case per parser. Include these payload/expected behaviors:

```text
UrlLink: "https://example.test" -> UrlLink(url=...)
TabLink: "tab-2" -> TabLink(tab_id="tab-2")
BookmarkLink: {"id": "bookmark-1", "tabId": "tab-2"} -> both fields
HeadingLink: {"id": "heading-1", "tabId": "tab-2"} -> both fields
TextStyle: all booleans, baselineOffset, fontSize, weightedFontFamily,
  foregroundColor, transparent backgroundColor, and one URL link
Bullet: listId, omitted nestingLevel -> 0, nested textStyle
ParagraphBorder: opaque color, width, padding, dashStyle
TabStop: offset and alignment
ParagraphStyle: every constructor field, including five borders, shading,
  all dimensions, literals, booleans, headingId, and two tabStops
```

The parameterized assertion is:

```python
@pytest.mark.parametrize(("parser", "payload", "expected"), CASES)
def test_parses_paragraph_presentation_model(parser, payload, expected) -> None:
    assert parser.parse(payload) == expected
```

Add one separate link test showing deprecated `{"bookmarkId": "legacy"}` at the `TextStyle.link` boundary normalizes to `BookmarkLink(bookmark_id="legacy")`.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `uv run pytest tests/parsers/test_paragraph.py -v`

Expected: FAIL because paragraph parsers are not attached.

- [ ] **Step 3: Implement exact link and style mappings**

Implement direct parsers and attach each singleton. The mapping is:

```text
UrlLinkParser: scalar string -> url
TabLinkParser: scalar string -> tab_id
BookmarkLinkParser: object id(required), tabId(optional) -> bookmark_id, tab_id
HeadingLinkParser: object id(required), tabId(optional) -> heading_id, tab_id

TextStyleParser:
  bold/italic/underline/strikethrough/smallCaps -> optional bool
  baselineOffset -> optional approved literal
  fontSize -> DimensionParser
  weightedFontFamily.fontFamily -> font_family (optional independently)
  weightedFontFamily.weight -> font_weight (optional independently)
  foregroundColor/backgroundColor -> parse_optional_color
  link -> inline exact-one dispatch:
    url scalar -> UrlLinkParser
    tabId scalar -> TabLinkParser
    bookmark object -> BookmarkLinkParser
    heading object -> HeadingLinkParser
    bookmarkId scalar -> BookmarkLink(bookmark_id=value, tab_id=UNSET)
    headingId scalar -> HeadingLink(heading_id=value, tab_id=UNSET)

BulletParser:
  listId required; nestingLevel defaults 0; textStyle optional

ParagraphBorderParser:
  color, width, padding, dashStyle all required

TabStopParser:
  offset and alignment required

ParagraphStyleParser:
  direct camelCase fields map to constructor snake_case fields
  direction -> direction
  all dimension fields -> DimensionParser
  borderBetween/Top/Bottom/Left/Right -> ParagraphBorderParser
  shading.backgroundColor -> parse_optional_color as shading_color
  tabStops -> list[TabStopParser]
```

Each link wrapper must contain exactly one supported target. Parsers ignore suggestion and extra keys. Present malformed optional fields raise at their field paths.

- [ ] **Step 4: Run focused and static checks**

```bash
uv run pytest tests/parsers/test_base.py tests/parsers/test_paragraph.py -v
uv run ruff check gdocs_patch/parsers/paragraph.py tests/parsers/test_paragraph.py
uv run ruff format --check gdocs_patch/parsers/paragraph.py tests/parsers/test_paragraph.py
uv run pyright
```

Expected: all pass.

- [ ] **Step 5: Verify branch and commit**

```bash
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch/parsers tests/parsers/test_paragraph.py
git commit -m "Parse Google Docs paragraph styles"
```

---

### Task 3: Parse paragraph elements, paragraphs, and named styles

**Files:**
- Modify: `gdocs_patch/parsers/paragraph.py`
- Modify: `tests/parsers/test_paragraph.py`

**Interfaces:**
- Consumes: Task 2 `TextStyleParser`, `ParagraphStyleParser`, and `BulletParser` through model class attributes.
- Produces: the remaining 13 paragraph-module parsers: eleven element variants, `ParagraphParser`, and `NamedStyleParser`.

- [ ] **Step 1: Add 13 happy-path cases and one union contract test**

Add one direct successful case for each parser:

```text
TextRun: content + textStyle
AutoText: type + textStyle
ColumnBreak: textStyle
DateElement: dateId + every dateElementProperties field + textStyle
Equation: empty object containing ignored suggestion IDs
FootnoteReference: footnoteId + footnoteNumber + textStyle
HorizontalRule: textStyle
InlineObjectReference: inlineObjectId + textStyle
PageBreak: textStyle
PersonReference: personId + all personProperties + textStyle
RichLink: richLinkId + all richLinkProperties + textStyle
Paragraph: paragraphStyle + bullet + positionedObjectIds + all 11 element wrappers
NamedStyle: namedStyleType + textStyle + paragraphStyle
```

Every paragraph-element wrapper in the `ParagraphParser` case includes `startIndex`, `endIndex`, and an ignored suggestion field, proving those extras do not enter the expected model.

Add one parameterized union-contract test covering both invalid cardinalities:

```python
@pytest.mark.parametrize(
    "element",
    [
        {},
        {"textRun": {"content": "x"}, "equation": {}},
    ],
)
def test_paragraph_element_requires_exactly_one_supported_variant(element) -> None:
    with pytest.raises(
        GDocParseError,
        match="exactly one supported paragraph element",
    ):
        Paragraph.gdoc_parser.parse({"elements": [element]})
```

- [ ] **Step 2: Run and verify the new cases fail**

Run: `uv run pytest tests/parsers/test_paragraph.py -v`

Expected: the new cases fail because the 13 parsers are not attached.

- [ ] **Step 3: Implement the remaining paragraph mappings**

Attach parsers with these exact mappings:

```text
TextRunParser: content required; textStyle optional
AutoTextParser: type required; textStyle optional
ColumnBreakParser: textStyle optional
DateElementParser: dateId required; dateElementProperties optional wrapper;
  its dateFormat/displayText/locale/timeFormat/timeZoneId/timestamp fields
  independently become values or UNSET; textStyle optional
EquationParser: validate object, ignore all fields, return Equation()
FootnoteReferenceParser: footnoteId and footnoteNumber required; textStyle optional
HorizontalRuleParser: textStyle optional
InlineObjectReferenceParser: inlineObjectId required; textStyle optional
PageBreakParser: textStyle optional
PersonReferenceParser: personId required; personProperties optional wrapper;
  email/name independently optional; textStyle optional
RichLinkParser: richLinkId required; richLinkProperties required because uri is
  required; uri required, title/mimeType optional; textStyle optional
ParagraphParser:
  elements missing -> []
  paragraphStyle -> ParagraphStyleParser or UNSET
  bullet -> BulletParser or UNSET
  positionedObjectIds -> validated list[str] or UNSET
  for every element wrapper count supported keys and invoke exactly one of:
    textRun, autoText, columnBreak, dateElement, equation, footnoteReference,
    horizontalRule, inlineObjectElement, pageBreak, person, richLink
NamedStyleParser: namedStyleType required approved literal; textStyle and
  paragraphStyle optional
```

Do not read or pass index fields. Parent dispatch passes only the inner variant value and extends the path through the variant key.

- [ ] **Step 4: Run module and project checks**

```bash
uv run pytest tests/parsers/test_paragraph.py tests/models -v
uv run ruff check gdocs_patch tests
uv run ruff format --check gdocs_patch tests
uv run pyright
```

Expected: all pass.

- [ ] **Step 5: Verify branch and commit**

```bash
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch/parsers/paragraph.py tests/parsers/test_paragraph.py
git commit -m "Parse Google Docs paragraphs"
```

---

### Task 4: Parse section models

**Files:**
- Create: `gdocs_patch/parsers/section.py`
- Modify: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_section.py`

**Interfaces:**
- Consumes: `Dimension.gdoc_parser` and Task 1 validators.
- Produces: `SectionColumnParser`, `SectionStyleParser`, and `SectionBreakParser`.

- [ ] **Step 1: Write three direct happy-path tests**

Use payloads that cover:

```text
SectionColumn: required width and paddingEnd dimensions
SectionStyle: two columnProperties; all three literals; every header/footer ID;
  booleans; pageNumberStart; and all six margin dimensions
SectionBreak: required sectionStyle plus ignored start/end/suggestion fields
```

Assert exact equality with `SectionColumn`, `SectionStyle`, and `SectionBreak` model instances.

- [ ] **Step 2: Run and verify failure**

Run: `uv run pytest tests/parsers/test_section.py -v`

Expected: FAIL because section parsers are unattached.

- [ ] **Step 3: Implement section parsers**

```text
SectionColumnParser:
  width -> required DimensionParser
  paddingEnd -> required DimensionParser
SectionStyleParser:
  columnProperties -> list[SectionColumnParser] or UNSET
  direct optional literal/string/bool/int fields map to constructor names
  marginTop/Bottom/Left/Right/Header/Footer -> optional DimensionParser
SectionBreakParser:
  sectionStyle -> required SectionStyleParser
```

Ignore suggestion/index extras and attach all three stateless instances.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/parsers/test_section.py -v
uv run ruff check gdocs_patch/parsers/section.py tests/parsers/test_section.py
uv run ruff format --check gdocs_patch/parsers/section.py tests/parsers/test_section.py
uv run pyright
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch/parsers tests/parsers/test_section.py
git commit -m "Parse Google Docs sections"
```

---

### Task 5: Parse table models and recursive cell content

**Files:**
- Create: `gdocs_patch/parsers/table.py`
- Modify: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_table.py`

**Interfaces:**
- Consumes: value/style parsers and typed concrete structural parser attributes.
- Produces: `TableCellBorderParser`, `TableCellStyleParser`, `TableCellParser`, `TableRowParser`, `TableColumnParser`, and `TableParser`.

- [ ] **Step 1: Write six direct happy-path cases**

Cover these observable mappings:

```text
TableCellBorder: color, width, dashStyle
TableCellStyle: spans, transparent background, four distinct borders,
  four padding dimensions, contentAlignment
TableCell: nested paragraph structural wrapper + tableCellStyle; index extras ignored
TableRow: two cells + complete tableRowStyle; index extras ignored
TableColumn: FIXED_WIDTH + width
Table: tableRows + tableStyle.tableColumnProperties; numeric rows/columns ignored
```

The nested paragraph proves `TableCellParser` recursively produces a `Paragraph`; do not mock its parser.

- [ ] **Step 2: Run and verify failure**

Run: `uv run pytest tests/parsers/test_table.py -v`

Expected: FAIL because table parsers are unattached.

- [ ] **Step 3: Implement all table mappings**

```text
TableCellBorderParser:
  color -> required OptionalColor normalization
  width -> required DimensionParser
  dashStyle -> required approved literal
TableCellStyleParser:
  rowSpan/columnSpan default 1
  backgroundColor optional
  borderLeft/Right/Top/Bottom -> optional TableCellBorderParser
  paddingLeft/Right/Top/Bottom -> optional DimensionParser
  contentAlignment -> optional approved literal
  wrap TableCellStyle invariant ValueError at this object path
TableCellParser:
  content missing -> []
  inline exact-one structural dispatch for paragraph/sectionBreak/table/
    tableOfContents
  tableCellStyle -> TableCellStyleParser or UNSET
TableRowParser:
  tableCells missing -> []
  tableRowStyle optional; absorb minRowHeight/preventOverflow/tableHeader
TableColumnParser:
  widthType required; width optional; wrap constructor invariant ValueError
TableParser:
  tableRows missing -> []
  tableStyle absent -> column_styles=UNSET
  tableStyle present -> tableColumnProperties missing becomes []
  ignore rows and columns
```

Attach all six parsers. Duplicate structural dispatch inline; do not add a structural helper/parser.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/parsers/test_table.py tests/parsers/test_paragraph.py -v
uv run ruff check gdocs_patch/parsers/table.py tests/parsers/test_table.py
uv run ruff format --check gdocs_patch/parsers/table.py tests/parsers/test_table.py
uv run pyright
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch/parsers tests/parsers/test_table.py
git commit -m "Parse Google Docs tables"
```

---

### Task 6: Parse list models

**Files:**
- Create: `gdocs_patch/parsers/list.py`
- Modify: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_list.py`

**Interfaces:**
- Consumes: `Dimension.gdoc_parser`, `TextStyle.gdoc_parser`, validators, and path helpers.
- Produces: `ListLevelParser` and `ListDefinitionParser`.

- [ ] **Step 1: Write two direct happy-path cases**

```text
ListLevel: glyphFormat, glyphSymbol, omitted bulletAlignment/startNumber defaults,
  indentFirstLine, indentStart, and textStyle
ListDefinition: listProperties.nestingLevels containing one glyphSymbol level and
  one glyphType level, plus ignored suggestion fields
```

Assert complete equality with expected list models.

- [ ] **Step 2: Run and verify failure**

Run: `uv run pytest tests/parsers/test_list.py -v`

Expected: FAIL because list parsers are unattached.

- [ ] **Step 3: Implement list mappings**

```text
ListLevelParser:
  glyphFormat required string
  glyphType and glyphSymbol independently optional, then model invariant enforces
    exactly one
  bulletAlignment defaults BULLET_ALIGNMENT_UNSPECIFIED
  indentFirstLine/indentStart optional DimensionParser
  startNumber defaults 0
  textStyle optional TextStyleParser
  wrap ListLevel invariant ValueError at the level path
ListDefinitionParser:
  validate object
  listProperties absent -> levels=[]
  listProperties present and nestingLevels absent -> levels=[]
  parse each nesting level through ListLevelParser
```

Attach both parsers.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/parsers/test_list.py tests/models/test_list.py -v
uv run ruff check gdocs_patch/parsers/list.py tests/parsers/test_list.py
uv run ruff format --check gdocs_patch/parsers/list.py tests/parsers/test_list.py
uv run pyright
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch/parsers tests/parsers/test_list.py
git commit -m "Parse Google Docs lists"
```

---

### Task 7: Parse the document hierarchy and maximal integration fixture

**Files:**
- Create: `gdocs_patch/parsers/document.py`
- Modify: `gdocs_patch/parsers/__init__.py`
- Create: `tests/parsers/test_document.py`
- Create: `tests/parsers/fixtures/maximal_document.json`
- Create: `tests/parsers/maximal_document.py`

**Interfaces:**
- Consumes: every parser from Tasks 1–6.
- Produces: `DocumentParser`, `TabParser`, `DocumentTabParser`, `DocumentStyleParser`, `SegmentParser`, and `TableOfContentsParser`.
- Produces: eager package initialization and complete end-to-end parsing through `Document.gdoc_parser.parse`.

- [ ] **Step 1: Create six direct happy paths**

Add one direct case for each document parser:

```text
DocumentStyle: background, documentFormat.documentMode, pageSize height/width,
  all margins, IDs, booleans, flipPageOrientation, and pageNumberStart
Segment: one headerId plus paragraph content; content omission is also represented
  elsewhere by the maximal fixture
TableOfContents: paragraph and table content wrappers
DocumentTab: body, one entry in each resource map, documentStyle, namedStyles,
  and lists
Tab: complete tabProperties, documentTab, and one recursive childTab
Document: documentId, title, revisionId, suggestionsViewMode, and tabs
```

Expected values must be manually constructed model trees. The `Document` payload also contains unsupported top-level legacy fields and confirms they are ignored.

Add the single nested path-propagation test by changing a minimal otherwise-valid document's tab index to a string and asserting:

```python
with pytest.raises(
    GDocParseError,
    match=r"^\$\.tabs\[0\]\.tabProperties\.index: expected integer$",
):
    Document.gdoc_parser.parse(
        {
            "documentId": "doc-1",
            "title": "Example",
            "tabs": [
                {
                    "tabProperties": {
                        "tabId": "tab-1",
                        "title": "Main",
                        "index": "zero",
                    }
                }
            ],
        }
    )
```

- [ ] **Step 2: Build the maximal generic fixture and expected model**

Create static JSON at `tests/parsers/fixtures/maximal_document.json` with generic IDs/text only. It must include at least once:

```text
Document: every supported field and ignored top-level legacy/object/range field
Tabs: two root/child levels; every Tab property; present and absent documentTab
DocumentTab: body, headers, footers, footnotes, documentStyle, namedStyles, lists
Structural wrappers: paragraph, sectionBreak, table, tableOfContents
Paragraph: every field and all 11 paragraph element variants
TextStyle: every field; distribute all six link JSON forms across text styles
Date/person/rich-link property wrappers: every modeled property
ParagraphStyle: every field, five borders, shading, and tab stops
SectionStyle: every field and at least two columns
Table: row and cell styles, fixed/even columns, nested paragraph in a cell,
  and nested structural content sufficient to exercise recursion
Lists: one glyphSymbol level and one glyphType level
OptionalColor: at least one opaque value and one transparent {}
Defaults: omitted Dimension members, nesting levels, cell spans, and list defaults
Ignored data: indices at every structural/paragraph/table depth, suggestion fields,
  table rows/columns, namedRanges, inlineObjects, and positionedObjects
```

Create `tests/parsers/maximal_document.py` with one `expected_maximal_document() -> Document` function that manually constructs every expected node. Do not derive expected values by calling parsers or by reading the fixture.

Add an integration test:

```python
import json
from pathlib import Path

from gdocs_patch.models import Document
from tests.parsers.maximal_document import expected_maximal_document


def test_parses_maximal_document_response() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "maximal_document.json"
    decoded = json.loads(fixture_path.read_text())

    assert Document.gdoc_parser.parse(decoded) == expected_maximal_document()
```

- [ ] **Step 3: Run and verify document/integration failures**

Run: `uv run pytest tests/parsers/test_document.py -v`

Expected: FAIL because document parsers and root eager initialization do not exist.

- [ ] **Step 4: Implement document hierarchy parsers**

Implement these exact mappings:

```text
DocumentStyleParser:
  background.color -> optional-color normalization as background_color
  documentFormat.documentMode -> document_mode
  pageSize.width/pageSize.height -> page_width/page_height
  six direct margin fields -> DimensionParser
  direct ID/bool/int fields -> corresponding snake_case constructor fields

SegmentParser:
  validate exactly one of headerId/footerId/footnoteId and use it as segment_id
  content missing -> []
  inline exact-one structural dispatch for every content wrapper

TableOfContentsParser:
  content missing -> []
  inline exact-one structural dispatch for every content wrapper

DocumentTabParser:
  body absent -> UNSET; present body content missing -> [] and inline structural dispatch
  headers/footers/footnotes absent -> UNSET; present maps preserve keys and call SegmentParser
  documentStyle -> DocumentStyleParser or UNSET
  namedStyles absent -> UNSET; present styles missing -> [] and call NamedStyleParser
  lists absent -> UNSET; present map preserves keys and calls ListDefinitionParser

TabParser:
  tabProperties required
  tabId/title/index required
  nestingLevel defaults 0
  parentTabId/iconEmoji optional
  documentTab optional -> DocumentTabParser or UNSET
  childTabs missing -> []; recursively call TabParser

DocumentParser:
  documentId/title/tabs required
  revisionId/suggestionsViewMode optional
  call TabParser for every tab
  ignore all top-level legacy and unsupported fields
```

All four structural-content owners (`DocumentTabParser`, `SegmentParser`, `TableCellParser`, and `TableOfContentsParser`) must visibly contain their own supported-key count and dispatch logic. Do not centralize it.

- [ ] **Step 5: Complete eager parser initialization**

Make `gdocs_patch/parsers/__init__.py` import every semantic parser module in a cycle-safe order and continue re-exporting the base public API. The root package side-effect import added in Task 1 then initializes all 41 parser attachments. Respect Fixit's top-level import rule.

After this step, each of these works in a fresh interpreter without explicitly importing `gdocs_patch.parsers`:

```python
from gdocs_patch.models import Document, Paragraph

Document.gdoc_parser.parse(...)
Paragraph.gdoc_parser.parse(...)
```

Do not add an identity test for the shared parser objects.

- [ ] **Step 6: Run focused, integration, and full checks**

```bash
uv run pytest tests/parsers/test_document.py -v
uv run pytest -v
uv run ruff check gdocs_patch tests
uv run ruff format --check gdocs_patch tests
uv run pyright
```

Expected: all parser happy paths, maximal integration, and existing model tests pass.

- [ ] **Step 7: Verify branch and commit**

```bash
test "$(git branch --show-current)" = "feature-google-docs-parser"
git add gdocs_patch tests/parsers
git commit -m "Parse complete Google Docs documents"
```

---

### Task 8: Final behavioral error coverage and verification

**Files:**
- Modify: the smallest relevant files under `tests/parsers/` only if the three approved representative error behaviors are not already covered.
- Modify: production parser files only for failures demonstrated by these tests or verification.

**Interfaces:**
- Consumes and verifies the complete public parser API.
- Produces no new parser or model API.

- [ ] **Step 1: Audit the three approved invalid-input behaviors**

Ensure the suite contains exactly representative coverage for:

```text
1. malformed nested consumed value reports its complete path
2. tagged wrapper with zero or multiple supported variants raises GDocParseError
3. model invariant ValueError is wrapped and chained as GDocParseError
```

Task 1 covers constructor wrapping and Task 3 covers both invalid union cardinalities. Task 7 must add one nested path-propagation assertion through `DocumentParser`, such as a string at `$.tabs[0].tabProperties.index`. Add nothing beyond a missing category; do not create a malformed-input matrix.

- [ ] **Step 2: Run the original sample as a one-off integration check**

The original untracked sample is in the main checkout and may be read but must not be modified or copied into Git:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

from gdocs_patch.models import Document

path = Path(
    "/Users/mixxorz/Projects/gdocs_patch/"
    "document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json"
)
document = Document.gdoc_parser.parse(json.loads(path.read_text()))
assert document.document_id
assert document.tabs
print(f"parsed {len(document.tabs)} root tab(s): {document.title!r}")
PY
```

Expected: exits zero and prints one parsed root tab for the current sample. If it fails, preserve the failing path, add the smallest synthetic regression to the appropriate semantic parser test, fix only the demonstrated mapping, and commit that focused correction.

- [ ] **Step 3: Run complete project verification**

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: every command exits zero. Note that the Fixit pre-commit hook may apply automatic fixes; if it changes files, inspect them and rerun the entire verification block.

- [ ] **Step 4: Verify repository isolation and clean state**

```bash
test "$(git branch --show-current)" = "feature-google-docs-parser"
git -C /Users/mixxorz/Projects/gdocs_patch status --short --branch
git status --short --branch
git log --oneline --decorate -10
```

Expected: the original checkout remains on `main` with only its pre-existing untracked sample; all parser work and commits are on `feature-google-docs-parser`.

- [ ] **Step 5: Commit any verification-driven corrections**

If Step 2 or Step 3 required tracked changes:

```bash
git add gdocs_patch tests docs
git commit -m "Finish Google Docs parser verification"
```

If no tracked files changed, do not create an empty commit.
