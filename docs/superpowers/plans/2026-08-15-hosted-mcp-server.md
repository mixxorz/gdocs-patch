# Hosted MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, bearer-authenticated FastMCP 3.4.4 Streamable HTTP server that exposes the existing document and XHTML syntax operations without changing or burdening the CLI-only installation.

**Architecture:** A dependency-free `gdocs-patch-mcp` launcher lazily imports an optional FastMCP server. The server creates one `GoogleDocsClient` per document tool invocation and delegates directly to the existing command functions; FastMCP owns schema generation, HTTP transport, and MCP dispatch.

**Tech Stack:** Python 3.12+, `uv`, `fastmcp==3.4.4`, FastMCP HTTP transport, existing Google Docs client/commands, Pyright, Ruff, Fixit, pytest, pre-commit.

## Global Constraints

- Keep `fastmcp==3.4.4` in the `mcp` optional extra; do not add it to base dependencies.
- Keep `gdocs-patch --help`, existing CLI commands, and CLI imports free of MCP references.
- Expose MCP only through the separate `gdocs-patch-mcp` executable.
- Serve modern Streamable HTTP at `/mcp`; do not add stdio or legacy SSE support.
- Require a non-empty `GDOCS_PATCH_MCP_TOKEN` and never accept it as a command-line argument.
- Reuse `load_credentials()`, `GoogleDocsClient`, and the existing command functions directly.
- Use `snake_case` for every MCP tool argument.
- Apply edit and write operations immediately; do not add previews, server-side operation state, retries, or Google OAuth routes.
- Do not add automated MCP tests. Use the manual smoke checks in this plan and keep the existing automated suite green.
- Do not add unrelated abstractions or refactor the existing CLI/command layer.

## File Structure

- Modify `pyproject.toml` to declare the `mcp` extra and `gdocs-patch-mcp` entry point.
- Modify `uv.lock` through `uv add`; never edit it manually.
- Create `gdocs_patch/mcp_server/__init__.py` for dependency-free argument parsing, optional-dependency detection, token validation, and startup.
- Create `gdocs_patch/mcp_server/server.py` for FastMCP authentication, server construction, tool wrappers, and tool registration.
- Modify `README.md` with separately scoped MCP installation, deployment, security, and tool documentation.
- Do not create or modify any test file.

---

### Task 1: FastMCP dependency, authenticated server, and launcher

**Files:**
- Modify: `pyproject.toml:1-15`
- Modify: `uv.lock`
- Create: `gdocs_patch/mcp_server/__init__.py`
- Create: `gdocs_patch/mcp_server/server.py`
- Modify: `README.md` after the Google authentication section

**Interfaces:**
- Consumes: `GDOCS_PATCH_MCP_TOKEN` from the process environment.
- Produces: `gdocs_patch.mcp_server.main(argv: Sequence[str] | None = None) -> int`.
- Produces: `create_server(*, token: str) -> FastMCP` and `run_server(*, host: str, port: int, token: str) -> None`.
- Produces: `BearerTokenVerifier(*, token: str)`, a timing-safe FastMCP `TokenVerifier`.
- Produces: a `gdocs-patch-mcp` executable serving HTTP at `/mcp`.

- [ ] **Step 1: Add the exact optional dependency and console entry point**

Run:

```bash
uv add --optional mcp 'fastmcp==3.4.4'
```

Then add the second script without changing the existing one:

```toml
[project.scripts]
gdocs-patch = "gdocs_patch.cli:main"
gdocs-patch-mcp = "gdocs_patch.mcp_server:main"
```

Expected: `pyproject.toml` contains an `mcp` optional dependency with the exact FastMCP pin, and `uv.lock` resolves FastMCP only behind that extra.

- [ ] **Step 2: Create the dependency-free launcher**

Create `gdocs_patch/mcp_server/__init__.py`:

