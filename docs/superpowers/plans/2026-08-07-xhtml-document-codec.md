# XHTML Document Codec Implementation Plan

> **Status:** Implemented. Its imperative internal architecture is superseded by `2026-08-08-declarative-xhtml-rewrite.md`; the public behavior and syntax requirements remain authoritative.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic XML/XHTML serializer and deserializer for every currently modeled `Document` field.

**Architecture:** Add a private `_Encoder` that explicitly walks the existing model tree and a private `_Decoder` that explicitly walks XML elements. Shared XML, scalar, color, and text-style rules live in `base.py`; section and list grouping are the only sibling-sequence projections. The public surface remains two functions and one parse exception.

**Tech Stack:** Python 3.12+, standard-library `xml.etree.ElementTree`, `uv`, pytest, Ruff, Fixit, Pyright, pre-commit.

## Global Constraints

- Before implementation, use the `using-git-worktrees` skill to create an isolated feature worktree and branch based on `design/xhtml-document-codec`; do not implement on `main`.
- Follow test-driven development: write each behavioral test first, run it, and confirm the expected failure before production changes.
- Treat `docs/xhtml-syntax.md` as the normative grammar and `docs/superpowers/specs/2026-08-07-xhtml-document-codec-design.md` as the architecture specification.
- Keep the public API exactly `serialize_document(document: Document) -> str`, `deserialize_document(xhtml: str) -> Document`, and `XHTMLParseError` under `gdocs_patch.xhtml`.
- Use only the standard library. Do not add `lxml`, schema packages, an XML AST model, reflection, class-name dispatch, generic object serialization, or CSS.
- Keep `_Encoder` and `_Decoder` private. Use explicit type and qualified-tag matching.
- Preserve model constructors, mutability, keyword-only APIs, parent-link behavior, `UNSET`, explicit `False`, transparent `None`, and provider defaults except for the approved normalizations.
- Normalize every `Dimension` to a point magnitude and deserialize with `unit="PT"`; normalize empty `TextStyle`, empty `ParagraphStyle`, and default-only `TableCellStyle` to `UNSET`.
- Serialize and deserialize `DocumentTab.lists`, `ListDefinition`, and `ListLevel`; do not exclude them from equality assertions.
- Add or remove no paragraph-terminal newline. Every modeled newline serializes as `<br />`; literal line feeds inside spans are accepted as content.
- Permit metadata children in any position during deserialization, reject duplicate singular metadata, and preserve the relative order of actual content and repeated entries.
- CLI commands, files, Google API calls, compiler invocation, compiler changes, source-backed target merging, and request optimization are out of scope.
- Do not modify or commit `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json`.
- Commit each completed task. Write SDD reports under the implementation worktree's `.superpowers/sdd/` directory.

## File Structure

```text
gdocs_patch/xhtml/
├── __init__.py   # public exports only
├── base.py       # namespaces, XHTMLParseError, scalar/color/style/XML helpers
├── encoder.py    # private _Encoder model-tree visitor and serialize_document
└── decoder.py    # private _Decoder XML visitor and deserialize_document

tests/xhtml/
├── __init__.py
├── test_document.py
├── test_paragraph.py
├── test_structures.py
├── test_validation.py
└── test_round_trip.py
```

---

### Task 1: Public API, XML primitives, and document/tab envelope

**Files:**
- Create: `gdocs_patch/xhtml/__init__.py`
- Create: `gdocs_patch/xhtml/base.py`
- Create: `gdocs_patch/xhtml/encoder.py`
- Create: `gdocs_patch/xhtml/decoder.py`
- Create: `tests/xhtml/__init__.py`
- Create: `tests/xhtml/test_document.py`

**Interfaces:**
- Produces: `serialize_document(document: Document) -> str`.
- Produces: `deserialize_document(xhtml: str) -> Document`.
- Produces: `XHTMLParseError(ValueError)`.
- Produces private helpers `xhtml_name()`, `gdocs_name()`, strict scalar parsers, attribute validation, metadata extraction, and `_indent_xml()`.
- Later tasks extend `_Encoder.encode_document_tab()`, `_Encoder.encode_structural_sequence()`, `_Decoder.decode_document_tab()`, and `_Decoder.decode_structural_sequence()`.

