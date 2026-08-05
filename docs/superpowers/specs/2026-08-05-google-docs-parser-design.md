# Google Docs Parser Design

## Goal

Parse an already-decoded Google Docs API v1 `documents.get` response into the native mutable model tree. The public entry point is `Document.gdoc_parser.parse(value)`, and every concrete API-backed model also exposes its own parser for direct use.

The parser supports the modern tab response produced with `includeTabsContent=true`. It intentionally does not decode JSON text, serialize models, calculate document indices, add traversal or parent links, retain unsupported fields, or support the legacy top-level tab representation.

## Model revisions required by parsing

Before adding parsers, align the existing models with the final indexing and tab decisions:

- Remove `Document.legacy_tab`. `Document.tabs` remains required.
- Remove `start_offset` and `end_offset` from `ParagraphElement`, every concrete paragraph element, `TableRow`, and `TableCell`.
- No model stores Google's `startIndex` or `endIndex` values.
- Index calculation, traversal, and parent ownership remain separate future designs.

The native model design specification must be updated in the same change so it no longer describes offsets or legacy tab storage.

## Decoded JSON types

`parsers/base.py` defines the recursive values returned by a normal JSON decoder:

```python
type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type JsonObject = dict[str, JsonValue]
```

`JsonValue` means decoded, JSON-compatible Python data, not JSON text. Parsers do not mutate input values.

## Public parser API

The shared generic interface is:

```python
class GDocParser[T]:
    def parse(self, data: JsonValue, *, path: str = "$") -> T: ...
```

Every concrete parser implements `parse` directly. `path` defaults to the input root for direct calls; parent parsers extend it when invoking children so failures identify their location in the original response.

Primary use:

```python
document = Document.gdoc_parser.parse(decoded_response)
paragraph = Paragraph.gdoc_parser.parse(decoded_paragraph_payload)
```

There is no file-reading or JSON-decoding convenience method. Parsers are stateless and safe to reuse.

## Package and initialization

Parsers use the same semantic vertical slices as models:

```text
gdocs_patch/parsers/
├── __init__.py
├── base.py
├── document.py
├── paragraph.py
├── section.py
├── table.py
└── list.py
```

Each concrete model declares a precisely typed `ClassVar`, such as `gdoc_parser: ClassVar[GDocParser[Paragraph]]`. Its semantic parser module creates one parser and eagerly attaches it:

```python
Paragraph.gdoc_parser = ParagraphParser()
```

`gdocs_patch.parsers` imports every semantic parser module. The root `gdocs_patch` package initializes `parsers`, making parser attributes available regardless of whether a caller imports `gdocs_patch.models` or a specific model module.

`gdocs_patch.parsers` publicly exposes `GDocParser`, `GDocParseError`, `JsonValue`, and `JsonObject`. Concrete parser classes remain importable from their semantic modules, but the model class attribute is the normal API.

The design does not use a parser registry, descriptor, decorator, metaclass, generated parser, or annotation-driven construction.

## Recursive ownership and call stack

A containing parser owns Google wrapper recognition and tagged-union dispatch. It selects a concrete variant inline and passes the value under that variant key to the concrete parser. There is no parser or shared dispatch method for abstract unions.

For example, `DocumentTabParser` handles a structural wrapper conceptually as:

```python
if "paragraph" in raw_element:
    element = Paragraph.gdoc_parser.parse(raw_element["paragraph"], path=...)
```

`ParagraphParser` similarly selects `textRun`, `autoText`, and the other paragraph element variants. Most selected values are objects; scalar union members are also valid parser payloads. For example, `UrlLinkParser` receives the string under `url`, while `BookmarkLinkParser` receives the object under `bookmark` or the scalar value of deprecated `bookmarkId`.

The principal call graph is:

```text
DocumentParser
└── TabParser
    ├── DocumentTabParser
    │   ├── DocumentStyleParser
    │   ├── SegmentParser
    │   ├── NamedStyleParser
    │   ├── ListDefinitionParser
    │   └── concrete structural parser selected inline
    └── TabParser for each child tab

ParagraphParser
├── ParagraphStyleParser
├── BulletParser
└── concrete paragraph-element parser selected inline

TableParser
└── TableRowParser
    └── TableCellParser
        └── concrete structural parser selected inline

TableOfContentsParser
└── concrete structural parser selected inline
```

No parse context, parent node, index origin, or traversal state is passed.

## Exact parser inventory

The implementation contains 41 parsers for concrete API-backed model classes.

### Base values

1. `DimensionParser`
2. `ColorParser`

`ColorParser` receives Google's `Color` object and absorbs its `rgbColor` wrapper. Containing parsers own the outer `OptionalColor`: `{}` becomes `None`; otherwise the `color` value is passed to `ColorParser`.

