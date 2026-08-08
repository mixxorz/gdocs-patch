# XHTML Document Syntax Reference

Use this reference when reading or writing documents for the
`gdocs_patch.xhtml` codec. It covers the supported
`gdocs_patch.models.Document` vocabulary, the canonical output produced by the
codec, and the additional input forms the parser accepts.

The format is XML 1.0. Document content uses semantic XHTML, while Google
Docs-specific structure and metadata use a versioned namespace. The XHTML
namespace is `http://www.w3.org/1999/xhtml`; throughout this reference, the `g`
prefix denotes `urn:gdocs-patch:xhtml:1`. The XML declaration and both namespace
declarations are required.

Start with the complete example, then consult the sections for document
structure, inline content, tables and lists, metadata and validation, and the
Python API. The complete example is exact canonical serializer output. Smaller
fragments use the same canonical syntax, but may wrap start tags or replace
unrelated content with `...` for readability; examples explicitly described as
accepted input demonstrate the parser's additional ordering flexibility.

## Complete example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Example">
  <body>
    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">
      <g:document-tab>
        <g:body>
          <section>
            <g:section-style />
            <h1>
              <span>Welcome</span>
            </h1>
            <p>
              <span>Read the </span>
              <a href="https://example.com">
                <span>guide</span>
              </a>
            </p>
          </section>
        </g:body>
      </g:document-tab>
    </g:tab>
  </body>
</html>
```

## Documents, tabs, regions, and sections

### Document root

The XHTML `<html>` element represents the `Document` itself. It declares the XHTML and `gdocs` namespaces and carries document-level metadata as `g:*` attributes. The document's top-level tabs are represented directly in `<body>`. `<head>` is forbidden, and `Document.title` is carried by the root `g:title` attribute.

**XML fragment:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:g="urn:gdocs-patch:xhtml:1"
      g:document-id="doc-1"
      g:title="Example"
      g:revision-id="rev-1"
      g:suggestions-view-mode="SUGGESTIONS_INLINE">
  <body>...</body>
</html>
```

The XML declaration is required. The deserializer requires the XHTML namespace and exact `urn:gdocs-patch:xhtml:1` namespace, rejecting unsupported format versions. Exactly one `<body>` is required; `<head>` and XHTML `<title>` are forbidden. `g:document-id` and `g:title` are required. `g:revision-id` is omitted for `UNSET`. `g:suggestions-view-mode` is omitted for `UNSET` and otherwise accepts `DEFAULT_FOR_CURRENT_ACCESS`, `SUGGESTIONS_INLINE`, `PREVIEW_SUGGESTIONS_ACCEPTED`, or `PREVIEW_WITHOUT_SUGGESTIONS`.
### Tabs

Each tab uses a namespaced `<g:tab>` element with tab metadata in `g:*` attributes.

A tab separates its `Tab.content` and `Tab.children` fields explicitly:

**XML fragment:**

```xml
<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">
  <g:document-tab>
    <g:body>
      <section>
        <g:section-style />
        <p><span>Tab content</span></p>
      </section>
    </g:body>
  </g:document-tab>

  <g:child-tabs>
    <g:tab g:tab-id="tab-2" g:title="Nested" g:index="1">
      ...
    </g:tab>
  </g:child-tabs>
</g:tab>
```

`g:tab-id`, `g:title`, and integer `g:index` are required. `g:nesting-level` is a non-negative integer and defaults to `0` when omitted. `g:parent-tab-id` and `g:icon-emoji` accept any string and are omitted for `UNSET`. Parent/child XML nesting represents `Tab.children`, but the independently modeled `g:parent-tab-id` is preserved exactly rather than inferred.

`<g:document-tab>` is absent only when `Tab.content` is `UNSET`; an empty `DocumentTab()` is represented by `<g:document-tab />`. Because `Tab.children` is a required list rather than an `UNSET`-capable field, the canonical representation omits `<g:child-tabs>` when the list is empty.
### Document-tab canonical serialization order

The serializer writes present `DocumentTab` children in this order:

**XML fragment:**

```xml
<g:document-tab>
  <g:document-style />
  <g:named-styles />
  <g:list-definitions />
  <g:body>...</g:body>
  <g:headers>...</g:headers>
  <g:footers>...</g:footers>
  <g:footnotes>...</g:footnotes>
</g:document-tab>
```

Omitted fields disappear without changing the relative order of the remaining children. Input may place these unique field wrappers in any order.
### Bodies and segments

The `DocumentTab` indexed regions use dedicated namespaced wrappers:

- `<g:body>` represents `Body`.
- `<g:headers>` contains `<g:header>` elements.
- `<g:footers>` contains `<g:footer>` elements.
- `<g:footnotes>` contains `<g:footnote>` elements.

Each segment element carries both `g:key` for its containing dictionary key and `g:segment-id` for `Segment.segment_id`. The two values are intentionally independent.

An absent region or collection wrapper means that its `DocumentTab` field is `UNSET`. A present empty headers, footers, or footnotes wrapper represents an empty dictionary. `<g:body />` is invalid: a present Google Docs body must begin with a section break.

**XML fragment:**

```xml
<g:document-tab>
  <g:body>
    <section>
      <g:section-style />
      <p><span>Body content</span></p>
    </section>
  </g:body>
  <g:headers>
    <g:header g:key="header-map-key" g:segment-id="header-1">
      <p><span>Header content</span></p>
    </g:header>
  </g:headers>
</g:document-tab>
```
### Sections

A body contains one or more XHTML `<section>` elements and no direct structural content. Each section represents a leading `SectionBreak` followed by the subsequent body content up to the next break:

**XML fragment:**

