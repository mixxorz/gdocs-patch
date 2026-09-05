GUIDE = """\
Every document body starts with a section. A section contains its settings and
then its paragraphs, tables, and other body content:

<g:body>
  <section>
    <g:section-style />
    <p><span>First section</span></p>
  </section>
</g:body>

Add another `<section>` when the document needs another section break. Give a
new break an explicit `g:section-type`:

<g:body>
  <section>
    <g:section-style />
    <p><span>First section</span></p>
  </section>
  <section>
    <g:section-style g:section-type="NEXT_PAGE" />
    <p><span>Starts on the next page</span></p>
  </section>
</g:body>

Section settings live on `<g:section-style>`. For example, margins are point
values, and columns use nested metadata:

<g:section-style g:section-type="CONTINUOUS"
                 g:margin-left="72" g:margin-right="72">
  <g:columns>
    <g:column g:width="234" g:padding-end="18" />
    <g:column g:width="234" g:padding-end="18" />
  </g:columns>
</g:section-style>

Sections exist only in a document body, not inside headers, footers, footnotes,
or table cells. A retained section break cannot change its section type, and a
concrete section setting cannot currently be cleared by removing its attribute.
Other supported section-style changes are compiled normally.

For the complete list of section-style fields and limitations, run:
  gdocs-patch syntax sections --reference
"""

REFERENCE = """\
Section syntax reference

Required structure
------------------
A `<g:body>` contains one or more `<section>` elements. Every section contains
exactly one `<g:section-style>` plus its body content. The style may be empty,
but it must be present. Sections are allowed only in the document body.

Section attributes
------------------
`<g:section-style>` accepts:

  g:section-type         CONTINUOUS | NEXT_PAGE
  g:column-separator-style
                         NONE | BETWEEN_EACH_COLUMN
  g:content-direction    LEFT_TO_RIGHT | RIGHT_TO_LEFT
  g:use-first-page-header-footer
                         true | false
  g:flip-page-orientation
                         true | false
  g:page-number-start    integer
  g:margin-top           point value
  g:margin-bottom        point value
  g:margin-left          point value
  g:margin-right         point value
  g:margin-header        point value
  g:margin-footer        point value

Columns use one `<g:columns>` child. Each `<g:column>` requires point-valued
`g:width` and `g:padding-end` attributes.

Read-only IDs
-------------
The XHTML codec preserves these optional IDs on `<g:section-style>`:

  g:default-header-id        g:default-footer-id
  g:even-page-header-id      g:even-page-footer-id
  g:first-page-header-id     g:first-page-footer-id

They describe existing Google-managed regions. The compiler does not create,
delete, or change those IDs.

Compiler limits
---------------
A newly inserted section break must have a concrete `g:section-type`. A retained
break cannot change its type. Writable section formatting includes columns,
column separators, content direction, first-page header/footer use, page
orientation, page-number start, and margins.

A concrete writable setting cannot currently be cleared by removing its XHTML
attribute; Google Docs has no equivalent clear operation for these fields. Set
a new concrete value instead. Deleting a section break is supported and keeps
neighboring paragraph and list formatting intact.
"""