- [ ] **Step 1: Write the minimal envelope round-trip test**

Create `tests/xhtml/test_document.py` with a document containing root metadata, one root tab, one child tab, no `DocumentTab` content, and no `UNSET` ambiguity:

```python
from gdocs_patch.models import Document, Tab
from gdocs_patch.xhtml import deserialize_document, serialize_document


def test_serializes_and_deserializes_document_and_tab_envelope() -> None:
    document = Document(
        document_id="doc-1",
        title="Example & Report",
        revision_id="revision-1",
        suggestions_view_mode="SUGGESTIONS_INLINE",
        tabs=[
            Tab(
                tab_id="tab-root",
                title="Root",
                index=0,
                nesting_level=0,
                icon_emoji="📄",
                children=[
                    Tab(
                        tab_id="tab-child",
                        title="Child",
                        index=1,
                        nesting_level=1,
                        parent_tab_id="tab-root",
                        children=[],
                    )
                ],
            )
        ],
    )

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Example &amp; Report" g:revision-id="revision-1" '
        'g:suggestions-view-mode="SUGGESTIONS_INLINE">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-root" g:title="Root" g:index="0" '
        'g:icon-emoji="📄">\n'
        "      <g:child-tabs>\n"
        '        <g:tab g:tab-id="tab-child" g:title="Child" g:index="1" '
        'g:nesting-level="1" g:parent-tab-id="tab-root" />\n'
        "      </g:child-tabs>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert deserialize_document(xhtml) == document
```

- [ ] **Step 2: Write focused envelope validation tests**

Add tests that call `deserialize_document()` with malformed XML, a wrong `gdocs` namespace, and a duplicate `<body>`. Each must raise `XHTMLParseError`; assert useful substrings such as `"XML"`, `"namespace"`, and `"body"` rather than an entire message.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_document.py -v
```

Expected: collection fails because `gdocs_patch.xhtml` does not exist.

- [ ] **Step 4: Implement namespace, scalar, validation, and formatting helpers**

In `base.py`, define these exact constants and public exception:

```python
from xml.etree import ElementTree

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
GDOCS_NAMESPACE = "urn:gdocs-patch:xhtml:1"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'


class XHTMLParseError(ValueError):
    pass


def xhtml_name(local_name: str) -> str:
    return f"{{{XHTML_NAMESPACE}}}{local_name}"


def gdocs_name(local_name: str) -> str:
    return f"{{{GDOCS_NAMESPACE}}}{local_name}"
```

Add explicit helpers for required/optional strings, booleans, integers, floats, allowed constants, unknown-attribute rejection, one-child extraction, whitespace validation, and path-qualified errors. Use `ElementTree.register_namespace("", XHTML_NAMESPACE)` and `register_namespace("g", GDOCS_NAMESPACE)` before output.

Implement `_indent_xml(element, level=0)` recursively. It must add two-space indentation to structural and metadata elements but return immediately for XHTML `<span>` so it never changes mixed text or `<br />` tails.

- [ ] **Step 5: Implement the minimal private encoder and decoder**

In `encoder.py`, implement `_Encoder.encode_document()`, `_Encoder.encode_tab()`, and canonical attribute insertion. Reject a set `Tab.content` until Task 2 handles it. `serialize_document()` must prepend `XML_DECLARATION`, serialize Unicode XML, and end with one newline.

In `decoder.py`, require the XML declaration, parse with `ElementTree.fromstring()`, validate the root and exact namespaces, extract exactly one body independent of position, decode recursive tabs and child-tab wrappers, and reject unknown children/attributes. Missing optional values become `UNSET`; omitted nesting level becomes `0`; omitted child tabs become `[]`.

Wire public exports in `__init__.py`:

```python
from .base import XHTMLParseError
from .decoder import deserialize_document
from .encoder import serialize_document

__all__ = ["XHTMLParseError", "deserialize_document", "serialize_document"]
```

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_document.py -v
uv run pytest -q
```