### Document hierarchy

3. `DocumentParser`
4. `TabParser`
5. `DocumentTabParser`
6. `DocumentStyleParser`
7. `SegmentParser`
8. `TableOfContentsParser`

`TabParser` absorbs `tabProperties`. `DocumentTabParser` absorbs `body.content`, `namedStyles.styles`, and resource maps. `SegmentParser` recognizes exactly one appropriate `headerId`, `footerId`, or `footnoteId` in the supplied segment payload. A resource map key and its segment's embedded ID remain independent values.

### Paragraph hierarchy

9. `UrlLinkParser`
10. `TabLinkParser`
11. `BookmarkLinkParser`
12. `HeadingLinkParser`
13. `TextStyleParser`
14. `BulletParser`
15. `ParagraphBorderParser`
16. `TabStopParser`
17. `ParagraphStyleParser`
18. `TextRunParser`
19. `AutoTextParser`
20. `ColumnBreakParser`
21. `DateElementParser`
22. `EquationParser`
23. `FootnoteReferenceParser`
24. `HorizontalRuleParser`
25. `InlineObjectReferenceParser`
26. `PageBreakParser`
27. `PersonReferenceParser`
28. `RichLinkParser`
29. `ParagraphParser`
30. `NamedStyleParser`

`TextStyleParser` owns link dispatch and absorbs `weightedFontFamily`. Date, person, and rich-link parsers absorb their one-purpose `*Properties` wrappers. Paragraph and text-style suggestion fields are ignored.

### Sections

31. `SectionColumnParser`
32. `SectionStyleParser`
33. `SectionBreakParser`

### Tables

34. `TableCellBorderParser`
35. `TableCellStyleParser`
36. `TableCellParser`
37. `TableRowParser`
38. `TableColumnParser`
39. `TableParser`

`TableParser` absorbs `tableStyle.tableColumnProperties`. `TableRowParser` absorbs `tableRowStyle`. `TableCellParser` recursively parses structural content.

### Lists

40. `ListLevelParser`
41. `ListDefinitionParser`

`ListDefinitionParser` absorbs `listProperties.nestingLevels`.

There is no parser for `Model`, `UnsetType`, `StructuralElement`, `ParagraphElement`, or `Link`. There are no separate parsers for absorbed Google wrappers such as `Body`, `TabProperties`, `TableStyle`, `TableRowStyle`, `NamedStyles`, `ListProperties`, `DateElementProperties`, `PersonProperties`, or `RichLinkProperties`.

## Validation policy

Parsers are strict about data they consume and permissive about data they do not model:

- A required consumed field must be present.
- A present consumed field must have the expected JSON type.
- A present literal field must contain one of the model's supported literal values.
- `bool` is not accepted as an integer even though it subclasses `int` in Python.
- A JSON integer is accepted for a numeric magnitude and normalized as needed for a model float.
- JSON `null` is invalid unless a field explicitly assigns it meaning.
- Unknown or intentionally unsupported object fields are ignored.
- A tagged wrapper must contain exactly one supported variant. Unknown keys do not count as variants.
- Parsing stops at the first error.

Reusable type and field-validation helpers belong in `parsers/base.py`. Tagged-union dispatch remains inline in each containing parser so the supported variants are obvious at the point of use.

## Error behavior

All malformed supported input raises `GDocParseError`, rather than leaking `KeyError`, `TypeError`, or model-constructor `ValueError`.

Errors include the complete decoded-input path, for example:

```text
$.tabs[0].documentTab.body.content[2].paragraph.elements[1].textRun.content: expected str
```

Object fields use dot paths, sequence members use bracketed indices, and map keys use an unambiguous bracketed representation when necessary. A direct parser call starts at `$` unless the caller supplies another path.

If a model constructor rejects a parsed combination, the parser raises `GDocParseError` at that model object's path and preserves the constructor's `ValueError` as the exception cause.

Errors are not aggregated.

## Absence and normalization rules

### General rules

- An absent optional model field becomes `UNSET`.
- A present empty style object creates the corresponding empty style model; it is not treated as absent.
- An omitted intrinsic repeated child collection becomes an empty list.
- Supplied collection objects are newly assembled parsed collections; model constructors retain their intentional collection-aliasing behavior.
- Dictionary insertion order and list order are preserved.
- Dictionary keys supplied by Google are never inferred from IDs inside values.

### Required roots and identities

`DocumentParser` requires `documentId`, `title`, and modern `tabs`. It does not inspect top-level `body`, `headers`, `footers`, or other legacy-tab fields beyond ignoring them as unsupported extras.