```python
import argparse
import os
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the optional hosted MCP server."""
    parser = argparse.ArgumentParser(
        prog="gdocs-patch-mcp",
        description="Serve gdocs-patch tools over authenticated MCP HTTP.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    try:
        from gdocs_patch.mcp_server.server import run_server
    except ModuleNotFoundError as error:
        if error.name != "fastmcp":
            raise
        print(
            "gdocs-patch-mcp: error: MCP support is not installed. "
            "Install it with: uv tool install 'gdocs-patch[mcp]'",
            file=sys.stderr,
        )
        return 1

    token = os.environ.get("GDOCS_PATCH_MCP_TOKEN")
    if not token:
        print(
            "gdocs-patch-mcp: error: GDOCS_PATCH_MCP_TOKEN must be set.",
            file=sys.stderr,
        )
        return 1

    run_server(host=args.host, port=args.port, token=token)
    return 0
```

The module must not import `fastmcp`, `mcp`, Pydantic, Starlette, or any MCP server module at import time.

- [ ] **Step 3: Create the authenticated empty FastMCP server**

Create `gdocs_patch/mcp_server/server.py`:

```python
import hashlib
import secrets

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier


class BearerTokenVerifier(TokenVerifier):
    """Verify the single bearer token configured for this server."""

    def __init__(self, *, token: str) -> None:
        super().__init__()
        self._token_digest: bytes = hashlib.sha256(token.encode("utf-8")).digest()

    async def verify_token(self, token: str) -> AccessToken | None:
        candidate_digest = hashlib.sha256(token.encode("utf-8")).digest()
        if not secrets.compare_digest(candidate_digest, self._token_digest):
            return None
        return AccessToken(
            token=token,
            client_id="gdocs-patch-mcp",
            scopes=[],
        )


def create_server(*, token: str) -> FastMCP:
    """Create the configured gdocs-patch MCP server."""
    return FastMCP(
        name="gdocs-patch",
        instructions=(
            "Read and update Google Docs through canonical XHTML. Read a document "
            "before editing it, and use syntax_help when XHTML syntax is unclear."
        ),
        auth=BearerTokenVerifier(token=token),
        mask_error_details=True,
        strict_input_validation=True,
    )


def run_server(*, host: str, port: int, token: str) -> None:
    """Serve gdocs-patch using FastMCP's Streamable HTTP transport."""
    server = create_server(token=token)
    server.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
    )
```

Use FastMCP's documented `transport="http"`; in FastMCP 3.4.4 this is the modern Streamable HTTP transport. Do not use `StaticTokenVerifier`, which FastMCP documents as development-only and which stores configured tokens as plain dictionary keys.

- [ ] **Step 4: Document installation, operation, and the complete tool contract**

Insert this standalone section in `README.md` after Google authentication and before the Python client example:

````markdown
## Optional MCP server

MCP support is optional. A CLI-only installation does not install FastMCP:

```console
uv tool install gdocs-patch
```

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

Each edit object contains string `old_text` and `new_text` fields. Syntax topics
are `paragraphs`, `lists`, `tables`, `equations`, and `sections`. Read and syntax
help are read-only; edit and write mutate the Google document during the tool
call. Mutations use Google's required revision ID and are not retried when the
document changes concurrently.
````

- [ ] **Step 5: Verify CLI-only isolation manually**

Run:

```bash
uv sync --dev
uv run python - <<'PY'
import importlib.util

assert importlib.util.find_spec("fastmcp") is None
PY
uv run gdocs-patch --help > .gdocs-patch-help.txt
! rg -i 'mcp' .gdocs-patch-help.txt
uv run gdocs-patch-mcp > .gdocs-patch-mcp.out 2>&1 || true
rg "MCP support is not installed" .gdocs-patch-mcp.out
rm .gdocs-patch-help.txt .gdocs-patch-mcp.out
```

Expected: FastMCP is absent, normal CLI help contains no MCP command, and the optional launcher gives installation guidance without a traceback.

- [ ] **Step 6: Verify FastMCP startup and bearer authentication manually**

Run:

```bash
uv sync --extra mcp --dev
uv run fastmcp version | rg 'FastMCP version:.*3\.4\.4'
TOKEN="$(openssl rand -hex 32)"
GDOCS_PATCH_MCP_TOKEN="$TOKEN" \
  uv run gdocs-patch-mcp --port 8765 > .mcp-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; rm -f .mcp-smoke.log' EXIT
STATUS="$(curl --retry 20 --retry-connrefused --retry-delay 0 \
  -sS -o /dev/null -w '%{http_code}' \
  -X POST http://127.0.0.1:8765/mcp)"
test "$STATUS" = "401"
uv run fastmcp list http://127.0.0.1:8765/mcp --auth "$TOKEN"
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm .mcp-smoke.log
```