Expected: focused tests pass and the 100 baseline tests remain passing.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml
git commit -m "feat: add XHTML document envelope codec"
```

---

### Task 2: Bodies, sections, segments, paragraphs, runs, and text styles

**Files:**
- Modify: `gdocs_patch/xhtml/base.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_document.py`
- Create: `tests/xhtml/test_paragraph.py`

**Interfaces:**
- Extends `_Encoder` and `_Decoder` with `DocumentTab`, body sections, headers, footers, footnotes, basic paragraphs, and `TextRun`.
- Produces shared `encode_text_style(element, style)` and `decode_text_style(element, link, path)` behavior for every later style-bearing element.
- Produces `_Encoder.encode_structural_sequence(nodes, body=False)` and `_Decoder.decode_structural_sequence(elements, body=False)`.

- [ ] **Step 1: Write the body/segment and metadata-placement tests**

Add a test document containing:

- a `DocumentTab` whose `Body.content` begins with `SectionBreak(style=SectionStyle())`;
- one body paragraph using `ParagraphStyle(named_style_type="NORMAL_TEXT")`;
- one header dictionary whose map key differs from `Segment.segment_id`;
- empty footer and footnote dictionaries.

Use `TextRun(content="Body\n", text_style=TextStyle(bold=True, italic=False))`. Assert exact structural fragments including `<section>`, `<g:section-style />`, `<p>`, `<span g:bold="true" g:italic="false">Body<br /></span>`, map key, and segment ID. Assert complete round-trip equality.

Add a hand-written XHTML test where `<g:document-tab>` wrappers and `<g:section-style>` appear in noncanonical order. Assert the decoded model is identical and content order is unchanged.

- [ ] **Step 2: Write text-style, link, color, and newline tests**

In `tests/xhtml/test_paragraph.py`, add public round-trip tests for:

```python
TextRun(
    content="First\nSecond\n",
    text_style=TextStyle(
        bold=True,
        italic=False,
        underline=True,
        strikethrough=False,
        small_caps=True,
        baseline_offset="SUPERSCRIPT",
        font_size=Dimension(magnitude=12, unit="UNIT_UNSPECIFIED"),
        font_family="Arial",
        font_weight=700,
        foreground_color=Color(red=0.1, green=0.2, blue=0.3),
        background_color=None,
        link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
    ),
)
```

Assert exact `<a g:bookmark-id="bookmark-1" g:tab-id="tab-1">`, explicit style attributes, all RGB components, transparent background, and two `<br />` elements. Assert the decoded `font_size` unit is `PT` and every other field matches.

Add one hand-written span containing a literal line feed and one `<br />`; assert both become `"\n"`. Add adjacent and empty spans and assert they remain separate `TextRun` objects.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_document.py tests/xhtml/test_paragraph.py -v
```

Expected: tests fail because `Tab.content`, structural elements, and text styles are not supported yet.

- [ ] **Step 4: Implement shared text-style and link helpers**

In `base.py`, explicitly encode/decode these attributes: `bold`, `italic`, `underline`, `strikethrough`, `small-caps`, `baseline-offset`, `font-size`, `font-family`, `font-weight`, foreground/background RGB triples, and transparent markers.

Implement exact `<a>` target validation:

- `href` only creates `UrlLink`;
- `g:tab-id` alone creates `TabLink`;
- `g:bookmark-id` with optional `g:tab-id` creates `BookmarkLink`;
- `g:heading-id` with optional `g:tab-id` creates `HeadingLink`;
- all other combinations raise `XHTMLParseError`.

An absent style becomes `UNSET`; a style with any explicit attribute or link becomes `TextStyle`. Opaque colors require all three components. Dimension attributes create `Dimension(magnitude=value, unit="PT")`.

- [ ] **Step 5: Implement document-tab regions and body section projection**

Extend `_Encoder.encode_tab()` and `_Decoder.decode_tab()` for optional `<g:document-tab>`. Implement explicit wrappers for body, headers, footers, and footnotes. Preserve segment dictionary keys independently from embedded IDs.

