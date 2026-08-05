# Google Docs Native Model Design

## Goal

Build mutable Python data-model classes for the supported parts of a Google Docs API v1 `Document` response. The shapes must support future document loading, editing, traversal, dynamic index calculation, and mutation generation, but this phase implements only the model classes.

Parsing, serialization, traversal, index calculation, and `batchUpdate` request/response types are out of scope. Suggestion data, named ranges, object resource maps, and absolute structural-element indices are intentionally absent from the model design.

## Schema reference

The design is based on:

- `document-14FFBRJOhSbx0cXM8EwlKMQDdnalKjPeelLTr6rZD9EE.documents.get.json`
- The current Google Docs API v1 discovery schema, inspected through `google-api-python-client`

The discovery schema currently contains 170 schemas. There are 111 schemas transitively reachable from `Document`, but this design will model only the concepts selected during this design process. It will not create one shallow Python class per Google schema.

## Global model decisions

- Use ordinary, hand-written Python classes, not dataclasses and not generated classes.
- Instances and their child collections are mutable.
- A future parser will reject unrecognized JSON fields rather than retaining an extension mapping. Recognized but explicitly unsupported fields may be ignored. Parser implementation is outside this phase.
- Use an `UNSET` sentinel when field absence is semantically meaningful.
  - `UNSET` means the provider field was absent.
  - `None` is used only where the model assigns it explicit semantic meaning, notably a transparent `OptionalColor`; it is not a universal synonym for `UNSET`.
  - Do not mechanically expose `UNSET` for every field marked optional by the discovery schema. A class may require a field or normalize an omitted proto-default value when that produces a clearer valid model.
- Google enumerated strings remain strings and use inline, field-specific `Literal[...]` annotations directly in constructor signatures. The model does not define a global enum or separate aliases for these values.
- Closely related Google wrapper schemas may be absorbed into a deeper class when their original JSON nesting can be reconstructed exactly.
- Dictionary keys supplied by Google remain distinct from IDs repeated inside dictionary values. The serializer must not infer one from the other.
- Suggestion fields, named ranges, and inline/positioned object resource maps are not represented in the model. Their values are ignored and discarded during parsing. Paragraph-level object references remain modeled so edits preserve object anchors.
- `StructuralElement` objects do not store Google's absolute `startIndex` or `endIndex` values. Their positions and extents will be derived dynamically from document structure.
- Indices stored by descendants inside a structural element use coordinates relative to that containing structural element. Parsing converts Google's absolute indices to relative indices; serialization converts them back using the structural element's derived absolute position.
- Moving or editing structural elements must therefore shift serialized absolute indices without requiring an index-rewrite pass over the model.

All Python model attributes use idiomatic `snake_case`. JSON boundary code maps them to and from Google's `camelCase` keys.
- Every concrete class has an explicit, fully typed, keyword-only constructor. Required fields have no default; optional fields default to `UNSET` or their approved semantic default. Constructors and classes are hand-written rather than generated.
- All model classes inherit a small `Model` base that supplies structural equality and readable representation. Mutable model objects are unhashable. Parsing, serialization, validation, and traversal do not belong to this base.
- Constructors store supplied list and dictionary objects directly rather than copying them. Container aliasing is intentional for implementation simplicity.
- Intrinsic collections such as paragraph elements, table rows, row cells, and list levels are required constructor arguments. Collections whose complete provider field may be absent default to `UNSET`. Constructors do not use mutable collection defaults or normalize through `None`.
- Constructor requiredness follows semantic meaning: identity, concrete variant payloads, and intrinsic child collections are required; meaningful proto defaults use approved Python defaults; optional presentation metadata and provider-omittable offsets use `UNSET`. Concrete link targets are required except bookmark/heading `tab_id`, which may be `UNSET` for legacy links.
- Constructors enforce semantic invariants that annotations cannot express, including color bounds, list glyph exclusivity, positive table spans, and fixed-width column consistency. They do not duplicate Pyright with exhaustive runtime `isinstance` checks. Invariant failures raise built-in `ValueError` with field-specific messages; no custom model exception hierarchy is introduced.

## Approved classes

### `Document`

Root object for a `documents.get` response.