```xml
<g:body>
  <section>
    <g:section-style />
    <p><span>First section content</span></p>
  </section>
  <section>
    <g:section-style />
    <p><span>Second section content</span></p>
  </section>
</g:body>
```

`SectionBreak.style` is required. The serializer canonically writes exactly one `<g:section-style>` as the first child of every section, including for an empty style object. Accepted input may place that unique required metadata element anywhere among the section's children. It is metadata rather than ordered content; the resulting `SectionBreak` precedes the section's structural children. Empty sections represent consecutive section breaks.

A present body must contain at least one section; `<g:body />` and direct body content outside a section are rejected. Section breaks are body-only, so headers, footers, footnotes, and table cells contain structural elements directly and reject `<section>`.

`SectionStyle` uses scalar and dimension attributes plus a column collection:

**XML fragment:**

```xml
<g:section-style
    g:column-separator-style="BETWEEN_EACH_COLUMN"
    g:content-direction="LEFT_TO_RIGHT"
    g:section-type="NEXT_PAGE"
    g:default-header-id="header-1"
    g:default-footer-id="footer-1"
    g:even-page-header-id="header-even"
    g:even-page-footer-id="footer-even"
    g:first-page-header-id="header-first"
    g:first-page-footer-id="footer-first"
    g:use-first-page-header-footer="true"
    g:flip-page-orientation="false"
    g:page-number-start="1"
    g:margin-top="72">
  <g:columns>
    <g:column g:width="234" g:padding-end="18" />
  </g:columns>
</g:section-style>
```

The supported dimension attributes are `g:margin-top`, `g:margin-bottom`, `g:margin-left`, `g:margin-right`, `g:margin-header`, and `g:margin-footer`. Their absence means `UNSET`.

Allowed constants:

- `g:column-separator-style`: `COLUMN_SEPARATOR_STYLE_UNSPECIFIED`, `NONE`, `BETWEEN_EACH_COLUMN`
- `g:content-direction`: `CONTENT_DIRECTION_UNSPECIFIED`, `LEFT_TO_RIGHT`, `RIGHT_TO_LEFT`
- `g:section-type`: `SECTION_TYPE_UNSPECIFIED`, `CONTINUOUS`, `NEXT_PAGE`

Header/footer ID attributes accept any string and are omitted for `UNSET`. Boolean attributes accept `true` or `false`; `g:page-number-start` is an integer. An absent `<g:columns>` means `UNSET`; an empty wrapper means an empty list. Each `<g:column>` requires point-magnitude `g:width` and `g:padding-end` attributes.
### Table of contents

`TableOfContents` uses the explicit `<g:table-of-contents>` element:

**XML fragment:**

```xml
<g:table-of-contents>
  <p><span>First heading</span></p>
  <p><span>Second heading</span></p>
</g:table-of-contents>
```

Its children use the normal structural-element syntax. An empty element represents `TableOfContents(content=[])`.

## Paragraphs, text styles, links, and inline elements

### Paragraphs and text runs

The paragraph element canonically represents `ParagraphStyle.named_style_type` using semantic XHTML where an unambiguous element exists and a `gdocs` element otherwise:

- `NORMAL_TEXT`: `<p>`
- `HEADING_1` through `HEADING_6`: `<h1>` through `<h6>`
- `TITLE`: `<g:title>`
- `SUBTITLE`: `<g:subtitle>`
- `NAMED_STYLE_TYPE_UNSPECIFIED`: `<g:named-style-unspecified>`
- `UNSET`, including a normalized empty `ParagraphStyle()`: `<g:paragraph>`

Each of these elements directly represents one `Paragraph` and accepts the same metadata and paragraph-element children. The element supplies `ParagraphStyle.named_style_type`; it is never duplicated in metadata.

The remaining non-empty `Paragraph.style` fields use a `<g:paragraph-style>` metadata child. For example:

**XML fragment:**

```xml
<h2>
  <g:paragraph-style g:alignment="CENTER" />
  <span>Centered heading</span>
</h2>
```

Scalar `ParagraphStyle` fields are attributes on `<g:paragraph-style>`:

**XML fragment:**

```xml
<g:paragraph-style
    g:alignment="CENTER"
    g:direction="LEFT_TO_RIGHT"
    g:line-spacing="120"
    g:spacing-mode="NEVER_COLLAPSE"
    g:keep-lines-together="true"
    g:keep-with-next="false"
    g:avoid-widow-and-orphan="true"
    g:page-break-before="false"
    g:heading-id="heading-1" />
```

Dimension fields are point-magnitude attributes. Borders, shading, and tab stops remain nested metadata because they are structured values. For a document paragraph, `named_style_type` is represented only by the owning paragraph element.

Allowed scalar attribute values:

- `g:alignment`: `ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, `END`, `JUSTIFIED`
- `g:direction`: `CONTENT_DIRECTION_UNSPECIFIED`, `LEFT_TO_RIGHT`, `RIGHT_TO_LEFT`
- `g:spacing-mode`: `SPACING_MODE_UNSPECIFIED`, `NEVER_COLLAPSE`, `COLLAPSE_LISTS`
- `g:keep-lines-together`, `g:keep-with-next`, `g:avoid-widow-and-orphan`, and `g:page-break-before`: `true`, `false`
- `g:line-spacing`: any model-valid floating-point value
- `g:heading-id`: any string

Paragraph dimensions are point-magnitude attributes:

**XML fragment:**

```xml
<g:paragraph-style
    g:space-above="6"
    g:space-below="8"
    g:indent-first-line="18"
    g:indent-start="36"
    g:indent-end="12" />
