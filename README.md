# Google Workspace patch tools

Agent-oriented Google Workspace editing tools, maintained in one uv workspace.
Each product is independently installable and has its own CLI and MCP server.

| Package | Purpose | Documentation |
| --- | --- | --- |
| `gdocs-patch` | Edit Google Docs through XHTML instead of managing document indices | [Docs guide](packages/gdocs-patch/README.md) |
| `gsheets-patch` | Thin native Google Sheets API access, without a new editing language | [Sheets guide](packages/gsheets-patch/README.md) |

Both support Python 3.10+. A Slides product is planned, but not implemented.
The `gdocs-patch` package, commands, and authentication remain unchanged.

## Install

```console
uv tool install gdocs-patch
uv tool install gsheets-patch
```

Install a product's optional `[mcp]` extra to use its Streamable HTTP MCP server:

```console
uv tool install 'gdocs-patch[mcp]'
uv tool install 'gsheets-patch[mcp]'
```

See the individual guides for Google OAuth setup and MCP bearer-token configuration.
The two products store credentials separately.

## Repository layout

```text
packages/
  gdocs-patch/
    pyproject.toml
    src/gdocs_patch/
    tests/
  gsheets-patch/
    pyproject.toml
    src/gsheets_patch/
    tests/
scripts/                # Package smoke checks and release selection
pyproject.toml          # Shared development tools and uv workspace
uv.lock                 # Shared dependency resolution
```

## Development

Use Python 3.14 for development tooling. From the repository root:

```console
uv sync --locked --all-packages --all-extras --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m fixit lint .
uv run pyright
uv run pre-commit install
uv run pre-commit run --all-files
```

Run one product's tests or commands:

```console
uv run pytest packages/gsheets-patch/tests
uv run --package gsheets-patch gsheets-patch schema
uv run --package gdocs-patch gdocs-patch --help
```

Automated tests are offline: no Google credentials or scratch spreadsheet needed.
CI checks both packages on Python 3.10–3.14 and builds each independently.

Build and smoke-test a distribution (including a wheel rebuilt from its sdist):

```console
bash scripts/smoke-package.sh gdocs-patch
bash scripts/smoke-package.sh gsheets-patch
```

See [RELEASING.md](RELEASING.md) for independent versions, package-qualified tags,
and PyPI Trusted Publishing.

## License

MIT