For a body, require the first model child to be `SectionBreak`. Consume each break and following structural siblings through the next break into one `<section>`. Decode each `<section>` into one `SectionBreak` plus decoded structural content. Reject empty bodies, direct body content, and section elements in segments.

Initially support empty `SectionStyle()`; Task 3 adds its fields.

- [ ] **Step 6: Implement paragraphs and text runs**

Implement paragraph tag dispatch for `<g:paragraph>` and `<p>` in this task; Task 3 adds all remaining named-style tags. Filter optional paragraph metadata independent of placement, then preserve the order of actual paragraph elements.

Encode every `TextRun` as one span. Split `TextRun.content` on `"\n"` and insert empty XHTML `<br />` children without merging runs. Decode element text, `<br />`, and child tails back into one string. Reject children other than `<br />` inside a span. Do not add or remove terminal newlines.

- [ ] **Step 7: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_document.py tests/xhtml/test_paragraph.py -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_document.py tests/xhtml/test_paragraph.py
git commit -m "feat: encode XHTML body text and regions"
```

---

### Task 3: Paragraph, section, and positioned-object metadata

**Files:**
- Modify: `gdocs_patch/xhtml/base.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_paragraph.py`
- Create: `tests/xhtml/test_structures.py`

**Interfaces:**
- Completes `ParagraphStyle`, `ParagraphBorder`, `TabStop`, `SectionStyle`, and `SectionColumn` encoding.
- Adds all canonical paragraph element tags for named style types.
- Adds `Paragraph.positioned_object_ids`.
- Later named-style definitions reuse these paragraph-style methods.

- [ ] **Step 1: Write a compound paragraph-style test**

Construct one paragraph with `ParagraphStyle` containing every field: named style, alignment, direction, line spacing, spacing mode, all five point dimensions, four paragraph booleans, heading ID, all five borders, transparent shading, and two tab stops. Add two positioned object IDs.

Assert:

- `HEADING_2` uses `<h2>` and the nested style does not repeat that field;
- point dimensions are attributes;
- borders contain required dash style, width, padding, and opaque/transparent color;
- tab-stop order and empty-list behavior are preserved;
- `<g:paragraph-style>` and `<g:positioned-objects>` can be moved between run spans in input without changing run order;
- the round trip matches except approved point-unit normalization.

Add a parameterized test for `UNSET`, `NAMED_STYLE_TYPE_UNSPECIFIED`, `NORMAL_TEXT`, `TITLE`, `SUBTITLE`, and all six headings using their exact tags.

- [ ] **Step 2: Write a complete section-style test**

Create `tests/xhtml/test_structures.py` with one `SectionStyle` containing all scalar values, IDs, booleans, page number, all six margins, and two `SectionColumn` objects. Assert exact constants, point attributes, column order, `UNSET` versus empty columns, and round-trip behavior.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py -v
```

Expected: failures show unsupported paragraph metadata, tags, and section-style fields.

- [ ] **Step 4: Implement reusable structured metadata helpers**

Add explicit point-attribute, structured optional-color child, border, and ordered metadata collection helpers. Structured colors accept either all RGB components or `g:transparent="true"`, never partial or mixed forms.

Implement paragraph-style encode/decode methods on `_Encoder` and `_Decoder`. When encoding a document paragraph, consume `named_style_type` into the owning tag. Accept `g:named-style-type` inside a metadata paragraph style only when no paragraph tag owns that field, as required later by named-style definitions.

- [ ] **Step 5: Implement section styles and positioned objects**

Encode/decode all `SectionStyle` attributes and the optional columns wrapper. Require both width and padding-end on every column. Keep the required empty `<g:section-style />` distinct from absence.

Encode/decode positioned object wrappers, preserving list order and distinguishing `UNSET` from an empty list.

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py
git commit -m "feat: encode XHTML paragraph and section metadata"
```

---

### Task 4: Non-text paragraph elements and table of contents

**Files:**
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_paragraph.py`
- Modify: `tests/xhtml/test_structures.py`