```

An absent attribute means `UNSET`; `"0"` represents a zero-point `Dimension`.

Paragraph borders use field-specific border elements containing their required color, width, and padding values. `g:dash-style` carries the required scalar field:

**XML fragment:**

```xml
<g:paragraph-style>
  <g:border-bottom
      g:dash-style="SOLID"
      g:width="1"
      g:padding="2">
    <g:color g:red="0.4" g:green="0.5" g:blue="0.6" />
  </g:border-bottom>
</g:paragraph-style>
```

The field-specific names are `<g:border-between>`, `<g:border-top>`, `<g:border-bottom>`, `<g:border-left>`, and `<g:border-right>`. `g:dash-style` accepts `DASH_STYLE_UNSPECIFIED`, `SOLID`, `DOT`, or `DASH`. A transparent Google `OptionalColor`, modeled as `None`, uses `<g:color g:transparent="true" />`. This means a present border with transparent color, not an absent border.

Paragraph shading uses one field-specific color element without recreating Google's absorbed `Shading` wrapper:

**XML fragment:**

```xml
<g:shading-color g:red="0.9" g:green="0.9" g:blue="0.9" />
<g:shading-color g:transparent="true" />
```

The first form is opaque, the second is transparent, and absence means `UNSET`.

Paragraph tab stops preserve the `UNSET`/empty-list distinction and list order:

**XML fragment:**

```xml
<g:tab-stops>
  <g:tab-stop g:alignment="START" g:offset="36" />
  <g:tab-stop g:alignment="END" g:offset="72" />
</g:tab-stops>
```

An absent `<g:tab-stops>` means `UNSET`; `<g:tab-stops />` is an empty list. Each tab stop requires its alignment and offset. `g:alignment` on `<g:tab-stop>` accepts `TAB_STOP_ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, or `END`.

`Paragraph.positioned_object_ids` uses an ordered metadata collection:

**XML fragment:**

```xml
<g:positioned-objects>
  <g:positioned-object g:id="object-1" />
  <g:positioned-object g:id="object-2" />
</g:positioned-objects>
```

An absent wrapper means `UNSET`; an empty wrapper means an empty list. Each `g:id` accepts any string, and collection order is preserved.

The serializer writes optional `<g:paragraph-style>` and `<g:positioned-objects>` metadata before the ordered paragraph elements. The deserializer accepts either unique metadata child anywhere and filters it out while preserving the relative order of paragraph elements. Bullet metadata is outside the paragraph under its containing `<li>`.

Other paragraph-level fields use scalar attributes or namespaced metadata children according to the general mapping rule.

Every `TextRun` is represented by exactly one `<span>`, including an unstyled run. This preserves adjacent run boundaries. Text styles use explicit attributes on that span:

**XML fragment:**

```xml
<p>
  <span g:bold="true">Hello</span>
  <span> world</span>
</p>
```

**XML fragment:**

```xml
<span g:bold="true"
      g:font-size="12"
      g:font-family="Arial"
      g:font-weight="700">Styled text</span>
```

Empty text runs use an empty span. A linked run wraps its single span in `<a>`; no other text-style wrappers are used.

Every line-feed character (`"\n"`) in `TextRun.content` is canonically serialized as `<br />` inside that run's span. Carriage-return characters (`"\r"`) are canonically serialized as `&#13;`, including the carriage-return portion of `"\r\n"`, so XML parsing does not normalize representable model content:

**XML fragment:**

```xml
<span>First<br />Second<br />Third&#13;Fourth&#13;<br />Fifth</span>
```

Deserialization converts each `<br />` back to `"\n"`, decodes `&#13;` as `"\r"`, and also accepts literal line-feed text inside the span as `"\n"`. A span may contain only text and empty `<br />` elements. The serializer neither adds nor removes paragraph-terminal line endings and does not require a paragraph to end with one.
### Text styles and links

`TextStyle` fields are represented as `g:*` attributes on the corresponding style-bearing element. Dimension values are point magnitudes without unit attributes; colors use separate red, green, and blue component attributes.

A span with no style attributes and no `<a>` wrapper is the canonical representation of both `TextRun.text_style is UNSET` and an empty `TextStyle()`. It deserializes to `UNSET`. Boolean values are always explicit attributes when present:

**XML fragment:**

```xml
<span>Unset or empty text style</span>
<span g:bold="false">Explicitly non-bold</span>
<span g:bold="true">Bold</span>
```

The boolean text-style attributes are `g:bold`, `g:italic`, `g:underline`, `g:strikethrough`, and `g:small-caps`; each accepts `true` or `false`, with absence meaning `UNSET`.

`g:baseline-offset` accepts every model literal: `BASELINE_OFFSET_UNSPECIFIED`, `NONE`, `SUPERSCRIPT`, or `SUBSCRIPT`. Absence means `UNSET`.

Text colors have one canonical opaque or transparent form. An opaque foreground always emits `g:foreground-red`, `g:foreground-green`, and `g:foreground-blue`, including zero-valued components; each component must be between `0.0` and `1.0`. `g:foreground-color="transparent"` represents explicit `None`. Absence of both forms means `UNSET`, and opaque components cannot be combined with the transparent marker. Background color uses the identical `g:background-*` pattern.

Font family and weight are independently optional string and integer attributes. `g:font-size` is a point magnitude; its presence creates `Dimension(unit="PT")`, and its absence means `UNSET`.

**XML fragment:**

```xml
<span g:small-caps="true"
      g:font-size="12"
      g:font-family="Arial"
      g:font-weight="700"
      g:foreground-red="0.1"
      g:foreground-green="0.2"
      g:foreground-blue="0.3">Styled text</span>
```