Expected: FastMCP reports version 3.4.4, the unauthenticated request returns 401, and the authenticated client connects and reports an empty tool list.

- [ ] **Step 7: Run static checks and commit the setup**

Run:

```bash
uv run ruff check gdocs_patch/mcp_server
uv run ruff format --check gdocs_patch/mcp_server
uv run pyright
uv run fixit lint gdocs_patch/mcp_server
```

Expected: all commands pass.

Commit:

```bash
git add pyproject.toml uv.lock gdocs_patch/mcp_server README.md
git commit -m "feat: add optional authenticated MCP server"
```

---

### Task 2: `read_document` tool

**Files:**
- Modify: `gdocs_patch/mcp_server/server.py`

**Interfaces:**
- Consumes: `create_server(*, token: str) -> FastMCP` from Task 1.
- Consumes: `read_document(*, client: GoogleDocsClient, doc_id: str, offset: int = 1, limit: int | None = None) -> str` from `gdocs_patch.commands`.
- Produces: MCP tool `read_document(*, document_id: str, offset: int = 1, limit: int | None = None) -> str`.

- [ ] **Step 1: Add typed imports and the read wrapper**

Update `gdocs_patch/mcp_server/server.py` imports to include:

```python
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]
from mcp.types import ToolAnnotations
from pydantic import Field

from gdocs_patch.client import AuthenticationError, GoogleDocsClient, load_credentials
from gdocs_patch.commands import read_document as run_read_document
```

Add this function before `create_server`:

```python
def read_document(
    *,
    document_id: str,
    offset: Annotated[int, Field(ge=1)] = 1,
    limit: Annotated[int | None, Field(gt=0)] = None,
) -> str:
    """Read canonical XHTML lines from a Google document."""
    try:
        client = GoogleDocsClient(credentials=load_credentials())
        return run_read_document(
            client=client,
            doc_id=document_id,
            offset=offset,
            limit=limit,
        )
    except (AuthenticationError, GoogleAuthError, HttpError) as error:
        raise ToolError(str(error)) from None
```

The Pydantic constraints preserve the CLI's one-based offset and positive-limit validation without duplicating FastMCP's type validation.

- [ ] **Step 2: Register only the read tool**

Change `create_server` to create a local `server`, register the tool, and return it:

```python
def create_server(*, token: str) -> FastMCP:
    """Create the configured gdocs-patch MCP server."""
    server = FastMCP(
        name="gdocs-patch",
        instructions=(
            "Read and update Google Docs through canonical XHTML. Read a document "
            "before editing it, and use syntax_help when XHTML syntax is unclear."
        ),
        auth=BearerTokenVerifier(token=token),
        mask_error_details=True,
        strict_input_validation=True,
    )
    server.tool(
        title="Read Document",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(read_document)
    return server
```

- [ ] **Step 3: Smoke-check discovery and a real read**

Use a Google document reserved for manual smoke checks:

```bash
: "${GDOCS_PATCH_SMOKE_DOC_ID:?Set GDOCS_PATCH_SMOKE_DOC_ID to a disposable Google document ID}"
TOKEN="$(openssl rand -hex 32)"
GDOCS_PATCH_MCP_TOKEN="$TOKEN" \
  uv run gdocs-patch-mcp --port 8765 > .mcp-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; rm -f .mcp-smoke.log' EXIT
uv run fastmcp list http://127.0.0.1:8765/mcp \
  --auth "$TOKEN" --input-schema
uv run fastmcp call http://127.0.0.1:8765/mcp read_document \
  --input-json "$(jq -n --arg document_id "$GDOCS_PATCH_SMOKE_DOC_ID" \
    '{document_id: $document_id, limit: 3}')" \
  --auth "$TOKEN"
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm .mcp-smoke.log
```

Expected: discovery lists only `read_document` with `document_id`, `offset`, and `limit`; the call returns the first three lines of canonical XHTML.

- [ ] **Step 4: Run static checks and commit the read tool**

Run:

```bash
uv run ruff check gdocs_patch/mcp_server/server.py
uv run ruff format --check gdocs_patch/mcp_server/server.py
uv run pyright
uv run fixit lint gdocs_patch/mcp_server/server.py
```

