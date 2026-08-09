# Declarative XHTML Codec Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all direct model-to-`ElementTree` encoding and `ElementTree`-to-model decoding with the approved declarative XHTML `Tag`, `Field`, `Attribute`, and `Children` architecture while preserving the public XHTML behavior exactly.

**Architecture:** Encoding becomes `Document models → typed Tag/Text tree → generic ElementTree encoder`; decoding becomes `XML security boundary → generic typed Tag/Text decoder → Document models`. `tags.py` declares the complete XML vocabulary and grammar. `encoder.py` and `decoder.py` retain only semantic model projections such as body sections, contiguous lists, semantic paragraph tags, links, and model construction.

**Tech Stack:** Python 3.12+, standard-library `xml.etree.ElementTree`, `uv`, pytest, Ruff, Fixit, Pyright, pre-commit.

## Global Constraints

- Work only in `.worktrees/feature-xhtml-document-codec` on `feature/xhtml-document-codec`; never modify `main` or `design/xhtml-document-codec`.
- Use no subagents unless the user explicitly permits them again.
- Treat `docs/xhtml-syntax.md` as the normative grammar.
- Preserve the public API exactly: `serialize_document()`, `deserialize_document()`, and `XHTMLParseError`.
- Preserve all existing canonical XML, normalization, security limits, error categories, and useful error paths. Existing public behavioral tests must remain unchanged.
- Add tests only for a newly discovered behavioral gap; do not test declarations or implementation structure.
- Use `UNSET`, not a second missing-value sentinel.
- Tag declarations remain agnostic to Google Docs model classes.
- Avoid giant symbol imports in mapper modules: use `from gdocs_patch import models` with names such as `models.AutoText` and `models.Body`, and use `from . import tags` with names such as `tags.BodyTag` and `tags.ColorTag`.
- Model mappers must not create, inspect, or mutate `ElementTree.Element`; `ElementTree` is allowed only at parse/render/security boundaries.
- Do not modify `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json`.
- Commit each completed migration slice only after the complete test suite and static checks pass.

## File Structure

```text
gdocs_patch/xhtml/
├── __init__.py    # unchanged public exports
├── base.py        # namespaces, limits, error adaptation, indentation/rendering
├── nodes.py       # generic declarative XHTML tree and XML boundary
├── attributes.py  # reusable XML attribute fields
├── tags.py        # complete XHTML vocabulary and child grammar
├── encoder.py     # Document models → Tag/Text tree
└── decoder.py     # Tag/Text tree → Document models
```

---

### Task 1: Complete the Generic XHTML Boundary

**Files:**
- Modify: `gdocs_patch/xhtml/nodes.py`
- Modify: `gdocs_patch/xhtml/attributes.py`
- Test: existing `tests/xhtml/`

**Interfaces:**
- Produces `Encoder.encode_element(node: Tag) -> ElementTree.Element` and `Decoder.decode_element(element: ElementTree.Element, node_type: type[T]) -> T` suitable for the complete document tree.
- Produces contextual `DecodeError` paths with repeated-child indexes and attribute names.
- Produces shallow per-node validation during decoding without repeatedly validating descendants; encoding trusts its typed tag tree.

- [ ] Add indexed path steps to `TagDecoder` so repeated tags render as `g:tab[1]`, `g:named-style[1]`, and similar existing paths.
- [ ] Validate each decoded tag at its own current path after its children are decoded; make `Children.validate()` enforce only direct grammar and cardinality.
- [ ] Encode each trusted tag once as recursive encoding reaches it without a second validation pass.
- [ ] Keep whitespace policy declarative through `Children(text_error=..., tail_error=...)`.
- [ ] Add only attribute primitives required by later declarations: positive/non-negative integer variants or decode hooks if those rules cannot remain in semantic mapping.
- [ ] Run `uv run pytest tests/xhtml -q`, Ruff, Fixit, and Pyright; commit as `refactor: complete declarative XHTML boundary`.

---

### Task 2: Document Envelope, Tabs, and Document Metadata