A linked `TextRun` uses `<a>` around its single span. A `UrlLink` uses the XHTML `href` attribute; tab, bookmark, and heading links use their corresponding `g:*` attributes. Optional linked-tab IDs are also represented with `g:*` attributes.

**XML fragment:**

```xml
<a href="https://example.com"><span>Website</span></a>
<a g:tab-id="tab-2"><span>Other tab</span></a>
<a g:bookmark-id="bookmark-1"><span>Bookmark</span></a>
<a g:heading-id="heading-1"><span>Heading</span></a>
```

Exactly one primary target is required: `href` for `UrlLink`, `g:tab-id` alone for `TabLink`, `g:bookmark-id` for `BookmarkLink`, or `g:heading-id` for `HeadingLink`. Bookmark and heading links may additionally carry optional `g:tab-id`. All other target-attribute combinations are rejected.

Each `<span>` creates one `TextRun`; an ancestor `<a>` supplies that run's `TextStyle.link`, while the span attributes supply all other text-style fields. Formatting whitespace between elements is ignored, while whitespace inside a span is preserved as run content. A run span may contain text and empty `<br />` elements only.

A content-level `<a>` contains exactly one style-bearing paragraph element: a run span or one non-text inline element. When a `TextStyle` is metadata rather than rendered content, its owning metadata element contains one empty `<a>` child instead. This preserves one link element and target-attribute syntax without pretending that the metadata has visible linked text.
### Non-text paragraph elements

`AutoText` uses an inline Google Docs element:

**XML fragment:**

```xml
<g:auto-text g:type="PAGE_NUMBER" g:bold="true" />
```

`g:type` is required and accepts `TYPE_UNSPECIFIED`, `PAGE_NUMBER`, or `PAGE_COUNT`. Non-link `TextStyle` fields are attributes on the element. If an inline paragraph element's text style contains a link, `<a>` wraps that element just as it wraps a text-run span:

**XML fragment:**

```xml
<a href="https://example.com">
  <g:auto-text g:type="PAGE_NUMBER" />
</a>
```

`ColumnBreak` uses `<g:column-break />`. Its only modeled field is `text_style`, represented by attributes and an optional wrapping `<a>` using the shared inline-element rules.

`DateElement` uses semantic XHTML `<time>`:

**XML fragment:**

```xml
<time g:date-id="date-1"
      g:date-format="DATE_FORMAT_ISO8601"
      g:time-format="TIME_FORMAT_HOUR_MINUTE"
      g:display-text="2026-08-08"
      g:locale="en-US"
      g:time-zone-id="UTC"
      datetime="2026-08-08T12:00:00Z"
      g:bold="true" />
```

`g:date-id` is required. `datetime` represents optional `timestamp`; the remaining date properties are optional `g:*` attributes. `g:display-text` remains an attribute to distinguish `UNSET` from an empty string. Text style follows the shared inline rules.

`g:date-format` accepts `DATE_FORMAT_UNSPECIFIED`, `DATE_FORMAT_CUSTOM`, `DATE_FORMAT_MONTH_DAY_ABBREVIATED`, `DATE_FORMAT_MONTH_DAY_FULL`, `DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED`, or `DATE_FORMAT_ISO8601`. `g:time-format` accepts `TIME_FORMAT_UNSPECIFIED`, `TIME_FORMAT_DISABLED`, `TIME_FORMAT_HOUR_MINUTE`, or `TIME_FORMAT_HOUR_MINUTE_TIMEZONE`.

`Equation` is an opaque marker with no modeled expression and no `TextStyle`. It uses `<g:equation />` and cannot be wrapped in `<a>`.

`FootnoteReference` uses:

**XML fragment:**

```xml
<g:footnote-reference
    g:footnote-id="footnote-1"
    g:footnote-number="3"
    g:bold="true" />
```

`g:footnote-id` and `g:footnote-number` are required strings. Text style follows the shared inline rules. The ID refers to the corresponding entry under `<g:footnotes>`.

`HorizontalRule` uses standard XHTML `<hr />`, carrying text-style attributes directly and an optional wrapping `<a>` using the shared inline rules.

`InlineObjectReference` uses `<g:inline-object g:inline-object-id="object-1" />`. `g:inline-object-id` is a required string; text style follows the shared inline rules.

`PageBreak` uses `<g:page-break />`. Its only modeled field is `text_style`, represented through the shared inline rules.

`PersonReference` uses:

**XML fragment:**

```xml
<g:person g:person-id="person-1"
          g:email="person@example.com"
          g:name="Example Person" />
```

`g:person-id` is required. `g:email` and `g:name` are omitted for `UNSET` and may be empty strings when explicitly present. Text style follows the shared inline rules.

`RichLink` uses `<g:rich-link>`. Its `g:uri` is smart-chip metadata and is distinct from its optional `TextStyle.link`:

**XML fragment:**

```xml
<g:rich-link
    g:rich-link-id="rich-link-1"
    g:uri="https://drive.google.com/..."
    g:title="Quarterly report"
    g:mime-type="application/vnd.google-apps.document" />
```

`g:rich-link-id` and `g:uri` are required strings. `g:title` and `g:mime-type` are omitted for `UNSET` and may be empty. Text style follows the shared inline rules, including an optional outer `<a>` that remains distinct from `g:uri`.

## Tables and lists

### Tables

Tables use the standard XHTML table tree:

**XML fragment:**

```xml
<table g:table-key="table-1">
  <tbody>
    <tr g:row-key="row-1">
      <td g:cell-key="cell-1">
        <p><span>Cell content</span></p>
      </td>
      <td g:cell-key="cell-2" />
    </tr>
  </tbody>
</table>
```