```text
Document
├── document_id: str
├── title: str
├── revision_id: str | UNSET
├── suggestions_view_mode: Literal[
│     "DEFAULT_FOR_CURRENT_ACCESS",
│     "SUGGESTIONS_INLINE",
│     "PREVIEW_SUGGESTIONS_ACCEPTED",
│     "PREVIEW_WITHOUT_SUGGESTIONS"
│   ] | UNSET
├── tabs: list[Tab]
└── legacy_tab: DocumentTab | UNSET
```

Google exposes first-tab content through legacy fields directly on `Document` when `includeTabsContent` is false or omitted. The model groups these fields into `legacy_tab`:

```text
body
documentStyle
headers
footers
footnotes
lists
namedStyles
```

When serializing `Document`, the fields of `legacy_tab` are emitted at the document's top level. The modern `tabs` representation remains separate, so a response containing both representations can preserve both.

### `Tab`

Represents a tab, its metadata, content, and recursively nested child tabs.

```text
Tab
├── tab_id: str
├── title: str
├── index: int
├── nesting_level: int = 0
├── parent_tab_id: str | UNSET
├── icon_emoji: str | UNSET
├── content: DocumentTab | UNSET
└── children: list[Tab]
```

There is no separate `TabProperties` class. `Tab` absorbs Google's `tabProperties` wrapper and reconstructs this JSON shape during serialization:

```json
{
  "tabProperties": {
    "tabId": "...",
    "title": "...",
    "index": 0,
    "nestingLevel": 0,
    "parentTabId": "...",
    "iconEmoji": "..."
  },
  "documentTab": {},
  "childTabs": []
}
```

Each absent metadata field remains `UNSET`; it is not replaced with a default.

### `DocumentTab`

Container for the content and referenced resources belonging to a modern tab or to `Document.legacy_tab`.

```text
DocumentTab
├── body: list[StructuralElement] | UNSET
├── headers: dict[str, Segment] | UNSET
├── footers: dict[str, Segment] | UNSET
├── footnotes: dict[str, Segment] | UNSET
├── document_style: DocumentStyle | UNSET
├── named_styles: list[NamedStyle] | UNSET
└── lists: dict[str, ListDefinition] | UNSET
```

There is no separate `Body` class. `DocumentTab.body` absorbs Google's one-field `Body` wrapper:

```json
{
  "body": {
    "content": []
  }
}
```

An absent `body` and a present body with absent or empty `content` must remain distinguishable through `UNSET` versus the corresponding list state.

### `Segment`

Shared representation for Google `Header`, `Footer`, and `Footnote` objects, which have identical structure except for the JSON name of their ID field.

```text
Segment
├── segment_id: str
└── content: list[StructuralElement]
```

`DocumentTab` determines the ID key emitted for each collection:

| Collection | Serialized ID field |
|---|---|
| `headers` | `headerId` |
| `footers` | `footerId` |
| `footnotes` | `footnoteId` |

Example:

```json
{
  "headers": {
    "header-map-key": {
      "headerId": "embedded-header-id",
      "content": []
    }
  }
}
```

is represented as a map entry whose key is `header-map-key` and whose `Segment.segment_id` is `embedded-header-id`. Both values are preserved independently.

### Structural elements

Google's tagged `StructuralElement` wrapper is absorbed into a base class and four concrete classes:

```text
StructuralElement

Paragraph(StructuralElement)
SectionBreak(StructuralElement)
Table(StructuralElement)
TableOfContents(StructuralElement)
```

`StructuralElement` defines the shared structural protocol but stores no `start_index` or `end_index` fields. Each concrete element will eventually calculate its extent from its content. A document traversal will calculate its absolute position from the extents of preceding elements and containing structures.

Each concrete class serializes its fields inside the corresponding Google variant key (`paragraph`, `sectionBreak`, `table`, or `tableOfContents`). Any descendant indices are stored relative to the concrete structural element and translated at the JSON boundary.

### `Paragraph`

Concrete structural element containing inline paragraph elements and paragraph-level presentation data.

```text
Paragraph(StructuralElement)
├── elements: list[ParagraphElement]
├── style: ParagraphStyle | UNSET
├── bullet: Bullet | UNSET
└── positioned_object_ids: list[str] | UNSET
```

`Paragraph` has no absolute position fields. Its future extent is calculated from its paragraph elements. Each paragraph element stores indices relative to this paragraph. Google suggestion fields on a paragraph are ignored during parsing.