**Interfaces:**
- Completes explicit paragraph-element dispatch for every current concrete subtype.
- Adds recursive `TableOfContents` structural content.
- Reuses Task 2 text-style/link helpers on every style-bearing inline element.

- [ ] **Step 1: Write parameterized paragraph-element round-trip tests**

Use parameterization with hardcoded model/expected-tag cases for:

- `AutoText` → `<g:auto-text>`;
- `ColumnBreak` → `<g:column-break>`;
- `DateElement` → `<time>`;
- `Equation` → `<g:equation>`;
- `FootnoteReference` → `<g:footnote-reference>`;
- `HorizontalRule` → `<hr>`;
- `InlineObjectReference` → `<g:inline-object>`;
- `PageBreak` → `<g:page-break>`;
- `PersonReference` → `<g:person>`;
- `RichLink` → `<g:rich-link>`.

Give each style-bearing variant a distinct explicit style or link across the cases. Assert required fields, optional empty strings, every date/time enum, smart-chip URI distinct from an outer text-style link, and complete round-trip equality.

- [ ] **Step 2: Write recursive table-of-contents tests**

Construct a `TableOfContents` containing two paragraphs and another empty nested table of contents. Place it in a body section. Assert `<g:table-of-contents>`, nested recursive structural decoding, and empty-content preservation.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py -v
```

Expected: failures identify unknown paragraph-element and table-of-contents types.

- [ ] **Step 4: Implement explicit paragraph-element dispatch**

Extend `_Encoder.encode_node()` for every concrete paragraph element and `_Decoder.decode_paragraph_element()` for every approved qualified tag. Reuse style attributes directly on the represented element and wrap one style-bearing content element in `<a>` when linked. Reject multiple children in a content-level anchor and reject children on opaque empty elements.

Use the exact allowed constants from `docs/xhtml-syntax.md`; do not derive enum values from annotations at runtime.

- [ ] **Step 5: Implement recursive table-of-contents encoding**

Encode/decode `TableOfContents.content` through the same structural-sequence visitor with `body=False`. Preserve empty content and reject body-only section elements.

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_paragraph.py tests/xhtml/test_structures.py
git commit -m "feat: encode XHTML paragraph elements"
```

---

### Task 5: Tables, columns, rows, cells, spans, and recursive content

**Files:**
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_structures.py`

**Interfaces:**
- Adds `Table`, `TableColumn`, `TableRow`, `TableCell`, `TableCellStyle`, and `TableCellBorder` support.
- Reuses `_Encoder.encode_structural_sequence()` and `_Decoder.decode_structural_sequence()` recursively for cell content.

- [ ] **Step 1: Write a kitchen-sink table test**

Construct a keyed table with:

- one fixed and one evenly distributed column;
- a header row with min height, explicit booleans, and row key;
- an opaque styled merged cell with `row_span=2`, `column_span=2`, every border, every padding, and content alignment;
- a transparent-background cell;
- nested paragraph, nested table, and table-of-contents content;
- an empty row and empty cell where permitted.

Assert exact `<colgroup>`, `<tbody>`, keys, `rowspan`/`colspan`, row attributes, cell metadata, point dimensions, RGB/transparent colors, and recursive round-trip equality.

- [ ] **Step 2: Write table normalization and invariant tests**

Add focused tests for:

- absent `column_styles` versus an empty `<colgroup />`;
- default-only `TableCellStyle()` normalizing to `UNSET`;
- explicit `rowspan="1"` or `colspan="1"` rejected;
- `FIXED_WIDTH` without width rejected;
- non-fixed width with `g:width` rejected;
- partial cell color and missing border width rejected.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_structures.py -v
```

Expected: failures identify unsupported table elements.

- [ ] **Step 4: Implement table tree encoding**

Extend `_Encoder.encode_node()` with explicit table dispatch. Encode one optional colgroup followed by one tbody canonically. Walk `Table.children`, `TableRow.children`, and `TableCell.children`; serialize cell structural children through `encode_structural_sequence(body=False)`.

Keep row and cell keys separate from styles. Fold all point dimensions into owner attributes. Put row/column spans on `<td>` and all remaining cell style in one metadata child.