`<table>`, `<tr>`, and `<td>` represent `Table`, `TableRow`, and `TableCell`. `<tbody>` is a required synthetic XHTML wrapper. The optional `g:table-key`, `g:row-key`, and `g:cell-key` attributes accept any string; their absence represents model `None`. Empty tables, rows, and cells are allowed. Cell children use the normal structural syntax, including nested tables and table-of-contents elements.

`Table.column_styles` uses standard XHTML column metadata before `<tbody>`:

**XML fragment:**

```xml
<colgroup>
  <col g:width-type="FIXED_WIDTH"
       g:width="144" />
  <col g:width-type="EVENLY_DISTRIBUTED" />
</colgroup>
```

An absent `<colgroup>` means `UNSET`; an empty element means an empty list. Column order is preserved, exactly one `<col>` represents each `TableColumn`, and HTML's `span` shorthand is forbidden. `g:width-type` is required and accepts `WIDTH_TYPE_UNSPECIFIED`, `EVENLY_DISTRIBUTED`, or `FIXED_WIDTH`. `FIXED_WIDTH` requires `g:width`, a point magnitude; other width types forbid it. Its presence creates `Dimension(unit="PT")`.

Table-row fields use attributes on `<tr>`:

**XML fragment:**

```xml
<tr g:row-key="row-1"
    g:min-height="24"
    g:prevent-overflow="true"
    g:is-header="false">
  ...
</tr>
```

An absent `g:min-height` means `UNSET`; a present value is a point magnitude and creates `Dimension(unit="PT")`. `g:prevent-overflow` and `g:is-header` accept `true` or `false`, with absence meaning `UNSET`. All rows remain under the single `<tbody>`; `<thead>` and `<tfoot>` are not used.

Merged-cell spans use standard XHTML attributes on `<td>`:

**XML fragment:**

```xml
<td g:cell-key="cell-1" rowspan="2" colspan="3">...</td>
```

`rowspan` and `colspan` map to `TableCellStyle.row_span` and `column_span`. Omission means the model default `1`; values must be positive integers. Explicit `rowspan="1"` or `colspan="1"` is non-canonical and rejected. A `TableCellStyle` containing only default spans and otherwise `UNSET` normalizes to no cell style.

Remaining cell styles use a metadata child:

**XML fragment:**

```xml
<g:cell-style
    g:content-alignment="MIDDLE"
    g:padding-left="6"
    g:padding-right="6"
    g:padding-top="4"
    g:padding-bottom="4">
  <g:background-color g:transparent="true" />
  <g:border-left g:dash-style="SOLID" g:width="1">
    <g:color g:red="0" g:green="0" g:blue="0" />
  </g:border-left>
</g:cell-style>
```

The serializer places the element before structural cell content; the deserializer accepts it anywhere in the cell and filters it from ordered content. An empty/default-only style normalizes to absence. `<g:border-left>`, `<g:border-right>`, `<g:border-top>`, and `<g:border-bottom>` contain required color and width values plus `g:dash-style`, using the allowed paragraph-border dash constants; cell borders have no padding child. Background color uses opaque RGB or transparent syntax. `g:content-alignment` accepts `CONTENT_ALIGNMENT_UNSPECIFIED`, `CONTENT_ALIGNMENT_UNSUPPORTED`, `TOP`, `MIDDLE`, or `BOTTOM`.
### Lists

A list container canonically groups contiguous bullet paragraphs that share either an existing Google list ID or a target bullet preset. Each `<li>` contains exactly one paragraph element using the paragraph syntax defined above. The `<li>` is synthetic grouping syntax; its paragraph child is the actual `Paragraph` model object.

All lists use `<g:list>`. Its attributes preserve Google list identity or a bullet preset, and each item's `g:nesting-level` preserves nesting.

An existing list uses `g:list-id`:

**XML fragment:**

```xml
<g:list g:list-id="existing-list-1">
  <li g:nesting-level="0">
    <p><span>Existing item</span></p>
  </li>
  <li g:nesting-level="1">
    <p><span>Added nested item</span></p>
  </li>
</g:list>
```

Each item deserializes to a `Bullet` carrying the container's list ID and its own nesting level.

A new target list uses `g:bullet-preset`:

**XML fragment:**

```xml
<g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">
  <li g:nesting-level="0">
    <p><span>New item</span></p>
  </li>
</g:list>
```

A `<g:list>` must contain at least one `<li>` because an empty list container has no corresponding model object. Each `<li>` contains exactly one paragraph element and, for an existing list only, at most one `<g:bullet-style>` metadata child in any position.

Exactly one of `g:list-id` and `g:bullet-preset` is required. `g:list-id` accepts any string. `g:bullet-preset` accepts:

- `BULLET_GLYPH_PRESET_UNSPECIFIED`
- `BULLET_DISC_CIRCLE_SQUARE`
- `BULLET_DIAMONDX_ARROW3D_SQUARE`
- `BULLET_CHECKBOX`
- `BULLET_ARROW_DIAMOND_DISC`
- `BULLET_STAR_CIRCLE_SQUARE`
- `BULLET_ARROW3D_CIRCLE_SQUARE`
- `BULLET_LEFTTRIANGLE_DIAMOND_DISC`
- `BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE`
- `BULLET_DIAMOND_CIRCLE_SQUARE`
- `NUMBERED_DECIMAL_ALPHA_ROMAN`
- `NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS`
- `NUMBERED_DECIMAL_NESTED`
- `NUMBERED_UPPERALPHA_ALPHA_ROMAN`
- `NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL`
- `NUMBERED_ZERODECIMAL_ALPHA_ROMAN`