`Bullet` retains Google's API name. It records a paragraph's membership in a list; it does not directly represent the rendered glyph. Its `list_id` refers to `DocumentTab.lists`, and the selected list nesting level defines glyph and indentation behavior.

```text
Bullet
├── list_id: str
├── nesting_level: int
└── text_style: TextStyle | UNSET
```

`Paragraph.bullet` itself may be `UNSET`. A `Bullet` requires `list_id`. Google commonly omits `nestingLevel` for level zero, as it does in the provided fixture; parsing normalizes that omission to `nesting_level=0`. Only `text_style` is `UNSET` within a valid `Bullet`.

### Paragraph elements

Google's tagged `ParagraphElement` wrapper is absorbed into a base class and eleven concrete classes:

```text
ParagraphElement
├── start_offset: int | UNSET
└── end_offset: int | UNSET

TextRun(ParagraphElement)
AutoText(ParagraphElement)
ColumnBreak(ParagraphElement)
DateElement(ParagraphElement)
Equation(ParagraphElement)
FootnoteReference(ParagraphElement)
HorizontalRule(ParagraphElement)
InlineObjectReference(ParagraphElement)
PageBreak(ParagraphElement)
PersonReference(ParagraphElement)
RichLink(ParagraphElement)
```

`start_offset` and `end_offset` are relative to the containing `Paragraph`, not absolute Google document indices. Either may be `UNSET` if absent in the source. During serialization, the paragraph's dynamically derived absolute start is added to these offsets.

The names `InlineObjectReference` and `PersonReference` replace Google's `InlineObjectElement` and `Person` schema names to describe their roles more precisely. Each concrete class recreates the corresponding Google variant key when serialized.

### `TextRun`

```text
TextRun(ParagraphElement)
├── start_offset
├── end_offset
├── content: str
└── text_style: TextStyle | UNSET
```

Suggestion fields are discarded. Both offsets are retained rather than inferred from `content`; index-unit and boundary calculations belong to the later indexing design.

### `TextStyle`

```text
TextStyle
├── bold: bool | UNSET
├── italic: bool | UNSET
├── underline: bool | UNSET
├── strikethrough: bool | UNSET
├── small_caps: bool | UNSET
├── baseline_offset: Literal[
│     "BASELINE_OFFSET_UNSPECIFIED",
│     "NONE",
│     "SUPERSCRIPT",
│     "SUBSCRIPT"
│   ] | UNSET
├── font_size: Dimension | UNSET
├── font_family: str | UNSET
├── font_weight: int | UNSET
├── foreground_color: Color | None | UNSET
├── background_color: Color | None | UNSET
└── link: Link | UNSET
```

All fields are optional through `UNSET`. There is no `WeightedFontFamily` class. `font_family` and `font_weight` absorb Google's `weightedFontFamily` wrapper and are nested again at the JSON boundary.

### Links

A text style's link is a tagged target represented by an abstract base and four concrete classes:

```text
Link

UrlLink(Link)
└── url: str

TabLink(Link)
└── tab_id: str

BookmarkLink(Link)
├── bookmark_id: str
└── tab_id: str | UNSET

HeadingLink(Link)
├── heading_id: str
└── tab_id: str | UNSET
```

The concrete class determines whether JSON uses `url`, `tabId`, `bookmark`, or `heading`. Legacy `bookmarkId` and `headingId` inputs normalize into `BookmarkLink` and `HeadingLink` with `tab_id=UNSET`; modern nested JSON is emitted later.

### `AutoText`

```text
AutoText(ParagraphElement)
├── start_offset
├── end_offset
├── auto_text_type: Literal["TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"]
└── text_style: TextStyle | UNSET
```

The literal values are written inline in `AutoText`; no `AutoTextType` alias is introduced. Suggestion fields are discarded.

### `ColumnBreak`

```text
ColumnBreak(ParagraphElement)
├── start_offset
├── end_offset
└── text_style: TextStyle | UNSET
```

The concrete class identifies the control element as a column break. Suggestion fields are discarded.

### `DateElement`

`DateElement` absorbs Google's shallow `dateElementProperties` wrapper:

```text
DateElement(ParagraphElement)
├── start_offset
├── end_offset
├── date_id: str
├── date_format: Literal[
│     "DATE_FORMAT_UNSPECIFIED",
│     "DATE_FORMAT_CUSTOM",
│     "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
│     "DATE_FORMAT_MONTH_DAY_FULL",
│     "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
│     "DATE_FORMAT_ISO8601"
│   ] | UNSET
├── display_text: str | UNSET
├── locale: str | UNSET
├── time_format: Literal[
│     "TIME_FORMAT_UNSPECIFIED",
│     "TIME_FORMAT_DISABLED",
│     "TIME_FORMAT_HOUR_MINUTE",
│     "TIME_FORMAT_HOUR_MINUTE_TIMEZONE"
│   ] | UNSET
├── time_zone_id: str | UNSET
├── timestamp: str | UNSET
└── text_style: TextStyle | UNSET
```

All date-property fields may be `UNSET`. `timestamp` remains Google's RFC 3339 string rather than being normalized to `datetime`. Suggestion fields are discarded.

### `Equation`

```text
Equation(ParagraphElement)
├── start_offset
└── end_offset
```

The Docs API does not expose an equation expression or tree. It returns only an equation marker and its index span; the equation payload otherwise contains suggestion IDs, which this model discards. The relative offsets therefore preserve all equation information exposed within the supported scope.

### `FootnoteReference`

```text
FootnoteReference(ParagraphElement)
├── start_offset
├── end_offset
├── footnote_id: str
├── footnote_number: str
└── text_style: TextStyle | UNSET
```

`footnote_id` refers to `DocumentTab.footnotes`. `footnote_number` preserves Google's rendered number as a string. Suggestion fields are discarded.

### `HorizontalRule`

```text
HorizontalRule(ParagraphElement)
├── start_offset
├── end_offset
└── text_style: TextStyle | UNSET
```

The concrete class identifies the control element. Google exposes no additional supported horizontal-rule properties.

### `InlineObjectReference`

```text
InlineObjectReference(ParagraphElement)
├── start_offset
├── end_offset
├── inline_object_id: str
└── text_style: TextStyle | UNSET
```

`inline_object_id` preserves the paragraph's server-side object anchor. The corresponding resource map and object properties are intentionally not loaded because they cannot be mutated through this model. Suggestion fields are discarded.

### `PageBreak`

```text
PageBreak(ParagraphElement)
├── start_offset
├── end_offset
└── text_style: TextStyle | UNSET
```

The concrete class identifies the page break. Google exposes no other supported payload fields. Suggestion fields are discarded.

### `PersonReference`

`PersonReference` absorbs Google's one-purpose `personProperties` wrapper:

```text
PersonReference(ParagraphElement)
├── start_offset
├── end_offset
├── person_id: str
├── email: str | UNSET
├── name: str | UNSET
└── text_style: TextStyle | UNSET
```

There is no separate `PersonProperties` class. Suggestion fields are discarded.

### `RichLink`

A rich link is a Google smart chip, distinct from a normal `TextStyle.link`. It absorbs Google's one-purpose `richLinkProperties` wrapper:

```text
RichLink(ParagraphElement)
├── start_offset
├── end_offset
├── rich_link_id: str
├── uri: str
├── title: str | UNSET
├── mime_type: str | UNSET
└── text_style: TextStyle | UNSET
```

There is no separate `RichLinkProperties` class. Suggestion fields are discarded.

### `ParagraphStyle`

```text
ParagraphStyle
├── named_style_type: Literal[
│     "NAMED_STYLE_TYPE_UNSPECIFIED", "NORMAL_TEXT", "TITLE", "SUBTITLE",
│     "HEADING_1", "HEADING_2", "HEADING_3",
│     "HEADING_4", "HEADING_5", "HEADING_6"
│   ] | UNSET
├── alignment: Literal[
│     "ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END", "JUSTIFIED"
│   ] | UNSET
├── direction: Literal[
│     "CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"
│   ] | UNSET
├── line_spacing: float | UNSET
├── spacing_mode: Literal[
│     "SPACING_MODE_UNSPECIFIED", "NEVER_COLLAPSE", "COLLAPSE_LISTS"
│   ] | UNSET
├── space_above: Dimension | UNSET
├── space_below: Dimension | UNSET
├── indent_first_line: Dimension | UNSET
├── indent_start: Dimension | UNSET
├── indent_end: Dimension | UNSET
├── keep_lines_together: bool | UNSET
├── keep_with_next: bool | UNSET
├── avoid_widow_and_orphan: bool | UNSET
├── page_break_before: bool | UNSET
├── heading_id: str | UNSET
├── border_between: ParagraphBorder | UNSET
├── border_top: ParagraphBorder | UNSET
├── border_bottom: ParagraphBorder | UNSET
├── border_left: ParagraphBorder | UNSET
├── border_right: ParagraphBorder | UNSET
├── shading_color: Color | None | UNSET
└── tab_stops: list[TabStop] | UNSET
```