- [ ] **Step 5: Implement table tree decoding and invariants**

Accept colgroup and cell-style metadata independent of position but require exactly one tbody. Preserve row/cell order. Combine `rowspan` and `colspan` with optional cell-style fields into one `TableCellStyle`; return `UNSET` only when both spans are one and every other style field is `UNSET`.

Call model constructors only after cross-field validation so constructor `ValueError` does not leak past `XHTMLParseError`.

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_structures.py -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_structures.py
git commit -m "feat: encode XHTML tables"
```

---

### Task 6: Existing lists, bullet presets, bullet styles, and list definitions

**Files:**
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_structures.py`

**Interfaces:**
- Adds parent-level grouping of contiguous `Paragraph.bullet` values into `<g:list>`.
- Adds inverse flattening into `Bullet` or `BulletPreset`.
- Adds complete `DocumentTab.lists`, `ListDefinition`, and `ListLevel` support.

- [ ] **Step 1: Write existing and new paragraph-list tests**

Create one structural sequence containing:

- two adjacent `Bullet(list_id="list-1")` paragraphs at nesting levels zero and two, with distinct bullet text styles;
- a normal paragraph that breaks grouping;
- two adjacent `BulletPreset(preset="BULLET_DISC_CIRCLE_SQUARE")` paragraphs at levels zero and one;
- an adjacent paragraph with a different numbered preset.

Assert one existing-list container, one grouped bullet-preset container, and one separate numbered-preset container. Assert each `<li>` contains exactly one paragraph, bullet style is a dedicated metadata child, and metadata links use an empty `<a>`. Assert flattening restores the exact bullets.

- [ ] **Step 2: Write list-definition and list-level tests**

Construct `DocumentTab.lists` with two dictionary entries, including an empty definition and levels that cover glyph type, glyph symbol, all alignment/default behavior, indentation, start number, complete text style, and metadata link. Assert map keys, definition and level order, `UNSET` versus empty dictionary, and full round-trip equality.

- [ ] **Step 3: Write invalid-list tests**

Assert `XHTMLParseError` for an empty `<g:list>`, both/neither identity attributes, a preset list containing bullet style, an `<li>` with zero or two paragraphs, invalid nesting level, missing glyph format, both/neither glyph variants, and invalid glyph/alignment constants.

- [ ] **Step 4: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_structures.py -v
```

Expected: failures identify unknown list containers and list-definition wrappers.

- [ ] **Step 5: Implement paragraph-list grouping and flattening**

In `_Encoder.encode_structural_sequence()`, use an explicit group key:

```python
def _bullet_group_key(paragraph: Paragraph) -> tuple[str, str] | None:
    bullet = paragraph.bullet
    if isinstance(bullet, Bullet):
        return ("existing", bullet.list_id)
    if isinstance(bullet, BulletPreset):
        return ("preset", bullet.preset)
    return None
```

Consume only adjacent paragraphs with the same non-`None` key. Encode the list identity on the container, nesting on each item, optional existing bullet style, and the paragraph without duplicating its bullet field.

Decode each list into multiple paragraphs and assign a new `Bullet` or `BulletPreset` per paragraph. Do not create a list-group model or synthetic list key.

- [ ] **Step 6: Implement list definitions and levels**

Add document-tab metadata encode/decode for the lists dictionary. Preserve map insertion order and level order. Explicitly validate glyph invariants and allowed constants before constructing `ListLevel`. Reuse shared text-style attributes and empty metadata anchors. Normalize point indentation units to `PT`.

- [ ] **Step 7: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_structures.py -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_structures.py
git commit -m "feat: encode XHTML lists"
```

---

### Task 7: Document style, named styles, and complete normalized round trip

**Files:**
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `tests/xhtml/test_document.py`
- Create: `tests/xhtml/test_round_trip.py`

**Interfaces:**
- Completes `DocumentStyle` and `NamedStyle` support.
- Completes every current modeled field.
- Establishes the full supported-document round-trip invariant, including list definitions.

