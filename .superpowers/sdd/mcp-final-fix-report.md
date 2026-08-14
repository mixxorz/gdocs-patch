# MCP final whole-branch review fix report

## Scope

Applied the single confirmed documentation finding only. Updated `README.md` in the Optional MCP server section to explain that Python console entry points are unconditional, that a base install still provides `gdocs-patch-mcp`, and that launching it without the `mcp` extra exits cleanly without a traceback and directs the user to:

```console
uv tool install 'gdocs-patch[mcp]'
```

No runtime code, FastMCP statefulness, tests, or unrelated documentation changed.

## Review and coherence

The clarification sits directly after the CLI-only installation command and before the existing MCP-extra installation command. The surrounding flow remains coherent: base installation and missing-extra behavior, MCP-extra installation, credentials, server launch, endpoint authentication, and TLS guidance.

The documented command exactly matches the launcher message in `gdocs_patch/mcp_server/__init__.py`.

## Checks

### `git diff --check`

Exit status: 0. No output.

### `uv run pre-commit run --files README.md`

Exit status: 0.

```text
ruff check...........................................(no files to check)Skipped
ruff format check....................................(no files to check)Skipped
pyright..................................................................Passed
Fixit - lint and apply autofixes.....................(no files to check)Skipped
Detect hardcoded secrets.................................................Passed
```

### README review

Read the complete edited Optional MCP server passage. The existing install and launch instructions remain consistent, and the exact launcher-provided installation command appears in both the clarification and the existing install example.

## Isolation evidence

Before editing:

```text
working directory: /Users/mixxorz/Projects/gdocs_patch/.worktrees/mcp-server
branch: mcp-server
mcp-server HEAD: f844caf6f1600bc95506b229f68cfb6e39980c66
status: clean
main worktree: /Users/mixxorz/Projects/gdocs_patch
main HEAD: 34122637ac486352c6d14e2409550f0dabd49b4b
```

All work was performed in the `mcp-server` worktree. Final post-commit branch and main-ref verification is recorded in the task response.

## Concerns

None. This is a documentation-only change; Python-specific test and formatter hooks correctly had no README files to inspect, while Pyright and the hardcoded-secret check passed through pre-commit.