Each field is independently optional through `UNSET`; `ParagraphStyle()` is valid and represents no direct overrides. Enum-valued attributes use inline field-specific `Literal[...]` annotations. The one-field Google `Shading` wrapper is absorbed into `shading_color`. `ParagraphBorder` and `TabStop` remain reusable classes.

### `Dimension`

```text
Dimension
├── magnitude: float
└── unit: Literal["UNIT_UNSPECIFIED", "PT"]
```

Google uses this value throughout margins, spacing, indentation, font sizes, object sizes, borders, and tables. An omitted proto-default `magnitude` normalizes to `0`; an omitted `unit` normalizes to `"UNIT_UNSPECIFIED"`. Both attributes are always present on a `Dimension`. The containing model field uses `UNSET` when the complete dimension is absent.

### `Color`

Google's `OptionalColor → Color → RgbColor` wrappers collapse into one value class:

```text
Color
├── red: float = 0
├── green: float = 0
└── blue: float = 0
```

Each component is constrained to `0.0..1.0`; omitted proto-default components normalize to `0`. At a containing field, `Color(...)` means opaque, `None` means Google's transparent `OptionalColor` (`{}`), and `UNSET` means the complete color field was absent. Thus an optional-color field is typed as `Color | None | UNSET`.

### `ParagraphBorder`

```text
ParagraphBorder
├── color: Color | None
├── width: Dimension
├── padding: Dimension
└── dash_style: Literal[
      "DASH_STYLE_UNSPECIFIED",
      "SOLID",
      "DOT",
      "DASH"
    ]
```

Once present, a paragraph border requires all four properties. `None` represents a transparent color. The containing `ParagraphStyle.border_*` field uses `UNSET` when that border is absent.

### `TabStop`

```text
TabStop
├── offset: Dimension
└── alignment: Literal[
      "TAB_STOP_ALIGNMENT_UNSPECIFIED",
      "START",
      "CENTER",
      "END"
    ]
```

Both fields are required for a valid tab stop. Absence is represented by omitting it from `ParagraphStyle.tab_stops`; that complete list may itself be `UNSET`.

### `SectionBreak`

```text
SectionBreak(StructuralElement)
└── style: SectionStyle
```

A section break requires its section style. It stores no indices; its future extent and absolute position are derived structurally. Suggestion fields are discarded.

### `SectionStyle`

```text
SectionStyle
├── columns: list[SectionColumn] | UNSET
├── column_separator_style: Literal[
│     "COLUMN_SEPARATOR_STYLE_UNSPECIFIED", "NONE", "BETWEEN_EACH_COLUMN"
│   ] | UNSET
├── content_direction: Literal[
│     "CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"
│   ] | UNSET
├── section_type: Literal[
│     "SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"
│   ] | UNSET
├── default_header_id: str | UNSET
├── default_footer_id: str | UNSET
├── even_page_header_id: str | UNSET
├── even_page_footer_id: str | UNSET
├── first_page_header_id: str | UNSET
├── first_page_footer_id: str | UNSET
├── use_first_page_header_footer: bool | UNSET
├── flip_page_orientation: bool | UNSET
├── page_number_start: int | UNSET
├── margin_top: Dimension | UNSET
├── margin_bottom: Dimension | UNSET
├── margin_left: Dimension | UNSET
├── margin_right: Dimension | UNSET
├── margin_header: Dimension | UNSET
└── margin_footer: Dimension | UNSET
```

Each field is independently `UNSET`; partial section styles are valid because omitted properties inherit or retain other section/document settings. Enum-valued attributes use inline field-specific `Literal[...]` annotations.

### `SectionColumn`

This class replaces Google's verbose `SectionColumnProperties` name:

```text
SectionColumn
├── width: Dimension
└── padding_end: Dimension
```