- [ ] **Step 1: Write complete document-style and named-style tests**

Construct `DocumentStyle` with background color, document mode, page dimensions, every margin, every header/footer ID, every boolean, and page-number start. Assert `<g:document-style />` remains distinct from `UNSET` and all point dimensions deserialize with `PT`.

Construct an ordered named-style list containing all ten named-style type constants. Give one entry complete text style plus an empty metadata anchor link and complete nested paragraph style including `g:named-style-type`. Assert `UNSET` versus empty named-style list and exact order.

- [ ] **Step 2: Write the full normalized round-trip test**

In `tests/xhtml/test_round_trip.py`, start from `tests.parsers.maximal_document.expected_maximal_document()`. Create separate input and expected instances. Add this explicit helper to both so the synthetic parser fixture satisfies the approved body grammar:

```python
def _prepend_leading_section(document: Document) -> None:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    body = content.body
    assert isinstance(body, Body)
    content.body = Body(content=[SectionBreak(style=SectionStyle()), *body.content])
```

Normalize only the approved representational differences on the expected instance:

```python
input_document = expected_maximal_document()
expected_document = expected_maximal_document()
_prepend_leading_section(input_document)
_prepend_leading_section(expected_document)

content = expected_document.tabs[0].content
assert isinstance(content, DocumentTab)
body = content.body
assert isinstance(body, Body)
rich_paragraph = body.content[1]
assert isinstance(rich_paragraph, Paragraph)
for index in (7, 8, 9, 10):
    element = rich_paragraph.elements[index]
    assert isinstance(
        element,
        (InlineObjectReference, PageBreak, PersonReference, RichLink),
    )
    element.text_style = UNSET

table = body.content[3]
assert isinstance(table, Table)
first_cell_style = table.rows[0].cells[0].style
assert isinstance(first_cell_style, TableCellStyle)
first_cell_style.padding_left = Dimension(magnitude=0, unit="PT")
table.rows[0].cells[1].style = UNSET
```

Leave `DocumentTab.lists`, every `ListDefinition`, and every `ListLevel` unchanged. Assert:

```python
xhtml = serialize_document(input_document)
actual = deserialize_document(xhtml)
assert actual == expected_document
assert serialize_document(actual) == xhtml
```

Also assert parent links at representative body, paragraph, table, row, cell, and nested-content nodes.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_document.py tests/xhtml/test_round_trip.py -v
```

Expected: failures identify unsupported document and named styles or remaining field omissions.

- [ ] **Step 4: Implement document and named styles**

Add explicit document-style attributes and its optional background-color child. Preserve `DocumentStyle()` as a present empty element.

Encode/decode ordered named styles. Put `NamedStyle.text_style` attributes on `<g:named-style>`, an optional empty link anchor among its children, and the nested paragraph style in one metadata child. In this context only, represent nested `ParagraphStyle.named_style_type` with `g:named-style-type`.

- [ ] **Step 5: Audit model-field coverage against constructors**

Read every constructor in `gdocs_patch/models/`. For each field, point to one encoder branch, one decoder branch, and one focused or kitchen-sink test. Record the audit in the Task 7 SDD report. Do not add reflection-based coverage machinery to production.

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_document.py tests/xhtml/test_round_trip.py -v
uv run pytest -q
```

Expected: all tests pass and list definitions participate in the final equality assertion.

- [ ] **Step 7: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_document.py tests/xhtml/test_round_trip.py
git commit -m "feat: complete XHTML document round trip"
```

---

### Task 8: Semantic validation and error-context hardening

**Files:**
- Modify: `gdocs_patch/xhtml/base.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Create: `tests/xhtml/test_validation.py`

**Interfaces:**
- Keeps all malformed XML and semantic failures behind `XHTMLParseError`.
- Adds path context without changing successful decode behavior.
- Completes unknown/duplicate/missing/contradictory input validation across the grammar.

- [ ] **Step 1: Write parameterized invalid-input tests**

Create parameterized cases covering at least:

- malformed XML and missing XML declaration;
- wrong root/default/`gdocs` namespaces;
- unknown attributes and children at root, tab, paragraph, style, table, and list levels;
- duplicate singular wrappers placed apart;
- invalid boolean, integer, float, enum, color, link, dimension, span, table-width, and list combinations;
- non-whitespace raw text outside spans;
- a span with a child other than empty `<br />`;
- body without a section, section outside a body, and section missing style;
- leaked model-constructor `ValueError` cases.

Each assertion must check `XHTMLParseError` and a path substring identifying the failing element.

- [ ] **Step 2: Write permissive-order tests**

Add one hand-written document that moves every unique metadata wrapper after or between content: document-tab metadata, section style, paragraph style, positioned objects, cell style, bullet style, named-style paragraph style, and metadata anchor. Assert it decodes to the same expected model and repeated content order is preserved.

- [ ] **Step 3: Run validation tests and verify RED**

Run:

```bash
uv run pytest tests/xhtml/test_validation.py -v
```

Expected: some cases leak `KeyError`, `ValueError`, or `ElementTree.ParseError`, or are silently accepted.

- [ ] **Step 4: Centralize contextual validation**

Complete `base.py` helpers so every decode site follows this order:

1. verify qualified element name;
2. reject unknown attributes;
3. parse required and optional attributes;
4. extract unique metadata independent of placement;
5. reject duplicate/unknown children;
6. validate cross-field combinations;
7. construct the model inside a narrow `try` that wraps constructor `ValueError` as `XHTMLParseError` with path.

Do not add broad `except Exception` handling. Preserve the original XML parser error as `__cause__`.

- [ ] **Step 5: Run validation, XHTML, and complete tests**

Run:

```bash
uv run pytest tests/xhtml/test_validation.py -v
uv run pytest tests/xhtml -v
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add gdocs_patch/xhtml tests/xhtml/test_validation.py
git commit -m "feat: validate XHTML document input"
```

---

### Task 9: Final documentation, verification, and review

**Files:**
- Modify: `docs/xhtml-syntax.md`
- Modify if implementation details changed: `docs/superpowers/specs/2026-08-07-xhtml-document-codec-design.md`
- Test: `tests/xhtml/`

**Interfaces:**
- Preserves the approved grammar while converting the design record into user-facing reference documentation.
- Produces final repository-wide verification evidence.

- [ ] **Step 1: Run the focused XHTML suite before documentation changes**

Run:

```bash
uv run pytest tests/xhtml -v
```

Expected: every XHTML test passes.

- [ ] **Step 2: Rewrite `docs/xhtml-syntax.md` as reference documentation**

Preserve every tested syntax and normalization rule, but reorganize the file into this reader-oriented order:

1. overview, namespace, and complete small example;
2. Python API and error example;
3. document, tabs, regions, and sections;
4. paragraphs, text styles, links, and inline elements;
5. tables and lists, including list definitions;
6. metadata placement, normalization, canonical output, and validation;
7. complete enum-value reference.

Remove chronological design commentary, rejected alternatives, and future-tense phrasing. Ensure every XML example parses under the implemented decoder unless it is explicitly labeled as a fragment.

- [ ] **Step 3: Run documentation and static checks**

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: every command exits zero and no formatter modifies files.

- [ ] **Step 4: Run the complete test suite**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Review the final diff and excluded fixture**

Run:

```bash
git diff --check
git status --short
git diff --stat
git diff -- gdocs_patch/xhtml tests/xhtml docs/xhtml-syntax.md OUTLINE.md
```

Expected: no whitespace errors; only intended codec, tests, and documentation changes; `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json` remains untracked and unstaged.

- [ ] **Step 6: Commit documentation and any final verified adjustments**

```bash
git add docs/xhtml-syntax.md docs/superpowers/specs/2026-08-07-xhtml-document-codec-design.md \
  gdocs_patch/xhtml tests/xhtml
git commit -m "docs: publish XHTML document reference"
```

- [ ] **Step 7: Request code review**

Use the `requesting-code-review` skill against the complete feature-branch diff. Address only verified findings, then rerun Task 9 Steps 3–5 before declaring completion.