Expected: all commands pass.

Commit:

```bash
git add gdocs_patch/mcp_server/server.py
git commit -m "feat: expose document reads over MCP"
```

---

### Task 3: `edit_document` tool

**Files:**
- Modify: `gdocs_patch/mcp_server/server.py`

**Interfaces:**
- Consumes: `XhtmlEdit(*, old_text: str, new_text: str)` and `edit_document(*, client: GoogleDocsClient, doc_id: str, edits: Sequence[XhtmlEdit], allow_bullet_normalization: bool = False) -> int` from `gdocs_patch.commands`.
- Produces: MCP tool `edit_document(*, document_id: str, edits: list[XhtmlEdit], allow_bullet_normalization: bool = False) -> str`.

- [ ] **Step 1: Import edit behavior and its expected failures**

Replace the command import in `gdocs_patch/mcp_server/server.py` with:

```python
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
    edit_document as run_edit_document,
    read_document as run_read_document,
)
from gdocs_patch.compiler import UnsupportedTransformation
from gdocs_patch.xhtml import XHTMLParseError
```

FastMCP/Pydantic converts each JSON edit object with `old_text` and `new_text` into the existing `XhtmlEdit` dataclass, so no second edit-input model is needed.

- [ ] **Step 2: Add the edit wrapper with MCP-boundary validation**

Add this function after the read wrapper:

```python
def edit_document(
    *,
    document_id: str,
    edits: list[XhtmlEdit],
    allow_bullet_normalization: bool = False,
) -> str:
    """Apply exact canonical-XHTML replacements to a Google document."""
    if not edits:
        raise ToolError("edits must contain at least one replacement.")
    for edit_index, edit in enumerate(edits):
        if not edit.old_text:
            raise ToolError(
                f"edits[{edit_index}].old_text must not be empty in {document_id}."
            )

    try:
        client = GoogleDocsClient(credentials=load_credentials())
        count = run_edit_document(
            client=client,
            doc_id=document_id,
            edits=edits,
            allow_bullet_normalization=allow_bullet_normalization,
        )
    except (
        XhtmlEditError,
        XHTMLParseError,
        UnsupportedTransformation,
        AuthenticationError,
        GoogleAuthError,
        HttpError,
    ) as error:
        raise ToolError(str(error)) from None

    noun = "block" if count == 1 else "blocks"
    return f"Successfully replaced {count} {noun} in {document_id}."
```

`ToolError` preserves useful expected messages despite `mask_error_details=True`; unexpected exceptions remain masked by FastMCP.

- [ ] **Step 3: Register the mutating, non-idempotent edit tool**

Add this registration in `create_server` after `read_document`:

```python
    server.tool(
        title="Edit Document",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )(edit_document)
```

- [ ] **Step 4: Smoke-check a reversible edit on a disposable document**

Choose unique exact XHTML blocks in a disposable document and export them before running:

```bash
: "${GDOCS_PATCH_SMOKE_DOC_ID:?Set GDOCS_PATCH_SMOKE_DOC_ID}"
: "${GDOCS_PATCH_SMOKE_OLD_TEXT:?Set a unique exact XHTML source block}"
: "${GDOCS_PATCH_SMOKE_NEW_TEXT:?Set its unique replacement block}"
TOKEN="$(openssl rand -hex 32)"
GDOCS_PATCH_MCP_TOKEN="$TOKEN" \
  uv run gdocs-patch-mcp --port 8765 > .mcp-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; rm -f .mcp-smoke.log' EXIT
FORWARD="$(jq -n \
  --arg document_id "$GDOCS_PATCH_SMOKE_DOC_ID" \
  --arg old_text "$GDOCS_PATCH_SMOKE_OLD_TEXT" \
  --arg new_text "$GDOCS_PATCH_SMOKE_NEW_TEXT" \
  '{document_id: $document_id, edits: [{old_text: $old_text, new_text: $new_text}]}')"
REVERSE="$(jq -n \
  --arg document_id "$GDOCS_PATCH_SMOKE_DOC_ID" \
  --arg old_text "$GDOCS_PATCH_SMOKE_NEW_TEXT" \
  --arg new_text "$GDOCS_PATCH_SMOKE_OLD_TEXT" \
  '{document_id: $document_id, edits: [{old_text: $old_text, new_text: $new_text}]}')"
uv run fastmcp call http://127.0.0.1:8765/mcp edit_document \
  --input-json "$FORWARD" --auth "$TOKEN"
uv run fastmcp call http://127.0.0.1:8765/mcp edit_document \
  --input-json "$REVERSE" --auth "$TOKEN"
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm .mcp-smoke.log
```