Both dimensions are required for a concrete column definition. The complete `SectionStyle.columns` field may be `UNSET` when no custom column properties are present.

### `Table`

```text
Table(StructuralElement)
├── rows: list[TableRow]
└── column_styles: list[TableColumn] | UNSET
```

Google's numeric `rows` and `columns` fields are treated as derived data and ignored during parsing. `row_count` is `len(rows)`; `column_count` is calculated from cell structure and column spans. Both counts are regenerated during serialization. `Table` stores no absolute start or end indices.

There is no `TableStyle` class. Its only API field, `tableColumnProperties`, is absorbed into `Table.column_styles` and reconstructed at the JSON boundary. Column style entries describe presentation and are not trusted as the source of table geometry.

### `TableRow`

`TableRow` absorbs Google's one-purpose `TableRowStyle` wrapper:

```text
TableRow
├── start_offset
├── end_offset
├── cells: list[TableCell]
├── min_height: Dimension | UNSET
├── prevent_overflow: bool | UNSET
└── is_header: bool | UNSET
```

Offsets are relative to the containing `Table`. The final three attributes serialize inside `tableRowStyle`; there is no separate `TableRowStyle` class. Suggestion fields are discarded.

### `TableCell`

```text
TableCell
├── start_offset
├── end_offset
├── content: list[StructuralElement]
└── style: TableCellStyle | UNSET
```

Offsets use the containing `Table` coordinate system. Cell content recursively uses the same structural-element hierarchy as the body. Suggestion fields are discarded.

### `TableCellStyle`

```text
TableCellStyle
├── row_span: int = 1
├── column_span: int = 1
├── background_color: Color | None | UNSET
├── border_left: TableCellBorder | UNSET
├── border_right: TableCellBorder | UNSET
├── border_top: TableCellBorder | UNSET
├── border_bottom: TableCellBorder | UNSET
├── padding_left: Dimension | UNSET
├── padding_right: Dimension | UNSET
├── padding_top: Dimension | UNSET
├── padding_bottom: Dimension | UNSET
└── content_alignment: Literal[
      "CONTENT_ALIGNMENT_UNSPECIFIED",
      "CONTENT_ALIGNMENT_UNSUPPORTED",
      "TOP",
      "MIDDLE",
      "BOTTOM"
    ] | UNSET
```

Missing proto-default spans normalize to `1` so table geometry remains calculable. Other style properties may be absent independently.

### `TableCellBorder`

```text
TableCellBorder
├── color: Color | None
├── width: Dimension
└── dash_style: Literal[
      "DASH_STYLE_UNSPECIFIED",
      "SOLID",
      "DOT",
      "DASH"
    ]
```

All three properties are required once a cell border exists. This class remains separate from `ParagraphBorder`, which additionally requires padding.

### `TableColumn`

This class replaces Google's `TableColumnProperties` name:

```text
TableColumn
├── width_type: Literal[
│     "WIDTH_TYPE_UNSPECIFIED",
│     "EVENLY_DISTRIBUTED",
│     "FIXED_WIDTH"
│   ]
└── width: Dimension | UNSET
```

`width` is present only for a fixed-width column. A table's list of these values is exposed directly as `Table.column_styles`; the one-field `TableStyle` wrapper is not modeled.

### `TableOfContents`

```text
TableOfContents(StructuralElement)
└── content: list[StructuralElement]
```

It stores no absolute indices. Its generated entries use the same recursive structural-element hierarchy as other document content. Suggestion fields are discarded.

### `ListDefinition`

Google's `List` and one-field `ListProperties` wrapper collapse into:

```text
ListDefinition
└── levels: list[ListLevel]
```

`DocumentTab.lists` is `dict[str, ListDefinition]`. The map key is the Google list ID referenced by `Bullet.list_id`. Suggestion fields are discarded.

### `ListLevel`

One class represents both ordered and unordered levels:

```text
ListLevel
├── glyph_format: str
├── glyph_type: Literal[
│     "GLYPH_TYPE_UNSPECIFIED",
│     "NONE",
│     "DECIMAL",
│     "ZERO_DECIMAL",
│     "UPPER_ALPHA",
│     "ALPHA",
│     "UPPER_ROMAN",
│     "ROMAN"
│   ] | UNSET
├── glyph_symbol: str | UNSET
├── alignment: Literal[
│     "BULLET_ALIGNMENT_UNSPECIFIED",
│     "START",
│     "CENTER",
│     "END"
│   ]
├── indent_first_line: Dimension | UNSET
├── indent_start: Dimension | UNSET
├── start_number: int = 0
└── text_style: TextStyle | UNSET
```

