# gdocs-patch

Efficient Google Doc editing for agents

## Overview

When you ask an agent to edit a Google Doc, they would typically need to
assemble Google Docs API requests manually. This involves finding the right order
of operations, managing document indices, and keeping track of styles. It is all
quite error-prone and could lead to data loss if the agent makes a mistake.

gdocs-patch is a CLI and MCP that allows agents to efficiently edit Google
documents by representing documents as XHTML and allowing the agent to make
targeted edits, just like editing a normal file locally.

## Install

Install the CLI with [uv](https://docs.astral.sh/uv/):

```console
uv tool install gdocs-patch
```

Alternatively, install it with pip:

```console
pip install gdocs-patch
```

gdocs-patch supports Python 3.10 and newer.

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
locally, and calls `write` to apply the edits to the Google Doc. Alternatively,
agents can call `edit` to make targeted replacements without a local copy.

## Authenticating with Google

You need to give the tool access to the Google Docs API. To do this, create a
Google Cloud project, enable the Google Docs API in the project, configure its
OAuth consent screen, and create an OAuth client with application type **Desktop
app**. Download its client JSON and save it in
`~/.config/gdocs-patch/client_secret.json`:

```console
mkdir -p ~/.config/gdocs-patch
cp ~/Downloads/client_secret.json ~/.config/gdocs-patch/client_secret.json
```

The `client_secret.json` file allows `gdocs-patch` to log you in via OAuth.

```console
gdocs-patch auth login
```

This command opens the OAuth authorization screen. Authorize the app. Once done,
`gdocs-patch` should say you're good to go.

If you need to run the tool non-interactively, you can copy the OAuth
authorization URL from the terminal and paste it into your local browser. After
finishing authorization, copy the complete callback URL from your browser's
address bar and paste it back into the terminal.

## MCP server

A Streamable HTTP MCP server is also available that exposes the `read`, `edit`,
and `write` commands over MCP. To use it, install `gdocs-patch[mcp]`:

```console
uv tool install 'gdocs-patch[mcp]'
```

The server uses the same Google credentials as the CLI.

The MCP server is secured via a static Bearer token. Generate a token and set it
to the `GDOCS_PATCH_MCP_TOKEN` environment variable. Then start the server with
`gdocs-patch-mcp`:

```console
export GDOCS_PATCH_MCP_TOKEN="$(openssl rand -hex 32)"
gdocs-patch-mcp --host 127.0.0.1 --port 8000
```

Every request must include `Authorization: Bearer` with the value of
`GDOCS_PATCH_MCP_TOKEN`. There's no built-in TLS, though, so you'd still need
your own reverse proxy and potentially more security if you want to expose the
MCP server over the open internet.

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

## License

MIT
