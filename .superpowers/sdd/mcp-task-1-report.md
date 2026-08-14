# Task 1 Report: FastMCP dependency, authenticated server, and launcher

## Status

DONE

## Implementation

- Added the exact optional dependency `fastmcp==3.4.4` under the `mcp` extra and refreshed `uv.lock`; the lock records FastMCP with `extra == 'mcp'`.
- Added the `gdocs-patch-mcp = "gdocs_patch.mcp_server:main"` console script without changing the existing CLI entry point.
- Added a dependency-free launcher in `gdocs_patch/mcp_server/__init__.py` with host/port parsing, port validation, lazy optional dependency loading, missing-extra guidance, token validation, and server dispatch.
- Added `BearerTokenVerifier`, `create_server`, and `run_server` in `gdocs_patch/mcp_server/server.py`. Tokens are SHA-256 digested and compared with `secrets.compare_digest`; the server uses FastMCP Streamable HTTP at `/mcp`.
- Added the required optional MCP installation, operation, authentication, TLS, and future tool-contract documentation to `README.md` after Google authentication.
- Added a targeted Fixit suppression to the required lazy import because the repository's `NoInlineImport` codemod conflicts with the launcher's required CLI-only dependency isolation.
- Added or modified no automated test files, as required.

## Files changed

- `README.md`
- `pyproject.toml`
- `uv.lock`
- `gdocs_patch/mcp_server/__init__.py` (new)
- `gdocs_patch/mcp_server/server.py` (new)

This report was written to `.superpowers/sdd/mcp-task-1-report.md`. It is tracked separately from the implementation commit.

## Commands and results

### Baseline and isolation

```console
pwd
git branch --show-current
git status --short
uv run pytest
```

Result: working directory was `/Users/mixxorz/Projects/gdocs_patch/.worktrees/mcp-server`, branch was `mcp-server`, status was clean, and `196 passed in 0.61s`.

Worktree metadata check:

```console
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
```

Result: `GIT_DIR=/Users/mixxorz/Projects/gdocs_patch/.git/worktrees/mcp-server` and `GIT_COMMON=/Users/mixxorz/Projects/gdocs_patch/.git`, confirming a linked worktree.

### Dependency update

```console
uv add --optional mcp 'fastmcp==3.4.4'
```

Result: exit 0; FastMCP 3.4.4 resolved and `pyproject.toml`/`uv.lock` updated.

### CLI-only isolation smoke check

Ran the task brief's commands verbatim:

```console
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

Result: exit 0. FastMCP was absent, normal CLI help contained no MCP text, and the launcher printed:

```text
gdocs-patch-mcp: error: MCP support is not installed. Install it with: uv tool install 'gdocs-patch[mcp]'
```

### FastMCP startup and authentication smoke check

Ran the task brief's server smoke sequence using port 8765.

Results:

```text
FastMCP version: 3.4.4
Unauthenticated HTTP status: 401
No tools found.
```

The initial curl connection attempt was refused while the retry loop waited for startup, then succeeded with HTTP 401 as expected. The authenticated FastMCP client connected and reported the expected empty tool list. Temporary smoke files were removed and the server process was stopped.

### Targeted static checks

```console
uv run ruff check gdocs_patch/mcp_server
uv run ruff format --check gdocs_patch/mcp_server
uv run pyright
uv run fixit lint gdocs_patch/mcp_server
git diff --check
```

Results: Ruff check passed; 2 files already formatted; Pyright reported 0 errors, 0 warnings, and 0 informations; Fixit reported 2 files clean; diff check passed.

### Full project checks

```console
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
git diff --check
```

Results: 196 tests passed; Ruff check passed; 105 files already formatted; Fixit reported 78 files clean; Pyright reported 0 errors, 0 warnings, and 0 informations; all five pre-commit hooks passed (Ruff check, Ruff format, Pyright, Fixit, hardcoded-secret detection); diff check passed.

### Test-file constraint

```console
git diff --name-only -- tests
```

Result: no output; no test files changed.

## Branch-isolation checks

`git branch --show-current` was run before implementation, after dependency changes, after CLI-only smoke checks, during static verification, immediately before commit, and immediately after commit. Every result was `mcp-server`.

`git status --short` was checked throughout. Before commit it showed only the five intended implementation paths. Immediately after commit it was clean. No command switched, reset, modified, or committed in main/master or `/Users/mixxorz/Projects/gdocs_patch`.

## Commit

```text
23bc5cfa590e476994a674866d5f5ad32345757e feat: add optional authenticated MCP server
```

Pre-commit hooks all passed during the implementation commit. The report is committed separately with subject `docs: add Task 1 implementation report` so the required final worktree state is committed.

## Self-review

- Compared the launcher, server configuration, exact dependency pin, script entry point, README placement/content, and smoke commands against every brief step.
- Confirmed `gdocs_patch.mcp_server` does not import FastMCP, MCP, Pydantic, Starlette, or the MCP server module at module import time.
- Confirmed the token is not retained as plaintext by the verifier; only its SHA-256 digest is retained, and candidate comparison is timing-safe.
- Confirmed the endpoint uses `transport="http"` and `path="/mcp"`.
- Confirmed lockfile metadata gates FastMCP behind the `mcp` extra.
- Confirmed no test files were added or modified.
- Reviewed the final diff and ran `git diff --check`.

## Concerns

None. The README describes the complete four-tool contract required by this setup task, while this task intentionally creates an authenticated empty server; tool registration belongs to subsequent tasks.

## Controller follow-up

The original report was moved to this MCP-specific path after commit `8f0c9a4` unintentionally replaced a historical report at the generic path. `.superpowers/sdd/task-1-report.md` was restored byte-for-byte from base commit `36aecce460ba3d7d0e28faf4c9f936c319a2f421`.

Verification confirmed the restored file's Git blob hash is `5eafca20c50bf3b6c6f1f7c48a23999f7d6da8be`, matching the base commit; the active branch is `mcp-server`; and `main` remains at `34122637ac486352c6d14e2409550f0dabd49b4b` (`3412263`). No production files were changed by this follow-up.
