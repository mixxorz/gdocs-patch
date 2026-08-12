GUIDE = """\
Tables use the normal XHTML table shape. Put rows inside one `<tbody>`, and put
paragraphs or other supported document content inside each cell:

<table>
  <tbody>
    <tr>
      <td><p><span>Top left</span></p></td>
      <td><p><span>Top right</span></p></td>
    </tr>
    <tr>
      <td><p><span>Bottom left</span></p></td>
      <td><p><span>Bottom right</span></p></td>
    </tr>
  </tbody>
</table>

Tables returned by `read` can carry opaque keys. Keep these keys when a target
table, row, or cell represents the same existing object:

<table g:table-key="table-key">
  <tbody>
    <tr g:row-key="row-key">
      <td g:cell-key="cell-key"><p><span>Updated text</span></p></td>
    </tr>
  </tbody>
</table>

Omit a key when you are adding a new table, row, or cell. The compiler uses the
keys to distinguish retained structures from new ones; they do not need to be
meaningful or globally unique.

Use standard `rowspan` and `colspan` attributes for merged cells. Column, row,
and cell formatting is also supported through `<colgroup>`, row attributes,
and `<g:cell-style>` metadata:

<table>
  <colgroup>
    <col g:width-type="FIXED_WIDTH" g:width="144" />
    <col g:width-type="EVENLY_DISTRIBUTED" />
  </colgroup>
  <tbody>
    <tr g:min-height="24">
      <td colspan="2">
        <g:cell-style g:content-alignment="MIDDLE" />
        <p><span>Merged cell</span></p>
      </td>
    </tr>
  </tbody>
</table>

For the complete list of table, column, row, cell, and border attributes, run:
  gdocs-patch syntax tables reference
"""

REFERENCE = """\
Table syntax reference

Required structure
------------------
A table has one optional `<colgroup>` followed by exactly one `<tbody>`. The
body contains `<tr>` rows, and rows contain `<td>` cells. Cells can contain
paragraphs, lists, nested tables, and table-of-contents elements.

Identity keys
-------------
These optional opaque strings tell the compiler which structures were retained:

  <table g:table-key="TABLE_KEY">
  <tr g:row-key="ROW_KEY">
  <td g:cell-key="CELL_KEY">

Keep a key when the target represents the same source object. Omit it for a new
table, row, or cell. Keys do not need to be meaningful or globally unique.
When duplicate keys exist, matching is deterministic.

Columns
-------
Each `<col>` requires `g:width-type`:

  WIDTH_TYPE_UNSPECIFIED
  EVENLY_DISTRIBUTED
  FIXED_WIDTH

A FIXED_WIDTH column also requires `g:width`, expressed in points. Other width
types must omit it.

Rows
----
A `<tr>` accepts these optional attributes:

  g:row-key             opaque identity key
  g:min-height          point value
  g:prevent-overflow    true | false
  g:is-header           true | false

The codec preserves `g:is-header`, but the compiler does not currently apply
changes to that field. Minimum height and overflow behavior are writable.

Cells and spans
---------------
A `<td>` accepts `g:cell-key`, `rowspan`, and `colspan`. Spans must be positive;
omit a span when it is 1. Use spans greater than 1 for merged cells.

Cell style
----------
A cell may contain one `<g:cell-style>` before its document content:

  g:content-alignment   CONTENT_ALIGNMENT_UNSPECIFIED |
                        CONTENT_ALIGNMENT_UNSUPPORTED | TOP | MIDDLE | BOTTOM
  g:padding-left        point value
  g:padding-right       point value
  g:padding-top         point value
  g:padding-bottom      point value

Its optional `<g:background-color>` child uses RGB attributes from 0 to 1 or
`g:transparent="true"`. Borders use `<g:border-left>`, `<g:border-right>`,
`<g:border-top>`, and `<g:border-bottom>`. Every border requires
`g:dash-style`, `g:width`, and one `<g:color>`. Dash styles are
DASH_STYLE_UNSPECIFIED, SOLID, DOT, and DASH.

Compiler behavior
-----------------
The compiler can insert and delete tables, rows, and columns; merge and unmerge
cells; edit supported cell content; and update column, row, and cell styles.
Keys are what let it edit an existing structure instead of replacing it with a
new one. The XHTML producer is expected to provide a valid table shape.
"""
