# gdocs-patch

Efficient Google Doc editing for agents

## Overview

When you ask an agent to edit a Google Doc, they would typically need to
assemble Google Doc API reqeusts manually. This involves finding the right order
of operations, managing document indices, and keeping track of styles. It is all
quite error prone and could lead to data loss if the agent makes a mistake.

gdocs-patch is a CLI and MCP that allows agents to efficiently edit Google
documents by representing documents as XHTML and allowing the agent to make
targetted edits; just like editing a normal file locally.

## Install

Install the CLI with [uv](https://docs.astral.sh/uv/):

```console
uv tool install gdocs-patch
```

gdocs-patch supports Python 3.12 and newer.

## How it works

gdocs-patch exposes a few commands for agents to use:

```
read    Read a Google document as canonical XHTML.
edit    Edit exact text in canonical XHTML.
write   Write canonical XHTML to a Google document.
syntax  Explore the XHTML document syntax.
skill   Show best practices for coding agents using gdocs-patch.
auth    Manage Google authentication.
```

The editing commands (`read`, `edit`, and `write`) all operate using a custom
XHTML dialect that represents every Google doc element as a tag or attribute.
The agents can learn the dialect by reading documents, or through the syntax and
skill commands.

gdocs-patch at its core is a `source doc + target doc = google doc batch
update request` compiler. The agent reads the source document, edits the XHTML
locally, calls `write` to apply the edits to the Google doc. Alternatively,
agents can call `edit` to make targetted replacements without a local copy.

## Usage

```console
gdocs-patch --help
gdocs-patch --version
```

## Google Docs support

This table shows what you can currently change with gdocs-patch and whether the
Google Docs `batchUpdate` API provides enough support for the feature.

- ✅ Supported
- ⚠️ Supported with limitations
- ❌ Unsupported

| Google Docs feature                            | Can add | Can edit | Can delete | `batchUpdate` supports it | Notes                                                                                                               |
| ---------------------------------------------- | :-----: | :------: | :--------: | :-----------------------: | ------------------------------------------------------------------------------------------------------------------- |
| Text and formatting                            |   ✅    |    ✅    |     ✅     |            ✅             | Includes links and common character formatting.                                                                     |
| Paragraphs and headings                        |   ✅    |    ✅    |     ✅     |            ✅             | Includes common paragraph styling. Heading IDs and tab stops are preserved but not editable.                        |
| Bulleted, numbered, and checklist items        |   ✅    |    ✅    |     ✅     |            ✅             | Includes nesting and Google's standard presets.                                                                     |
| Custom list appearance                         |   ❌    |    ⚠️    |     ✅     |            ❌             | Editing requires opt-in conversion to the closest Google preset, which may change its appearance.                   |
| Page breaks                                    |   ✅    |    ✅    |     ✅     |            ✅             | New page breaks can only be inserted in the document body.                                                          |
| Sections                                       |   ✅    |    ⚠️    |     ✅     |            ✅             | Most section formatting is editable, but some existing settings cannot be changed or cleared.                       |
| Tables                                         |   ✅    |    ✅    |     ✅     |            ✅             | Includes rows, columns, merged cells, nested content, and cell styling.                                             |
| Repeating table header rows                    |   ❌    |    ❌    |     ❌     |            ✅             | Existing settings are preserved, but gdocs-patch cannot change them yet.                                            |
| Headers and footers                            |   ❌    |    ✅    |     ❌     |            ✅             | Content in existing headers and footers is editable.                                                                |
| Footnotes                                      |   ❌    |    ✅    |     ✅     |            ✅             | Existing footnote content is editable.                                                                              |
| Document tabs                                  |   ❌    |    ⚠️    |     ❌     |            ✅             | Content in existing tabs is editable, but tabs cannot be created, moved, renamed, or deleted yet.                   |
| Images, drawings, and other embedded objects   |   ❌    |    ❌    |     ✅     |            ⚠️             | Existing objects are preserved. Google supports some image operations, but not every kind of embedded object.       |
| Dates, people, and rich links                  |   ❌    |    ❌    |     ✅     |            ✅             | Existing elements are preserved. Google supports inserting these, but gdocs-patch does not yet expose it.           |
| Equations                                      |   ❌    |    ❌    |     ✅     |            ❌             | Existing equations are preserved. Google does not expose their contents or provide requests to create or edit them. |
| Table of contents                              |   ❌    |    ❌    |     ✅     |            ❌             | Existing tables of contents are preserved. Google does not provide requests to create or update them.               |
| Column breaks, horizontal rules, and auto text |   ❌    |    ❌    |     ✅     |            ❌             | Existing elements are preserved. Google does not provide requests to create them.                                   |
| Document-wide and named style definitions      |   ❌    |    ❌    |     ❌     |            ✅             | Existing definitions are preserved. Applying a named style to a paragraph is supported.                             |
| Named ranges                                   |   ❌    |    ❌    |     ❌     |            ✅             | Named ranges are currently ignored by gdocs-patch.                                                                  |
| Comments                                       |   ❌    |    ❌    |     ❌     |            ❌             | Text edits try to preserve comment anchors. Comments are managed through the Google Drive API instead.              |
| Suggestions                                    |   ❌    |    ❌    |     ❌     |            ❌             | Suggested changes are not currently modeled.                                                                        |
| Document metadata                              |   ❌    |    ❌    |     ❌     |            ⚠️             | IDs and revision information are preserved. Google does not provide Docs requests for changing all metadata.        |

## Google authentication

Enable the Google Docs API in a Google Cloud project, configure its OAuth
consent screen, and create an OAuth client with application type **Desktop
app**. Download its client JSON.

Pass that file explicitly:

```console
uv run gdocs-patch auth login --client-secrets ~/Downloads/client_secret.json
```

Or save it at the default location and omit the option:

```console
mkdir -p ~/.config/gdocs-patch
cp ~/Downloads/client_secret.json ~/.config/gdocs-patch/client_secret.json
uv run gdocs-patch auth login
```

The command prints and opens Google's authorization URL. On a remote or
headless host, open the printed URL in another browser. After authorization,
the browser may fail to connect to localhost; copy its complete callback URL
from the address bar and paste it into the waiting command.

Refreshable user credentials are saved at
`~/.config/gdocs-patch/credentials.json`. Treat this file as a secret.

Sandbox environments can instead provide an automatically updated bearer
token:

```console
export GDOCS_PATCH_BEARER_TOKEN="..."
```

The environment token takes precedence over saved user credentials.

## Optional MCP server

MCP support is optional. A CLI-only installation does not install FastMCP:

```console
uv tool install gdocs-patch
```

Python console entry points are unconditional, so this base install still includes
`gdocs-patch-mcp`. Without the `mcp` extra, invoking it exits cleanly without a
traceback and directs you to install the extra with
`uv tool install 'gdocs-patch[mcp]'`.

Install the `mcp` extra to run the hosted server:

```console
uv tool install 'gdocs-patch[mcp]'
```

The server uses the same Google credentials as the CLI: either the saved
`~/.config/gdocs-patch/credentials.json` file or `GDOCS_PATCH_BEARER_TOKEN`.
It does not provide a Google login endpoint.

Generate and inject a separate token for MCP clients, then start the server:

```console
export GDOCS_PATCH_MCP_TOKEN="$(openssl rand -hex 32)"
gdocs-patch-mcp --host 127.0.0.1 --port 8000
```

The Streamable HTTP endpoint is `http://127.0.0.1:8000/mcp`. Every request must
include `Authorization: Bearer` with the value of `GDOCS_PATCH_MCP_TOKEN`.
The built-in server does not provide TLS. Put it behind an HTTPS reverse proxy
or ingress before exposing it beyond localhost, and inject the token through
your deployment's secret manager.

The server exposes four tools:

- `read_document(document_id, offset=1, limit=null)` returns canonical XHTML;
- `edit_document(document_id, edits, allow_bullet_normalization=false)` applies
  exact XHTML replacements immediately;
- `write_document(document_id, content, allow_bullet_normalization=false)`
  applies a complete target XHTML document immediately; and
- `syntax_help(topic=null, reference=false)` explains the XHTML grammar.

Each successful call returns both human-readable text and typed MCP structured
content. The structured results identify the document and include the XHTML,
replacement count, or syntax help relevant to the tool. Each edit object
contains string `old_text` and `new_text` fields. Syntax topics are `paragraphs`,
`lists`, `tables`, `equations`, and `sections`. Read and syntax help are read-only;
edit and write mutate the Google document during the tool call. Mutations use
Google's required revision ID and are not retried when the document changes
concurrently.

## Development

Install Python 3.14 and synchronize all development dependencies:

```console
uv sync --dev --all-extras
```

Run the test and static-analysis tools:

```console
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
```

Install and run the Git hooks:

```console
uv run pre-commit install
uv run pre-commit run --all-files
```

See [RELEASING.md](RELEASING.md) for package build, versioning, and PyPI
publication instructions.