Exactly one of `glyph_type` and `glyph_symbol` must be set. Missing proto-default alignment normalizes to `"BULLET_ALIGNMENT_UNSPECIFIED"`; missing `startNumber` normalizes to `0`.

### `NamedStyle`

There is no separate `NamedStyles` wrapper. `DocumentTab.named_styles` is directly `list[NamedStyle] | UNSET`, reconstructed under `namedStyles.styles` at the JSON boundary.

```text
NamedStyle
├── named_style_type: Literal[
│     "NAMED_STYLE_TYPE_UNSPECIFIED",
│     "NORMAL_TEXT",
│     "TITLE",
│     "SUBTITLE",
│     "HEADING_1",
│     "HEADING_2",
│     "HEADING_3",
│     "HEADING_4",
│     "HEADING_5",
│     "HEADING_6"
│   ]
├── text_style: TextStyle | UNSET
└── paragraph_style: ParagraphStyle | UNSET
```

The list preserves Google's named-style order.

### `DocumentStyle`

`DocumentStyle` absorbs Google's `Background`, `DocumentFormat`, and page `Size` wrappers:

```text
DocumentStyle
├── background_color: Color | None | UNSET
├── document_mode: Literal[
│     "DOCUMENT_MODE_UNSPECIFIED",
│     "PAGES",
│     "PAGELESS"
│   ] | UNSET
├── page_width: Dimension | UNSET
├── page_height: Dimension | UNSET
├── margin_top: Dimension | UNSET
├── margin_bottom: Dimension | UNSET
├── margin_left: Dimension | UNSET
├── margin_right: Dimension | UNSET
├── margin_header: Dimension | UNSET
├── margin_footer: Dimension | UNSET
├── default_header_id: str | UNSET
├── default_footer_id: str | UNSET
├── even_page_header_id: str | UNSET
├── even_page_footer_id: str | UNSET
├── first_page_header_id: str | UNSET
├── first_page_footer_id: str | UNSET
├── use_even_page_header_footer: bool | UNSET
├── use_first_page_header_footer: bool | UNSET
├── use_custom_header_footer_margins: bool | UNSET
├── flip_page_orientation: bool | UNSET
└── page_number_start: int | UNSET
```

All document-style properties are independent overrides and may be `UNSET`. No separate `Background`, `DocumentFormat`, `PageSize`, or `Size` classes are introduced.

## Module organization

Classes are grouped into semantic vertical slices rather than horizontal technical layers:

```text
gdocs_patch/models/
├── __init__.py       # public re-exports
├── base.py           # Model, UNSET, UnsetType, Dimension, Color
├── document.py       # Document, Tab, DocumentTab, Segment,
│                     # DocumentStyle, StructuralElement, TableOfContents
├── paragraph.py      # Paragraph, Bullet, ParagraphStyle,
│                     # ParagraphBorder, TabStop, all paragraph elements,
│                     # TextStyle, link hierarchy, NamedStyle
├── section.py        # SectionBreak, SectionStyle, SectionColumn
├── table.py          # Table, TableRow, TableCell, TableCellStyle,
│                     # TableCellBorder, TableColumn
└── list.py           # ListDefinition, ListLevel
```

`models.__init__` is the stable import surface. `base.py` includes the two cross-cutting leaf values rather than introducing a separate horizontal `common` module.

## Testing strategy

Tests cover distinct runtime behaviors rather than restating class definitions:

- `UNSET` singleton identity and representation
- exact-class structural equality, readable representation, and unhashability from `Model`
- `Color` component defaults, accepted boundaries, and out-of-range rejection
- `Dimension` proto-default normalization
- `Bullet.nesting_level` default normalization
- `ListLevel` glyph exclusivity
- `TableCellStyle` span defaults and positive-span validation
- `TableColumn` width consistency
- representative direct ownership of a supplied mutable collection

The suite does not test every constructor assignment, every optional field, static annotations at runtime, hierarchy declarations, or out-of-scope JSON behavior. Pyright checks static definitions and types. Verification runs Pytest, Ruff linting and formatting checks, and Pyright.
