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

The codec supports the complete current modeled document hierarchy, including tabs, indexed regions, sections, paragraphs, text runs, text and paragraph styles, links, paragraph-element variants, tables, list membership, bullet presets, list definitions and levels, document style, and named styles as documented in the syntax reference.

Out of scope:

- CLI commands and file handling;
- Google API retrieval;
- source/target orchestration;
- compiler invocation or compiler changes;
- combining a target document with source-backed metadata;
- coalescing redundant `createParagraphBullets` requests;
- changing existing list definitions directly.

The future compiler and source-backed target work is recorded in `OUTLINE.md`.

## Format principles

The format is XML 1.0 with the XHTML namespace as the default and `urn:gdocs-patch:xhtml:1` as the versioned `gdocs` namespace. It uses semantic XHTML where that clearly matches the document concept and explicit `gdocs` elements or attributes elsewhere. It does not use CSS or generic Python-object XML.

The serializer emits one canonical representation. The deserializer is deliberately more permissive about attribute order and metadata-child placement, while remaining strict about unknown syntax, duplicates, required values, and invalid combinations. Actual content order and repeated collection order remain significant.

The codec converts the model directly. It does not add or remove paragraph-terminal newlines, repair references, infer missing content, consult a source document, or enforce compiler feasibility. Each `TextRun` remains one `<span>`; each line feed becomes `<br />` and each carriage return becomes `&#13;` canonically, preserving `\n`, `\r`, and `\r\n` exactly through round trips.

Intentional normalizations are limited to:

- every `Dimension` becomes a point magnitude and deserializes with `unit="PT"`;
- empty `TextStyle()` and `ParagraphStyle()` values normalize to `UNSET`;
- a default-span `TableCellStyle()` with no other values normalizes to `UNSET`;
- metadata and attributes serialize in canonical order;
- literal line feeds accepted inside spans serialize back as `<br />`, while carriage returns serialize as `&#13;` to prevent XML normalization;
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

Use a small package with a declarative XHTML syntax tree between the Google Docs models and `ElementTree`:

```text
gdocs_patch/xhtml/
├── __init__.py    # public functions and XHTMLParseError
├── base.py        # namespaces, security limits, rendering, and public error adaptation
├── nodes.py       # generic Node, Text, Field, Children, Tag, Encoder, and Decoder
├── attributes.py  # reusable scalar, point, choice, literal, and composite attributes
├── tags.py        # declarative XHTML vocabulary and child grammar
├── encoder.py     # Document models → XHTML Tag tree
└── decoder.py     # XHTML Tag tree → Document models
```

### Declarative XHTML model

`nodes.py` defines a small XHTML syntax-tree library. A `Tag` subclass declares one qualified XML name, scalar/composite `Field` descriptors, and one `Children` descriptor. `Text` is an explicit ordered child node, so `ElementTree.text` and `ElementTree.tail` are translated only inside the generic XML boundary.

`attributes.py` owns canonical lexical conversion and `UNSET` handling. A scalar `Attribute[T]` represents exactly one XML attribute. `MultiValueAttribute[T]` composes several XML attributes into one Python value, such as an opaque/transparent `Color`.

`tags.py` is model-agnostic. It declares the complete accepted XHTML vocabulary, allowed direct child types, singular/repeated cardinalities, and context-specific variants that share an XML name. For example, paragraph-owned and named-style-owned paragraph metadata use separate tag classes because only the latter accepts `g:named-style-type`.

The generic decoder rejects undeclared attributes and children, accepts declared children independent of order, validates cardinalities, ignores formatting whitespace where text is forbidden, and preserves text exactly where `Text` is declared. It receives an expected root tag type; no global registry, class-name dispatch, or generic Document-model serialization is used.

### Encoder

A private model mapper converts each supported `Document` model object into its declared `Tag` representation. It sets typed tag fields and assembles ordered tag children; it never sets `ElementTree` attributes, `.text`, or `.tail` directly.

```python
class _Encoder:
    def encode_document(self, document: Document) -> HtmlTag: ...
    def encode_structural_sequence(
        self, nodes: list[StructuralElement], *, body: bool = False
    ) -> list[Tag]: ...
```

`serialize_document()` calls the generic XHTML `Encoder` exactly once at the XML boundary:

```text
Document models
└── _Encoder → declared Tag/Text tree
    └── nodes.Encoder → ElementTree
        └── security validation, indentation, and XML rendering
```

The model mapper retains the two unavoidable sibling projections: body sections and adjacent compatible list paragraphs. All XML lexical conversion, unknown vocabulary, cardinality, mixed text, and attribute mechanics are hidden below the tag declarations.

### Decoder

After XML security preflight and `ElementTree.fromstring()`, the generic XHTML `Decoder` parses the entire tree from the expected `HtmlTag` root. A private model mapper then converts typed tags into `Document` models:

```python
class _Decoder:
    def decode_document(self, root: HtmlTag) -> Document: ...
    def decode_structural_sequence(
        self, tags: list[Tag], *, body: bool = False
    ) -> list[StructuralElement]: ...
```

```text
XML text
├── security preflight and ElementTree.fromstring
├── nodes.Decoder → validated Tag/Text tree
└── _Decoder → Document models
```

The mapper handles only semantic projections and model construction: flattening sections, flattening list containers into bullet paragraphs, selecting semantic paragraph styles, reconstructing links and text styles, and preserving `UNSET`/empty collection distinctions. Model constructors receive completed child lists and establish ordinary parent links. Parent references and absolute indices are never represented in the XHTML tree.

## Structural projections

### Sections

A present body contains one or more `<section>` elements. Each section contains one required `SectionStyle` metadata object and represents a leading `SectionBreak` followed by that section's content. An empty body and direct body content are rejected. Section elements are body-only.

### Lists

`<g:list g:list-id="...">` preserves existing `Bullet` membership. `<g:list g:bullet-preset="...">` creates target `BulletPreset` values. Each `<li>` contains one paragraph and optional existing-bullet style metadata. Empty list containers are invalid because they have no corresponding model object.

Serialization groups contiguous compatible bullet paragraphs. New adjacent lists with the same preset intentionally canonicalize into one group. The codec does not optimize the compiler requests produced for those paragraphs.

`DocumentTab.lists` is independently encoded under `<g:list-definitions>`. Dictionary keys, list-definition level order, list-level glyph configuration, indentation, numbering, and text styles all round-trip even though compiler support for mutating those definitions is out of scope.

### Text

Each `TextRun` is exactly one `<span>`, preserving adjacent and empty run boundaries. The encoder replaces each line feed with an empty `<br />` and each carriage return with `&#13;`; the decoder reconstructs those characters and accepts literal line feeds. It adds, removes, or normalizes no model line ending.

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
3. Explicit normalized round trips using `deserialize_document(serialize_document(document))` and a hand-written expected model. Round-trip equality includes `DocumentTab.lists`, `ListDefinition`, and `ListLevel` values.
4. Parameterized invalid input covering malformed XML, unknown syntax, duplicates, missing fields, invalid constants, and contradictory combinations.
5. One kitchen-sink supported document containing nested tabs, regions, sections, list items, list definitions, tables, cells, styles, and every paragraph-element variant.

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