Expected: both calls report one replaced block, and the second call restores the disposable document.

- [ ] **Step 5: Run static checks and commit the edit tool**

Run:

```bash
uv run ruff check gdocs_patch/mcp_server/server.py
uv run ruff format --check gdocs_patch/mcp_server/server.py
uv run pyright
uv run fixit lint gdocs_patch/mcp_server/server.py
```

Expected: all commands pass.

Commit:

```bash
git add gdocs_patch/mcp_server/server.py
git commit -m "feat: expose exact document edits over MCP"
```

---

### Task 4: `write_document` tool

**Files:**
- Modify: `gdocs_patch/mcp_server/server.py`

**Interfaces:**
- Consumes: `write_document(*, client: GoogleDocsClient, doc_id: str, content: str, allow_bullet_normalization: bool = False) -> None` from `gdocs_patch.commands`.
- Produces: MCP tool `write_document(*, document_id: str, content: str, allow_bullet_normalization: bool = False) -> str`.

- [ ] **Step 1: Import and wrap the full-document write command**

Add `write_document` to the existing command import block:

```python
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
    edit_document as run_edit_document,
    read_document as run_read_document,
    write_document as run_write_document,
)
```

Add this function after the edit wrapper:

```python
def write_document(
    *,
    document_id: str,
    content: str,
    allow_bullet_normalization: bool = False,
) -> str:
    """Apply complete target XHTML to a Google document."""
    try:
        client = GoogleDocsClient(credentials=load_credentials())
        run_write_document(
            client=client,
            doc_id=document_id,
            content=content,
            allow_bullet_normalization=allow_bullet_normalization,
        )
    except (
        XHTMLParseError,
        UnsupportedTransformation,
        AuthenticationError,
        GoogleAuthError,
        HttpError,
    ) as error:
        raise ToolError(str(error)) from None

    return f"Successfully wrote to {document_id}."
```

- [ ] **Step 2: Register the mutating, idempotent write tool**

Add this registration in `create_server` after `edit_document`:

```python
    server.tool(
        title="Write Document",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(write_document)
```

The idempotent hint reflects that applying the same complete target XHTML repeatedly converges on the same document state; it does not imply automatic retries.

- [ ] **Step 3: Smoke-check a no-op full write against freshly read XHTML**

Run against the disposable smoke document:

```bash
: "${GDOCS_PATCH_SMOKE_DOC_ID:?Set GDOCS_PATCH_SMOKE_DOC_ID}"
printf '%s\n' "{\"docId\":\"$GDOCS_PATCH_SMOKE_DOC_ID\"}" \
  | uv run gdocs-patch read > .mcp-smoke-target.xhtml
PAYLOAD="$(jq -n \
  --arg document_id "$GDOCS_PATCH_SMOKE_DOC_ID" \
  --rawfile content .mcp-smoke-target.xhtml \
  '{document_id: $document_id, content: $content}')"
TOKEN="$(openssl rand -hex 32)"
GDOCS_PATCH_MCP_TOKEN="$TOKEN" \
  uv run gdocs-patch-mcp --port 8765 > .mcp-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; rm -f .mcp-smoke.log .mcp-smoke-target.xhtml' EXIT
uv run fastmcp call http://127.0.0.1:8765/mcp write_document \
  --input-json "$PAYLOAD" --auth "$TOKEN"
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm .mcp-smoke.log .mcp-smoke-target.xhtml
```

Expected: the tool reports a successful write, and the freshly read target produces no document-content change.

- [ ] **Step 4: Run static checks and commit the write tool**

Run:

```bash
uv run ruff check gdocs_patch/mcp_server/server.py
uv run ruff format --check gdocs_patch/mcp_server/server.py
uv run pyright
uv run fixit lint gdocs_patch/mcp_server/server.py
```

Expected: all commands pass.

Commit:

```bash
git add gdocs_patch/mcp_server/server.py
git commit -m "feat: expose complete document writes over MCP"
```

