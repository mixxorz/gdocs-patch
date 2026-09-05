# gsheets-patch

Thin, native Google Sheets v4 API access for agents. The CLI and authenticated
Streamable HTTP MCP server expose `spreadsheets.get`, `getByDataFilter`,
`batchUpdate`, and all ten `spreadsheets.values` methods. Request bodies and
responses remain native Google JSON. There is no custom Sheets validation,
preflight read, or editing compiler; the underlying Google client and API retain
their native behavior. Python 3.10+ is supported.

## Install and authenticate

```console
uv tool install gsheets-patch
gsheets-patch auth login --client-secrets client_secret.json
```

Enable the Google Sheets API in your Google Cloud project and configure a Desktop
OAuth client. Login requests `https://www.googleapis.com/auth/spreadsheets`.
You can reuse a Docs OAuth application's client-secret file with `--client-secrets`;
Sheets consent and saved tokens remain separate from Docs.

Credentials are stored at `~/.config/gsheets-patch/credentials.json`. The default
OAuth client path is `~/.config/gsheets-patch/client_secret.json`. Set
`GSHEETS_PATCH_BEARER_TOKEN` to use a Google access token directly.

## Agent guide

Start with `gsheets-patch skill` (or the MCP `skill` tool) for method-first schema
discovery, choosing/batching operations, and a worked inventory-tab example.
The guide is plain Markdown, works offline, and needs no Google credentials.

## CLI

Spreadsheet methods are top-level and values methods are under `values`:

```console
gsheets-patch get SPREADSHEET_ID --ranges 'Sheet1!A1:C10'
gsheets-patch values get SPREADSHEET_ID 'Sheet1!A1:C10'
gsheets-patch values update SPREADSHEET_ID 'Sheet1!A1' \
  --value-input-option USER_ENTERED --body '{"values":[["Name","Count"]]}'
gsheets-patch batch-update SPREADSHEET_ID --body @requests.json
gsheets-patch schema spreadsheets.batchUpdate
gsheets-patch schema RepeatCellRequest
```

`--body` accepts inline JSON, `@path`, or `-` for stdin. Use `--help` on a
command for its native query flags. Successful output is pretty-printed native
JSON, without truncation or a success envelope. Errors are JSON on stderr and
return a nonzero status. Use repeated `--ranges` flags for multiple ranges and
`--fields` for Google's partial-response field selection. Boolean query flags
have `--no-...` forms; omitted flags stay omitted.

### Available operations

| CLI | MCP tool |
| --- | --- |
| `get` | `get_spreadsheet` |
| `get-by-data-filter` | `get_spreadsheet_by_data_filter` |
| `batch-update` | `batch_update_spreadsheet` |
| `values get` | `get_values` |
| `values batch-get` | `batch_get_values` |
| `values batch-get-by-data-filter` | `batch_get_values_by_data_filter` |
| `values update` | `update_values` |
| `values batch-update` | `batch_update_values` |
| `values batch-update-by-data-filter` | `batch_update_values_by_data_filter` |
| `values append` | `append_values` |
| `values clear` | `clear_values` |
| `values batch-clear` | `batch_clear_values` |
| `values batch-clear-by-data-filter` | `batch_clear_values_by_data_filter` |
| `schema [NAME]` | `schema` |
| `skill` | `skill` |

API commands take `SPREADSHEET_ID` first; single-range commands take `RANGE` next.
Write/filter bodies use native Google JSON. For example, `get-by-data-filter`
accepts `includeGridData` **in its body**, not as a query flag.

`schema` works offline using the installed Google client's discovery document.
With no name it lists supported methods and schema names. Pass a fully qualified
method (such as `spreadsheets.values.update`) or a schema name (`CellData`). Nested
`$ref` names can be looked up separately without expanding the entire API schema.

There is no spreadsheet creation, cross-spreadsheet tab copying, dedicated
metadata endpoint, or Google Drive integration. Creating tabs and all native
batch-update request kinds remain available through `batch-update`.

### Native semantics

- `RAW` writes literal strings; `USER_ENTERED` parses input as Sheets would,
  including formulas and locale-dependent date/number interpretation.
- Value reads default to formatted output. Use `--value-render-option FORMULA`
  or `UNFORMATTED_VALUE` when appropriate.
- Value responses omit trailing empty rows/columns. In value writes, `null`
  skips a cell and `""` clears it. Typed cell operations use native `CellData`.
- `values clear` clears values, not formatting. Row deletion, shifted cell
  deletion, and overwriting values are different native operations.
- Use narrow field masks in formatting requests. The wrapper does not supply
  masks, confirm destructive actions, or prevent concurrent edits.
- API requests use a 60-second network timeout and no automatic API retries.
  A failed write may already have taken effect; inspect before retrying append
  or structural changes. Normal OAuth refresh still occurs when necessary.

Google failures use `{"error":{"http_status":400,"payload":...}}`, preserving
Google's payload. Local failures use `{"error":{"type":"input|auth|transport",
"message":"..."}}` with one concrete type. CLI parsing errors exit 2; other
reported failures exit 1.

## MCP

```console
uv tool install 'gsheets-patch[mcp]'
GSHEETS_PATCH_MCP_TOKEN=replace-me gsheets-patch-mcp --host 127.0.0.1 --port 8000
```

Connect to `http://127.0.0.1:8000/mcp` with that static bearer token. The server
provides 13 individual API tools plus `schema` and `skill`; authentication login remains CLI
only. Tool arguments use snake_case; native body keys retain camelCase. Successful
results include matching structured JSON and JSON text; failed calls are marked
as tool errors. The MCP token is separate from the Google access token.

There is no built-in TLS; use a reverse proxy and appropriate access controls if
exposing the server beyond localhost. No stdio transport is provided.

## Development

From the repository root, run `uv sync --all-packages --all-extras --dev` and
`uv run pytest packages/gsheets-patch/tests`. Automated tests are offline and need
no Google credentials. See the [workspace guide](../../README.md) and
[release guide](../../RELEASING.md).