**Files:**
- Modify: `gdocs_patch/xhtml/tags.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `gdocs_patch/xhtml/base.py`

**Interfaces:**
- Produces `HtmlTag`, `BodyTag`, `TabTag`, `ChildTabsTag`, `DocumentTabTag`, document-style tags, named-style wrappers, and list-definition tags.
- Changes `_DocumentEncoder.encode_document(document: Document) -> HtmlTag`.
- Changes `_DocumentDecoder.decode_document(root: HtmlTag) -> Document`.

- [ ] Declare root/document/tab attributes and unique wrappers with exact defaults and canonical field order.
- [ ] Declare full `DocumentStyle`, structured background color, `NamedStyle`, metadata link, `ListDefinition`, and `ListLevel` tags.
- [ ] Reuse shared declarative text-style attributes for span, metadata style, inline element, and list-level contexts without sharing mutable descriptor instances.
- [ ] Convert document, recursive tabs, document-tab metadata, named styles, and list definitions to model/tag mappings.
- [ ] Change `serialize_document()` to encode the returned trusted `HtmlTag` through `TagEncoder` and render it without model revalidation.
- [ ] Change `deserialize_document()` to decode `HtmlTag` before model mapping; retain declaration, DTD/entity, character, and depth preflight.
- [ ] Delete superseded envelope/document-style/named-style/list-definition XML helper methods and constants.
- [ ] Run the full unchanged suite and static checks; commit as `refactor: map XHTML document metadata through tags`.

---

### Task 3: Sections, Regions, and Structural Dispatch

**Files:**
- Modify: `gdocs_patch/xhtml/tags.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`

**Interfaces:**
- Produces body, section, section-style, columns, segment collection, and table-of-contents tags.
- Produces `_DocumentEncoder.encode_structural_sequence(...) -> list[Tag]` and `_DocumentDecoder.decode_structural_sequence(...) -> list[StructuralElement]`.

- [ ] Declare required body sections, full section-style attributes, optional/empty columns, and context-specific header/footer/footnote segment tags.
- [ ] Declare structural child alternatives using lazy `Child` references for paragraphs, lists, tables, and table-of-contents.
- [ ] Map body `SectionBreak` grouping into `SectionTag` children and flatten decoded sections back into model order.
- [ ] Map segment dictionary keys independently from `Segment.segment_id` and preserve absent versus empty wrappers.
- [ ] Map recursive table-of-contents content through the structural dispatcher.
- [ ] Delete superseded section, segment, and structural `ElementTree` parsing/encoding code.
- [ ] Run the full unchanged suite and static checks; commit as `refactor: map XHTML sections and regions through tags`.

---

### Task 4: Paragraph Vocabulary, Links, and Inline Elements

**Files:**
- Modify: `gdocs_patch/xhtml/tags.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `gdocs_patch/xhtml/base.py`

**Interfaces:**
- Produces all semantic paragraph tag classes, positioned-object tags, content and metadata anchor variants, and every paragraph-element tag.
- Generalizes existing `ParagraphTag` behavior across `<g:paragraph>`, `<p>`, headings, title, subtitle, and unspecified named style.

- [ ] Extract reusable declaration factories for text-style attributes while keeping each descriptor owned by exactly one class.
- [ ] Declare URL/tab/bookmark/heading anchor attributes and context-specific anchor child grammars.
- [ ] Declare all paragraph tags with one optional paragraph-style, one optional positioned-object wrapper, and ordered inline content.
- [ ] Declare `AutoText`, `ColumnBreak`, `DateElement`, `Equation`, `FootnoteReference`, `HorizontalRule`, `InlineObjectReference`, `PageBreak`, `PersonReference`, and `RichLink` tags with exact attributes and style-bearing behavior.
- [ ] Map every `ParagraphElement` to/from tags; preserve one span per `TextRun`, `<br />` newlines, outer links, and metadata-only links.
- [ ] Remove direct text-style/link/paragraph-element `ElementTree` helpers from `base.py`, `encoder.py`, and `decoder.py` once no caller remains.
- [ ] Run the full unchanged suite and static checks; commit as `refactor: map XHTML paragraphs through tags`.

