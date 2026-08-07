# XHTML Document Codec Design

## Goal

Add a deterministic XML/XHTML serializer and deserializer for the supported `gdocs_patch.models.Document` subset.

```python
from gdocs_patch.xhtml import deserialize_document, serialize_document

xhtml = serialize_document(document)
document = deserialize_document(xhtml)
```

The detailed, normative element and attribute grammar lives in [`docs/xhtml-syntax.md`](../../xhtml-syntax.md). This design specifies scope, architecture, data flow, validation, and testing.

## Scope

The codec supports the current document hierarchy, tabs, indexed regions, sections, paragraphs, text runs, text and paragraph styles, links, paragraph-element variants, tables, list membership and bullet presets, document style, and named styles as documented in the syntax reference.

The codec intentionally omits `DocumentTab.lists` definitions. Google assigns and owns existing list definitions; target mutations are expressed through retained `Bullet.list_id` values and `BulletPreset` creation intent. Serialization ignores the definition map, and deserialization sets it to `UNSET`.

Out of scope:

- CLI commands and file handling;
- Google API retrieval;
- source/target orchestration;
- compiler invocation or compiler changes;
- combining omitted target metadata with a source document;
- coalescing redundant `createParagraphBullets` requests;
- changing existing list definitions directly.

The future compiler and source-backed target work is recorded in `OUTLINE.md`.

## Format principles

The format is XML 1.0 with the XHTML namespace as the default and `urn:gdocs-patch:xhtml:1` as the versioned `gdocs` namespace. It uses semantic XHTML where that clearly matches the document concept and explicit `gdocs` elements or attributes elsewhere. It does not use CSS or generic Python-object XML.

The serializer emits one canonical representation. The deserializer is deliberately more permissive about attribute order and metadata-child placement, while remaining strict about unknown syntax, duplicates, required values, and invalid combinations. Actual content order and repeated collection order remain significant.

The codec converts the model directly. It does not add or remove paragraph-terminal newlines, repair references, infer missing content, consult a source document, or enforce compiler feasibility. Each `TextRun` remains one `<span>`; each newline character becomes `<br />` canonically and is reconstructed on input.

Intentional normalizations are limited to:

- every `Dimension` becomes a point magnitude and deserializes with `unit="PT"`;
- empty `TextStyle()` and `ParagraphStyle()` values normalize to `UNSET`;
- a default-span `TableCellStyle()` with no other values normalizes to `UNSET`;
- metadata and attributes serialize in canonical order;
- literal line feeds accepted inside spans serialize back as `<br />`;
- `DocumentTab.lists` definitions are omitted;
- synthetic XHTML section and list containers flatten back into existing model nodes and fields.

`DocumentStyle()` remains distinct from `UNSET`, and the required `SectionStyle` is always represented.

## Public API

Create `gdocs_patch/xhtml/` and export:

```python
def serialize_document(document: Document) -> str: ...

def deserialize_document(xhtml: str) -> Document: ...

class XHTMLParseError(ValueError):
    pass
```

There are no public serializer classes or configuration objects in the initial version.

`serialize_document()` returns canonical XML text including the XML declaration. It raises `ValueError` for model states that the supported grammar cannot represent.

`deserialize_document()` wraps malformed XML and semantic validation failures in `XHTMLParseError`. Errors identify the relevant element or attribute path when available. Unknown elements or attributes, duplicate singular metadata, missing required values, invalid constants, and contradictory representations are errors.

## Architecture

Use a small package:

```text
gdocs_patch/xhtml/
├── __init__.py   # public functions and XHTMLParseError
├── base.py       # namespaces and shared scalar/color/style/XML helpers
├── encoder.py    # private model-tree encoder
└── decoder.py    # private XML-tree decoder
```

### Shared helpers

`base.py` contains explicit XML mechanics rather than model reflection:

- qualified XHTML and `gdocs` names;
- required and optional attribute parsing;
- strict boolean, integer, float, and enum parsing;
- unknown-attribute validation;
- unique metadata-child extraction independent of placement;
- opaque/transparent color handling;
- explicit `TextStyle` attributes and `<a>` link targets;
- parse-path construction and contextual errors.

XML attributes are accepted in any order. Unique metadata children may appear anywhere among their owner's children. The decoder filters metadata before reconstructing ordered content and rejects duplicates. Whitespace outside spans is formatting; text and `<br />` inside spans are run content.

### Encoder

A private `_Encoder` uses the existing `TreeNode.children` hierarchy once encoding reaches actual document content. `Document`, `Tab`, and `DocumentTab` remain explicit because they are not `TreeNode` objects and their field semantics do not form the same tree.

Representative internal API:

```python
class _Encoder:
    def encode_document(self, document: Document) -> Element: ...

    def encode_structural_sequence(
        self,
        nodes: Sequence[StructuralElement],
        *,
        body: bool = False,
    ) -> list[Element]: ...

    def encode_node(self, node: TreeNode) -> Element: ...
```

Call flow:

```text
serialize_document
└── _Encoder.encode_document
    └── encode_tab                         # recursive child tabs
        └── encode_document_tab
            ├── explicit metadata/region fields
            ├── encode body sections
            │   └── encode_structural_sequence
            │       ├── group adjacent bullet paragraphs
            │       └── encode_node
            │           ├── Paragraph → paragraph children
            │           ├── Table → rows → cells → structural sequence
            │           └── TableOfContents → structural sequence
            └── encode segments through the same structural sequence
```

`encode_node()` uses explicit type matching. It does not infer a serializer from class names or object fields.

Two parent-level projections inspect sibling sequences:

1. A body consumes each `SectionBreak` and following structural siblings into one XHTML `<section>`.
2. A structural sequence consumes adjacent paragraphs with the same existing list ID or target bullet preset into one `<g:list>`.

All other tree recursion follows typed child collections directly. Parent pointers and derived indices are never serialized.

The encoder builds an ElementTree, inserts attributes and canonical metadata in stable model-field order, then formats the tree. Formatting must treat `<span>` as mixed content and never introduce whitespace inside it; doing so would mutate `TextRun.content`.

### Decoder

A private `_Decoder` mirrors the encoder:

```python
class _Decoder:
    def decode_document(self, root: Element) -> Document: ...

    def decode_structural_sequence(
        self,
        elements: Sequence[Element],
        *,
        body: bool = False,
    ) -> list[StructuralElement]: ...

    def decode_element(self, element: Element) -> TreeNode: ...
```

Call flow:

```text
deserialize_document
├── ElementTree.fromstring
└── _Decoder.decode_document
    └── decode_tab
        └── decode_document_tab
            ├── extract explicit metadata/region fields
            ├── flatten <section> into SectionBreak + structural children
            ├── flatten <g:list> into Paragraph objects with bullets
            ├── decode tables recursively through cell content
            └── decode segments through the structural dispatcher
```

Model constructors receive completed child lists and establish ordinary parent links. The decoder does not deserialize parent references or absolute indices.

## Structural projections

### Sections

A present body contains one or more `<section>` elements. Each section contains one required `SectionStyle` metadata object and represents a leading `SectionBreak` followed by that section's content. An empty body and direct body content are rejected. Section elements are body-only.

### Lists

`<g:list g:list-id="...">` preserves existing `Bullet` membership. `<g:list g:bullet-preset="...">` creates target `BulletPreset` values. Each `<li>` contains one paragraph and optional existing-bullet style metadata. Empty list containers are invalid because they have no corresponding model object.

Serialization groups contiguous compatible bullet paragraphs. New adjacent lists with the same preset intentionally canonicalize into one group. The codec does not optimize the compiler requests produced for those paragraphs.

### Text

Each `TextRun` is exactly one `<span>`, preserving adjacent and empty run boundaries. The encoder replaces each newline character with an empty `<br />`; the decoder accepts `<br />` and literal line feeds as newline characters. It adds or removes no terminal newline.

All non-link `TextStyle` fields are explicit `gdocs` attributes. A linked content element is wrapped in `<a>`. Metadata-only links, such as a bullet glyph link, use one empty `<a>` child inside the metadata style element.

## Error handling

XML well-formedness errors are wrapped with their parser location. Semantic decoding uses a path propagated through recursive calls. Validation occurs at each element boundary:

1. verify the expected qualified name;
2. validate allowed and required attributes;
3. extract and validate singular metadata;
4. dispatch remaining content children;
5. enforce cross-field invariants before constructing the model.

Examples of cross-field validation include mutually exclusive link targets, opaque versus transparent colors, table width type versus width, positive row/column spans, one list identity form, and required section/body structure.

The decoder accepts metadata placement flexibility but never silently ignores unknown input.

## Testing

Add approximately 25–30 test functions, using parameterization for roughly 50–70 behavioral cases:

```text
tests/xhtml/
├── test_document.py
├── test_paragraph.py
├── test_structures.py
├── test_validation.py
└── test_round_trip.py
```

Test levels:

1. Focused behavior for text runs, newlines, links, booleans, colors, dimensions, metadata placement, sections, lists, tables, and recursive content.
2. Exact canonical XML for representative models, including stable namespace and ordering behavior and indentation that does not mutate mixed content.
3. Explicit normalized round trips using `deserialize_document(serialize_document(document))` and a hand-written expected model.
4. Parameterized invalid input covering malformed XML, unknown syntax, duplicates, missing fields, invalid constants, and contradictory combinations.
5. One kitchen-sink supported document containing nested tabs, regions, sections, list items, tables, cells, styles, and every paragraph-element variant.

Tests assert public behavior rather than private delegation. Expected normalized models are written explicitly rather than derived by production helpers. CLI and live Google API tests are excluded.

## Documentation completion

After implementation and behavior are verified, revise `docs/xhtml-syntax.md` from a chronological design record into user-facing reference documentation. Preserve every approved syntax and normalization decision, but reorganize it around:

1. format overview and namespaces;
2. quick complete example;
3. document and structural elements;
4. paragraphs, text styles, and inline elements;
5. tables and lists;
6. metadata, normalization, validation, and omissions;
7. Python API examples.

This documentation rewrite is the final implementation task so its examples and claims reflect the tested codec rather than anticipated behavior.