---

### Task 5: `syntax_help` tool and final verification

**Files:**
- Modify: `gdocs_patch/mcp_server/server.py`

**Interfaces:**
- Consumes: `describe_syntax(topic: str | None = None, *, reference: bool = False) -> str` from `gdocs_patch.commands`.
- Produces: MCP tool `syntax_help(*, topic: Literal["paragraphs", "lists", "tables", "equations", "sections"] | None = None, reference: bool = False) -> str`.
- Completes: the four-tool MCP server described in `docs/superpowers/specs/2026-08-15-hosted-mcp-server-design.md`.

- [ ] **Step 1: Add the syntax topic type and command import**

Change the typing import to:

```python
from typing import Annotated, Literal
```

Add `describe_syntax` to the command import block:

```python
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
    describe_syntax,
    edit_document as run_edit_document,
    read_document as run_read_document,
    write_document as run_write_document,
)
```

- [ ] **Step 2: Add the credential-free syntax wrapper**

Add this function after the write wrapper:

```python
def syntax_help(
    *,
    topic: Literal[
        "paragraphs",
        "lists",
        "tables",
        "equations",
        "sections",
    ]
    | None = None,
    reference: bool = False,
) -> str:
    """Explain the canonical XHTML syntax accepted by gdocs-patch."""
    return describe_syntax(topic, reference=reference)
```

Do not construct a Google client in this tool.

- [ ] **Step 3: Register the closed-world, read-only syntax tool**

Add this registration in `create_server` after `write_document`:

```python
    server.tool(
        title="Syntax Help",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )(syntax_help)
```

- [ ] **Step 4: Smoke-check syntax help and the final four-tool listing**

Run:

```bash
TOKEN="$(openssl rand -hex 32)"
GDOCS_PATCH_MCP_TOKEN="$TOKEN" \
  uv run gdocs-patch-mcp --port 8765 > .mcp-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; rm -f .mcp-smoke.log .mcp-tools.json' EXIT
uv run fastmcp list http://127.0.0.1:8765/mcp \
  --auth "$TOKEN" --input-schema --json > .mcp-tools.json
uv run fastmcp call http://127.0.0.1:8765/mcp syntax_help \
  topic=tables reference=true --auth "$TOKEN"
rg 'read_document' .mcp-tools.json
rg 'edit_document' .mcp-tools.json
rg 'write_document' .mcp-tools.json
rg 'syntax_help' .mcp-tools.json
jq -e '
  [.tools[].name] | sort ==
  ["edit_document", "read_document", "syntax_help", "write_document"]
' .mcp-tools.json
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm .mcp-smoke.log .mcp-tools.json
```

Expected: syntax help returns the detailed table XHTML reference, and discovery contains exactly the four designed tool names.

- [ ] **Step 5: Run the complete project verification suite with the optional extra installed**

Run:

```bash
uv sync --extra mcp --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: 196 existing tests pass, Ruff reports no lint or formatting errors, Fixit reports clean files, Pyright reports zero errors, and every pre-commit hook passes. The test count may increase only if unrelated upstream changes have landed; this feature itself adds no tests.

- [ ] **Step 6: Reconfirm the base installation remains MCP-free**

Run:

```bash
uv sync --dev
uv run python - <<'PY'
import importlib.util

assert importlib.util.find_spec("fastmcp") is None
PY
uv run gdocs-patch --help > .gdocs-patch-help.txt
! rg -i 'mcp' .gdocs-patch-help.txt
rm .gdocs-patch-help.txt
uv sync --extra mcp --dev
```

Expected: the base environment contains no FastMCP module, normal CLI help remains unchanged, and the final command restores the development environment required by Pyright and pre-commit.

- [ ] **Step 7: Commit the syntax tool and completed MCP server**

```bash
git add gdocs_patch/mcp_server/server.py
git commit -m "feat: expose XHTML syntax help over MCP"
```

- [ ] **Step 8: Review the branch contents**

Run:

```bash
git status --short
git log --oneline --decorate main..HEAD
git diff --stat main...HEAD
git diff --check main...HEAD
```

Expected: the worktree is clean; the branch contains the design commit plus five focused implementation commits; only the optional packaging, MCP server package, lockfile, and README changed after the design; and the complete diff has no whitespace errors.