Each item in a preset list deserializes to a `BulletPreset` carrying the container's preset and its own nesting level. No synthetic new-list key is represented; adjacent target items with the same preset intentionally form one canonical list group. `g:nesting-level` is a non-negative integer and defaults canonically to `0` when omitted.

An existing `Bullet.text_style` uses dedicated list-item metadata so its style cannot be mistaken for paragraph-text styling:

**XML fragment:**

```xml
<g:list g:list-id="existing-list-1">
  <li>
    <g:bullet-style
        g:bold="true"
        g:font-size="12" />
    <p><span>Item text</span></p>
  </li>
</g:list>
```

An absent `<g:bullet-style>` means `UNSET`; an empty style normalizes to absence. It uses the same non-link `TextStyle` attributes as a run span. A metadata-only `TextStyle.link` uses one empty `<a>` child:

**XML fragment:**

```xml
<g:bullet-style g:bold="true">
  <a href="https://example.com" />
</g:bullet-style>
```

The empty anchor's target attributes use the same syntax as a linked run. `<g:bullet-style>` is forbidden in a preset list because `BulletPreset` has no `text_style` field.

A target bullet preset is represented by `g:bullet-preset`; an existing list identity is represented by `g:list-id`. These attributes are mutually exclusive.

### List definitions

`DocumentTab.lists` uses a dictionary wrapper alongside the other document-tab metadata:

**XML fragment:**

```xml
<g:list-definitions>
  <g:list-definition g:list-id="list-1">
    <g:list-level
        g:glyph-format="%0."
        g:glyph-type="DECIMAL"
        g:alignment="START"
        g:indent-first-line="18"
        g:indent-start="36"
        g:start-number="1"
        g:bold="true">
      <a href="https://example.com" />
    </g:list-level>
  </g:list-definition>
</g:list-definitions>
```

An absent `<g:list-definitions>` means `UNSET`; an empty wrapper means an empty dictionary. `g:list-id` is the dictionary key and accepts any string. Each `<g:list-definition>` represents `ListDefinition`, preserves the order of its `<g:list-level>` children, and may contain zero levels.

For each level, `g:glyph-format` is required and accepts any string. Exactly one of `g:glyph-type` and `g:glyph-symbol` is required. `g:glyph-symbol` accepts any string. `g:glyph-type` accepts `GLYPH_TYPE_UNSPECIFIED`, `NONE`, `DECIMAL`, `ZERO_DECIMAL`, `UPPER_ALPHA`, `ALPHA`, `UPPER_ROMAN`, or `ROMAN`.

`g:alignment` accepts `BULLET_ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, or `END`; omission uses the model default `BULLET_ALIGNMENT_UNSPECIFIED`. `g:start-number` is an integer and omission uses the model default `0`. Optional `g:indent-first-line` and `g:indent-start` are point magnitudes. Text-style attributes represent `ListLevel.text_style`, and an optional empty `<a>` supplies its metadata link.

## Metadata, normalization, canonical output, and validation

### XML vocabulary

The format uses XML 1.0 and XHTML-style semantic elements for document content, with the versioned `urn:gdocs-patch:xhtml:1` XML namespace for Google Docs-specific metadata and fields that XHTML cannot express.

### Validation and security limits

Deserialization enforces a maximum input size of 10,000,000 characters and a maximum XML element depth of 256, counting the root element as depth 1. It performs a stdlib expat preflight before `ElementTree` can expand content. Any DTD, internal or external entity declaration, or external entity reference is forbidden. The preflight also enforces element depth before construction of the `ElementTree` tree.

Invalid external XHTML input, including parser, declaration, size, depth, and semantic failures, raises `XHTMLParseError`. Parser and recursion causes are chained when applicable; deserialization does not expose a raw parser error or `RecursionError` for these validation failures.

Serialization treats its `Document` as trusted model data returned by Google Docs. It performs the model-to-tag projection and XML rendering without revalidating scalar types, enum values, collection shapes, grammar constraints, or output size and depth. Passing a manually mutated invalid model violates this API precondition; any resulting exception or malformed output is unspecified.

### Formatting attributes

Formatting is represented by explicit canonical `gdocs` attributes, not `style` attributes or stylesheets. Semantic XHTML represents document structure, paragraph named styles where applicable, and links.
### Lossless metadata

Google-specific fields, IDs, non-semantic style values, and values such as explicit `false`, `None`, and `UNSET` use the `gdocs` namespace when XHTML has no unambiguous representation.

Semantic markup is authoritative for the values it represents; equivalent `gdocs` attributes are not duplicated. In particular, `<a>` represents a text run's link. Other `TextStyle` values, including both `bold=True` and `bold=False`, use explicit `gdocs` attributes.
### Elements, attributes, and metadata

You can recognize the four representation forms used throughout the syntax as follows:

1. Structural values and values containing ordered document content appear as XML elements. Examples include `Document`, `Tab`, `Body`, `Segment`, `Paragraph`, `TextRun`, and tables.
2. Scalar values appear as attributes on the element they describe.
3. Non-empty structured metadata appears in namespaced metadata children. Examples include `ParagraphStyle`, borders, and tab stops. These metadata children are not document content and may appear anywhere among the containing element's children in accepted input.
4. `TextStyle` values normally appear as attributes on the element carrying the style. A text run's link is the semantic `<a>` exception. `Bullet.text_style` uses a dedicated `<g:bullet-style>` child so its attributes cannot be mistaken for styles on the item paragraph.

For example, the first child below is paragraph metadata, while the span is the paragraph's first content element:

**XML fragment:**

```xml
<p>
  <g:paragraph-style g:alignment="CENTER" />
  <span>Text</span>
