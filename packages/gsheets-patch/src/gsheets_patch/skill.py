SKILL = """\
---
name: gsheets-patch
description: Work with existing Google spreadsheets through native Sheets API calls.
---

# gsheets-patch

Use native Google JSON, not a custom spreadsheet language. CLI API responses are
JSON; request bodies accept inline JSON, `--body @file.json`, or `--body -` for
stdin. Construct larger bodies in files rather than hand-escaping shell strings.

## Discover from the method, not the CLI spelling

Start with command help and the method schema:

```sh
gsheets-patch batch-update --help
gsheets-patch schema spreadsheets.batchUpdate
```

The method's `request.$ref` names its body schema. Follow only the definitions you
need with `schema NAME`, such as `schema BatchUpdateSpreadsheetRequest` or
`schema RepeatCellRequest`. Names are case-sensitive: `schema batch-update` is
not a native method name. Running `schema` alone lists methods and types.
Don't look up every nested type before starting; use the example below and
consult schemas for unfamiliar fields.

## Choose the smallest useful operation

- `get`: workbook/tab metadata and optional grid data. Select response fields:
  `gsheets-patch get ID --fields 'sheets(properties(sheetId,title))'`.
- `values get` / `values batch-get`: cell values or formulas, addressed by A1
  ranges such as `'Page Types'!A1:C3`. Use repeated `--ranges` for batch reads.
- `values update` / `values batch-update`: write rectangular arrays. Use `RAW`
  for literal inventory data; `USER_ENTERED` interprets formulas, dates and numbers.
- `batch-update`: add tabs, format cells, freeze headers, or change structure.
  Numeric sheet IDs identify tabs; grid indices are zero-based and end-exclusive.

Value reads default to formatted display values. Use `--value-render-option FORMULA`
to inspect formulas or `UNFORMATTED_VALUE` for calculated typed values.
Returned arrays omit trailing empty rows/columns. In values writes, `null` skips a
cell and `""` clears it. Deleting rows is not the same as rewriting their values.

## Example: create and populate an inventory tab

In this example, 123 is a new, unused numeric sheet ID in the existing workbook.
Choose an unused ID/title or use an existing tab's ID and omit `addSheet`.
Save this as `requests.json`:

```json
{
  "requests": [
    {"addSheet": {"properties": {
      "sheetId": 123, "title": "Page Types",
      "gridProperties": {"frozenRowCount": 1}
    }}},
    {"repeatCell": {
      "range": {"sheetId": 123, "startRowIndex": 0, "endRowIndex": 1},
      "cell": {"userEnteredFormat": {"textFormat": {"bold": true}}},
      "fields": "userEnteredFormat.textFormat.bold"
    }},
    {"setBasicFilter": {"filter": {"range": {
      "sheetId": 123, "startRowIndex": 0, "endRowIndex": 3,
      "startColumnIndex": 0, "endColumnIndex": 3
    }}}},
    {"updateDimensionProperties": {
      "range": {"sheetId": 123, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 3},
      "properties": {"pixelSize": 200}, "fields": "pixelSize"
    }}
  ]
}
```

Then save `values.json` (the page types are illustrative project models):

```json
{
  "valueInputOption": "RAW",
  "data": [{"range": "'Page Types'!A1", "values": [
    ["Page type", "App", "Description"],
    ["HomePage", "home", "Site landing page"],
    ["ArticlePage", "news", "News article"]
  ]}]
}
```

```sh
gsheets-patch batch-update ID --body @requests.json
gsheets-patch values batch-update ID --body @values.json
```

For related inventories, add another tab (for example, Fields) and another entry
in `data`. Batch compatible operations instead of issuing one call per cell.
Requests within a `batch-update` run in order and apply atomically; the two CLI
calls above are separate operations. Narrow formatting masks preserve other
properties. For verification, read only the changed ranges or properties.

## MCP and failures

MCP exposes the same operations with snake_case arguments and native camelCase
body keys. For example, `batch_update_spreadsheet(spreadsheet_id=ID, body=...)`
and `schema(name="spreadsheets.batchUpdate")`. The `skill` tool returns this guide.

The wrapper adds no Sheets validation or general-purpose API retries. Normal
OAuth refresh can resend a request after HTTP 401. Inspect Google's error details;
do not blindly retry an ambiguous append or structural write, since it may
already have applied. Schema and skill discovery need no Google credentials.
Authenticate through the CLI with `auth login`.
"""