---

### Task 5: Lists and Bullet Projection

**Files:**
- Modify: `gdocs_patch/xhtml/tags.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`

**Interfaces:**
- Produces `ListTag`, `ListItemTag`, and `BulletStyleTag`.
- Retains sibling grouping by existing list ID or target bullet preset as a semantic projection.

- [ ] Declare mutually exclusive list ID/preset attributes, non-negative nesting level default, at-least-one list item, one paragraph per item, and optional bullet metadata.
- [ ] Encode contiguous compatible bullet paragraphs into one list tag while reusing the complete paragraph tag mapper.
- [ ] Decode list tags into ordered `Paragraph` models with `Bullet` or `BulletPreset`, rejecting bullet style for preset lists.
- [ ] Delete superseded list XML parsing/encoding code and duplicate preset constants.
- [ ] Run the full unchanged suite and static checks; commit as `refactor: map XHTML lists through tags`.

---

### Task 6: Tables and Recursive Cell Content

**Files:**
- Modify: `gdocs_patch/xhtml/tags.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`

**Interfaces:**
- Produces table, colgroup, column, tbody, row, cell, cell-style, background-color, and cell-border tags.

- [ ] Declare the complete XHTML table tree, required synthetic tbody, optional/empty colgroup, row and cell keys, row defaults, and canonical span attributes.
- [ ] Declare full cell style metadata, structured background color, and four required cell-border variants.
- [ ] Map table columns, rows, cells, spans, normalized empty styles, and recursively nested structural cell content.
- [ ] Enforce fixed-width/width consistency, positive spans, and non-canonical explicit span-one input without exposing XML mechanics to model mappers.
- [ ] Delete superseded table XML parsing/encoding code and duplicate constants.
- [ ] Run the full unchanged suite and static checks; commit as `refactor: map XHTML tables through tags`.

---

### Task 7: Remove the Imperative Codec and Tighten Boundaries

**Files:**
- Modify: `gdocs_patch/xhtml/base.py`
- Modify: `gdocs_patch/xhtml/encoder.py`
- Modify: `gdocs_patch/xhtml/decoder.py`
- Modify: `gdocs_patch/xhtml/nodes.py`
- Modify: `gdocs_patch/xhtml/attributes.py`
- Modify: `gdocs_patch/xhtml/tags.py`

**Interfaces:**
- Leaves `ElementTree` operations only in `nodes.py` and explicit parse/render/security boundary functions; model mapper methods never manipulate XML elements.
- Leaves encoder/decoder classes as model↔tag mappers only.

- [ ] Search for every direct `ElementTree.Element`, `.set()`, `.get()`, `.attrib`, `.text`, `.tail`, `SubElement`, and raw qualified-tag comparison in model mapper methods.
- [ ] Move remaining generic XML behavior downward into fields/tags or retain it only in the security/render boundary.
- [ ] Remove dead scalar parsers, validators, constants, and compatibility branches from `base.py`, `encoder.py`, and `decoder.py`.
- [ ] Ensure `tags.py` contains no imports from `gdocs_patch.models` and no Document-model mapping logic.
- [ ] Compare line counts and report core mapper reduction separately from reusable declarative infrastructure.
- [ ] Run `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run fixit lint .`, `uv run pyright`, and `uv run pre-commit run --all-files`.
- [ ] Commit as `refactor: complete declarative XHTML codec`.

---

### Task 8: Update User-Facing XHTML Documentation

**Files:**
- Modify: `docs/xhtml-syntax.md`
- Modify: `docs/superpowers/specs/2026-08-07-xhtml-document-codec-design.md`

- [ ] Preserve every syntax rule and example while rewriting specification-like implementation language into user-facing documentation.
- [ ] Describe the public API, canonical output, normalization, errors, and extension constraints without exposing private mapper classes as user API.
- [ ] Confirm all examples still match serializer output and all enum tables remain complete.
- [ ] Run markdown-sensitive pre-commit hooks and the complete project verification suite.
- [ ] Commit as `docs: finalize XHTML codec reference`.