</p>
```
### Document style

`DocumentTab.document_style` uses one metadata element. Scalar values, IDs, and point dimensions are attributes; background color remains a structured child:

**XML fragment:**

```xml
<g:document-style
    g:document-mode="PAGES"
    g:default-header-id="header-1"
    g:default-footer-id="footer-1"
    g:even-page-header-id="header-even"
    g:even-page-footer-id="footer-even"
    g:first-page-header-id="header-first"
    g:first-page-footer-id="footer-first"
    g:use-even-page-header-footer="true"
    g:use-first-page-header-footer="false"
    g:use-custom-header-footer-margins="true"
    g:flip-page-orientation="false"
    g:page-number-start="1"
    g:page-width="612"
    g:page-height="792"
    g:margin-top="72"
    g:margin-bottom="72"
    g:margin-left="72"
    g:margin-right="72"
    g:margin-header="36"
    g:margin-footer="36">
  <g:background-color g:red="1" g:green="1" g:blue="1" />
</g:document-style>
```

An absent `<g:document-style>` means `UNSET`; an empty element represents `DocumentStyle()`. `g:document-mode` accepts `DOCUMENT_MODE_UNSPECIFIED`, `PAGES`, or `PAGELESS`. Boolean attributes accept `true` or `false`; `g:page-number-start` is an integer; ID attributes accept any string. Dimension attributes use point magnitudes. Background color uses RGB components for opaque color or `g:transparent="true"` for `None`; absence means `UNSET`.
### Named styles

`DocumentTab.named_styles` uses an ordered collection:

**XML fragment:**

```xml
<g:named-styles>
  <g:named-style
      g:type="HEADING_1"
      g:bold="true"
      g:font-family="Arial">
    <a href="https://example.com" />
    <g:paragraph-style
        g:named-style-type="HEADING_1"
        g:keep-with-next="true" />
  </g:named-style>
