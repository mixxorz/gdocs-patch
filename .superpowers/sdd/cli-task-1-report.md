# CLI Task 1 Report

## Status

DONE_WITH_CONCERNS: Step 1 is implemented and its focused checks and full test suite pass. The repository-wide `ruff format --check .` command reports a pre-existing formatting issue in the already-committed implementation plan; all changed Python files pass Ruff format, and pre-commit passes.

## Commit

- `66e00de feat: add CLI read command`

## Implementation

- Added `read_document`, which fetches a document, parses the Google response, serializes canonical XHTML, and slices it by one-based line offset and optional line count.
- Added the `read` argparse command and a single common JSON-object stdin decoder.
- Added explicit read input validation for the exact `docId`, `offset`, and `limit` field set, including strict integer checks that reject booleans.
- Kept validation before credential loading/client construction.
- Preserved raw XHTML output with `sys.stdout.write` and the existing concise stderr error convention for input, authentication, and Google API failures.
- Added README usage and pagination/output semantics.
- Preserved `auth login` behavior.

## Files

- Created `gdocs_patch/commands/__init__.py`
- Created `gdocs_patch/commands/read.py`
- Modified `gdocs_patch/cli.py`
- Modified `README.md`
- Created `tests/commands/__init__.py`
- Created `tests/commands/support.py`
- Created `tests/commands/test_read.py`
- Created `tests/test_cli.py`

## RED evidence

Command:

```console
uv run pytest tests/commands/test_read.py tests/test_cli.py -v
```

Result: exit 2 during collection, as expected before production code existed:

```text
E   ModuleNotFoundError: No module named 'gdocs_patch.commands'
collected 3 items / 1 error
```

The complete captured output is in `.superpowers/sdd/cli-task-1-red.txt` (untracked harness evidence).

## GREEN evidence

Command:

```console
uv run pytest tests/commands/test_read.py tests/test_cli.py -v
```

Result:

```text
collected 4 items
4 passed in 0.29s
```

After refactoring/static-check fixes, the same focused test command passed again with `4 passed in 0.26s`.

Focused static checks:

```console
uv run ruff check gdocs_patch/cli.py gdocs_patch/commands/read.py tests/commands tests/test_cli.py
uv run pyright
uv run ruff format --check gdocs_patch/cli.py gdocs_patch/commands tests/commands tests/test_cli.py
```

Results: Ruff check passed, Pyright reported `0 errors, 0 warnings, 0 informations`, and all 7 changed Python files were formatted.

## Full-suite and project verification

Full suite (run once, after focused GREEN):

```console
uv run pytest
```

Result: `185 passed in 0.51s`.

Additional commands and results:

- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — failed only because `docs/superpowers/plans/2026-08-12-cli-document-commands.md` contains an already-committed Python snippet Ruff would reformat; no Task 1 file was implicated.
- `uv run fixit lint .` — 66 files clean.
- `uv run pyright` — 0 errors, warnings, or informations.
- `uv run pre-commit run --all-files` — all six hooks passed.
- `git diff --check` — passed.
- Main checkout verification — still on `main`, with only the two intentional untracked `.documents.get.json` and `.documents.get.xhtml` sample files.

The complete combined output is in `.superpowers/sdd/cli-task-1-verification.txt` (untracked harness evidence).

## Self-review

- Tests are limited exactly to the brief's read happy path and three JSON-boundary cases.
- The fake is a plain HTTP-boundary fake and records document IDs and batch bodies for later slices.
- Camel-case names stay at the JSON boundary; command/Python interfaces use snake case.
- `type(value) is int` prevents JSON booleans from being accepted as pagination integers.
- The only shared helper is the JSON-object decoder; no request classes or field-reader helper layers were introduced.
- The read command pipeline is direct and matches the prescribed parser/serializer composition.
- Unknown field reporting is deterministic if multiple unknown fields are supplied.
- No changes were made outside the feature worktree.

## Concerns

Repository-wide Ruff format is not clean because of an existing code block in the committed CLI implementation plan. I did not modify that out-of-scope plan. Changed Python files, focused checks, the full test suite, and all pre-commit hooks pass.