`TabParser` requires `tabProperties`, and that object requires `tabId`, `title`, and `index`. Missing `childTabs` becomes `[]`. Missing `documentTab` becomes `UNSET`. Missing `nestingLevel` uses `0`; optional tab metadata remains `UNSET`.

A segment requires its embedded ID. Missing segment content becomes `[]`.

Required scalar identities and concrete variant payloads continue to follow the approved model constructors, including text content, date/person/rich-link IDs, link targets, footnote fields, named-style type, border properties, section-column dimensions, and table-column width type.

### Intrinsic collections

These omitted API collections normalize to empty lists when their containing object is present:

- `Tab.childTabs`
- `Body.content`
- `Segment.content`
- `TableOfContents.content`
- `Paragraph.elements`
- `Table.tableRows`
- `TableRow.tableCells`
- `TableCell.content`
- `ListProperties.nestingLevels`

An absent complete optional wrapper remains `UNSET`; for example, an absent `body` is distinct from a present body whose omitted `content` becomes `[]`.

### Proto defaults

Parsers use the approved model defaults:

- `Dimension.magnitude = 0`
- `Dimension.unit = "UNIT_UNSPECIFIED"`
- omitted RGB components are `0`
- `Tab.nesting_level = 0`
- `Bullet.nesting_level = 0`
- `TableCellStyle.row_span = 1`
- `TableCellStyle.column_span = 1`
- `ListLevel.alignment = "BULLET_ALIGNMENT_UNSPECIFIED"`
- `ListLevel.start_number = 0`

### Optional colors

For a containing optional-color field:

- field absent -> `UNSET`
- field present as `{}` -> `None` (transparent)
- field containing an opaque color -> `Color`

Omitted RGB channels use zero. Color bounds and other cross-field invariants remain enforced by model constructors and are translated into parse errors at the boundary.

### Links

A text style's `link` object is a tagged target:

- `url` -> `UrlLink`
- `tabId` -> `TabLink`
- `bookmark` -> `BookmarkLink`
- `heading` -> `HeadingLink`
- deprecated `bookmarkId` and `headingId` normalize to the corresponding modern model with `tab_id=UNSET`

Exactly one supported link target may be present.

## Ignored API data

The parser intentionally discards:

- all `startIndex` and `endIndex` values at every depth
- suggestion IDs, suggested changes, and suggestion style maps
- top-level legacy tab content
- named ranges
- inline and positioned object resource maps
- positioned-object layout data
- table numeric `rows` and `columns`, which are derived from parsed structure
- all other unmodeled extra fields

Paragraph-level positioned-object IDs remain parsed because they are part of the approved `Paragraph` model.

## Testing strategy

Tests assert observable input-to-model behavior. They do not assert parser delegation, helper calls, singleton identity, annotations, or field existence.

### Maximal integration fixture

Add one generic synthetic `documents.get` fixture that exercises every supported shape at least once:

- modern tabs and nested child tabs
- body, headers, footers, and footnotes
- all four structural variants
- all eleven paragraph element variants
- all four link targets, including strategically selected modern/deprecated forms
- complete document, paragraph, text, section, table, row, and cell styles
- nested table content
- lists and named styles
- opaque and transparent optional colors
- representative omitted proto defaults
- ignored indices, suggestions, derived table counts, and extra fields

The fixture is structurally informed by the supplied API sample but contains only generic synthetic content and no Torchbox or client branding. The integration test parses from `Document` and compares the result with the complete expected model tree.

### Focused happy paths

Each of the 41 concrete parsers receives one direct happy-path case, grouped or parameterized by semantic module. Cases remain small. They establish independent parser behavior and supplement the maximal fixture only where a compact input makes normalization clearer, such as an omitted default, present empty style, transparent color, or deprecated link form.

### Representative invalid input

Because Google is the expected producer and should return well-formed data, invalid-input tests remain deliberately small:

1. a malformed nested supported value reports its full path;
2. a tagged wrapper with zero or multiple supported variants fails;
3. one model-constructor invariant is exposed as a chained `GDocParseError`.

There is no exhaustive mutation, field-type, literal, or malformed-input matrix.

### Verification

Run:

- the full Pytest suite;
- Ruff lint and formatting checks;
- Fixit checks;
- Pyright strict checking;
- all pre-commit hooks;
- a one-off parse of the original sample response when it is locally available.

## Out of scope

This work does not add:

- parsing from JSON text or files;
- legacy tab responses;
- serialization;
- model traversal or parent ownership;
- dynamic index calculation;
- mutation or `batchUpdate` generation;
- suggestion models;
- named ranges or object resources;
- preservation of unknown fields.