</g:named-styles>
```

An absent `<g:named-styles>` means `UNSET`; an empty wrapper means an empty list; element order is preserved. `g:type` is required and represents `NamedStyle.named_style_type`. Text-style attributes and an optional empty `<a>` represent `NamedStyle.text_style`. The optional `<g:paragraph-style>` represents `NamedStyle.paragraph_style`.

Both `g:type` and the nested paragraph style's `g:named-style-type` accept `NAMED_STYLE_TYPE_UNSPECIFIED`, `NORMAL_TEXT`, `TITLE`, `SUBTITLE`, `HEADING_1`, `HEADING_2`, `HEADING_3`, `HEADING_4`, `HEADING_5`, or `HEADING_6`. A nested `g:named-style-type` attribute is necessary here because no owning paragraph element exists to encode that `ParagraphStyle` field.
### Normalization and omission

The format preserves explicit values while applying these canonical normalization rules:

- An `UNSET` field has no corresponding attribute or child element.
- An empty style object whose fields are all `UNSET` is serialized identically to top-level `UNSET`. This applies to `TextStyle()`, `ParagraphStyle()`, and a default-span `TableCellStyle()` with no other fields set. It does not apply to `DocumentStyle()` or the required `SectionStyle`.
- Deserialization returns the canonical `UNSET` form for such an omitted style.
- A collection field that permits `UNSET` uses an absent wrapper for `UNSET` and an empty wrapper for an empty collection.
- A required collection may define omission as its one canonical empty representation when no `UNSET` distinction exists.
- Boolean fields use explicit `g:*="true"` or `g:*="false"` attributes when present; omission means `UNSET`.
- Explicit `None` for Google's `OptionalColor` uses a `transparent` marker; omission continues to mean `UNSET`.
- XHTML dimensions are always measured in points. Serialization omits `Dimension.unit`; both model unit literals normalize to points, and deserialization constructs `Dimension(unit="PT")`.

Deserializers reject duplicate or contradictory representations, such as `<a href="...">` combined with a `g:link-*` attribute on its run span.
### Structured color convention

A structured `OptionalColor` child such as `<g:color>`, `<g:background-color>`, or `<g:shading-color>` has exactly one of these forms:

**XML fragment:**

```xml
<g:color g:red="0.1" g:green="0.2" g:blue="0.3" />
<g:color g:transparent="true" />
```

Opaque colors require all three components, each between `0.0` and `1.0`, including zero-valued components. Transparent color requires only `g:transparent="true"`; `false`, partial RGB, and mixed forms are rejected.
### Attribute value conventions

- Enum values use the model's uppercase string literals exactly. Each syntax section lists every accepted literal for its enum-valued attributes.
- Boolean attributes accept only `true` and `false`.
- Integer and floating-point attributes use their canonical base-10 XML lexical form.
- String IDs and text attributes preserve their XML-decoded string value exactly.
### Ordering and metadata placement

The serializer emits one deterministic canonical order for attributes, metadata, field wrappers, and content. The deserializer does not require that serialization order:

- attributes are accepted in any order;
- unique metadata children and field wrappers may appear anywhere among their owner's children;
- duplicate metadata or duplicate singular field wrappers are rejected;
- metadata children are filtered out before reconstructing ordered model content;
- the relative order of actual content nodes and repeated collection entries remains significant and is preserved;
- unknown attributes and child elements are rejected.

For example, a `<g:paragraph-style>` appearing between two run spans still applies to the containing paragraph and does not interrupt the two runs' relative order.

Whitespace-only text nodes outside `<span>` are formatting and are ignored. All text inside `<span>`, including spaces and literal line feeds, is content and is preserved. Non-whitespace raw text outside a span is rejected; modeled text stored in attributes, including the document title, uses normal XML attribute escaping and decoding.

## Complete enum-value reference

Enum-valued attributes accept the exact, case-sensitive literals below. Omission
has the field-specific meaning described above; no lowercase aliases are accepted.

| Attribute or field | Accepted values |
| --- | --- |
| `g:suggestions-view-mode` | `DEFAULT_FOR_CURRENT_ACCESS`, `SUGGESTIONS_INLINE`, `PREVIEW_SUGGESTIONS_ACCEPTED`, `PREVIEW_WITHOUT_SUGGESTIONS` |
| `g:document-mode` | `DOCUMENT_MODE_UNSPECIFIED`, `PAGES`, `PAGELESS` |
| section `g:column-separator-style` | `COLUMN_SEPARATOR_STYLE_UNSPECIFIED`, `NONE`, `BETWEEN_EACH_COLUMN` |
| section or paragraph `g:content-direction` / `g:direction` | `CONTENT_DIRECTION_UNSPECIFIED`, `LEFT_TO_RIGHT`, `RIGHT_TO_LEFT` |
| `g:section-type` | `SECTION_TYPE_UNSPECIFIED`, `CONTINUOUS`, `NEXT_PAGE` |
| paragraph `g:alignment` | `ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, `END`, `JUSTIFIED` |
| `g:spacing-mode` | `SPACING_MODE_UNSPECIFIED`, `NEVER_COLLAPSE`, `COLLAPSE_LISTS` |
| paragraph or named-style type | `NAMED_STYLE_TYPE_UNSPECIFIED`, `NORMAL_TEXT`, `TITLE`, `SUBTITLE`, `HEADING_1`, `HEADING_2`, `HEADING_3`, `HEADING_4`, `HEADING_5`, `HEADING_6` |
| paragraph-border or cell-border `g:dash-style` | `DASH_STYLE_UNSPECIFIED`, `SOLID`, `DOT`, `DASH` |
| tab-stop `g:alignment` | `TAB_STOP_ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, `END` |
| text-style `g:baseline-offset` | `BASELINE_OFFSET_UNSPECIFIED`, `NONE`, `SUPERSCRIPT`, `SUBSCRIPT` |
| auto-text `g:type` | `TYPE_UNSPECIFIED`, `PAGE_NUMBER`, `PAGE_COUNT` |
| `g:date-format` | `DATE_FORMAT_UNSPECIFIED`, `DATE_FORMAT_CUSTOM`, `DATE_FORMAT_MONTH_DAY_ABBREVIATED`, `DATE_FORMAT_MONTH_DAY_FULL`, `DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED`, `DATE_FORMAT_ISO8601` |
| `g:time-format` | `TIME_FORMAT_UNSPECIFIED`, `TIME_FORMAT_DISABLED`, `TIME_FORMAT_HOUR_MINUTE`, `TIME_FORMAT_HOUR_MINUTE_TIMEZONE` |
| table-column `g:width-type` | `WIDTH_TYPE_UNSPECIFIED`, `EVENLY_DISTRIBUTED`, `FIXED_WIDTH` |
| cell `g:content-alignment` | `CONTENT_ALIGNMENT_UNSPECIFIED`, `CONTENT_ALIGNMENT_UNSUPPORTED`, `TOP`, `MIDDLE`, `BOTTOM` |
| list-level `g:glyph-type` | `GLYPH_TYPE_UNSPECIFIED`, `NONE`, `DECIMAL`, `ZERO_DECIMAL`, `UPPER_ALPHA`, `ALPHA`, `UPPER_ROMAN`, `ROMAN` |
| list-level `g:alignment` | `BULLET_ALIGNMENT_UNSPECIFIED`, `START`, `CENTER`, `END` |
| list `g:bullet-preset` | `BULLET_GLYPH_PRESET_UNSPECIFIED`, `BULLET_DISC_CIRCLE_SQUARE`, `BULLET_DIAMONDX_ARROW3D_SQUARE`, `BULLET_CHECKBOX`, `BULLET_ARROW_DIAMOND_DISC`, `BULLET_STAR_CIRCLE_SQUARE`, `BULLET_ARROW3D_CIRCLE_SQUARE`, `BULLET_LEFTTRIANGLE_DIAMOND_DISC`, `BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE`, `BULLET_DIAMOND_CIRCLE_SQUARE`, `NUMBERED_DECIMAL_ALPHA_ROMAN`, `NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS`, `NUMBERED_DECIMAL_NESTED`, `NUMBERED_UPPERALPHA_ALPHA_ROMAN`, `NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL`, `NUMBERED_ZERODECIMAL_ALPHA_ROMAN` |

Boolean attributes are not enums: they accept only `true` and `false`.

## Python API

The Python API consists of two functions and no configurable serializer classes:

```python
from gdocs_patch.models import Document
from gdocs_patch.xhtml import deserialize_document, serialize_document

xhtml: str = serialize_document(document)
document: Document = deserialize_document(xhtml)
```

`serialize_document(document: Document) -> str` returns canonical XML 1.0 text. `deserialize_document(xhtml: str) -> Document` parses the supported XHTML subset into the mutable model tree and establishes normal parent links through model constructors.

Malformed XML and semantic validation failures raise one public exception:

```python
class XHTMLParseError(ValueError):
    pass
```

Errors include useful element or attribute context when available. Unknown elements or attributes, duplicate singular metadata, invalid constants, and missing required values are parse errors. Serialization assumes the supplied `Document` is valid trusted model data and does not provide validation for manually mutated model states.

For example, malformed or unsupported input can be handled as follows:

```python
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document

try:
    document = deserialize_document(xhtml)
except XHTMLParseError as error:
    print(f"Invalid XHTML document: {error}")
```
