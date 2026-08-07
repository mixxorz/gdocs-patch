# Task 1 Report: Public XHTML API and Document/Tab Envelope

## Status

DONE

## Implementation

- Added the public `gdocs_patch.xhtml` API with `serialize_document`, `deserialize_document`, and `XHTMLParseError`.
- Added XHTML and gdocs namespace constants/name helpers, strict scalar parsers, attribute and child validation, path-qualified parse errors, whitespace checks, and span-safe two-space XML indentation.
- Added deterministic document and recursive tab-envelope encoding with canonical attribute order, namespace registration, UTF-8 XML declaration, Unicode output, and exactly one trailing newline.
- Added document and recursive tab-envelope decoding with required declaration/root/body validation, malformed XML wrapping, exact namespace rejection, unknown syntax rejection, optional-field `UNSET` preservation, nesting-level defaulting, and empty child-list reconstruction.
- Added extension points for later `DocumentTab` and structural-sequence tasks; set `Tab.content` is rejected until those tasks implement it.

## Files

- `gdocs_patch/xhtml/__init__.py`
- `gdocs_patch/xhtml/base.py`
- `gdocs_patch/xhtml/encoder.py`
- `gdocs_patch/xhtml/decoder.py`
- `tests/xhtml/__init__.py`
- `tests/xhtml/test_document.py`
- `.superpowers/sdd/task-1-report.md`

## TDD RED

Command:

```console
uv run pytest tests/xhtml/test_document.py -v
```

Result: exit 2 during collection, 0 tests collected and 1 error.

Key output:

```text
E   ModuleNotFoundError: No module named 'gdocs_patch.xhtml'
ERROR tests/xhtml/test_document.py
```

Reason: expected failure because the required public XHTML package/API did not yet exist. This demonstrated that the new test exercised the missing feature rather than passing against existing behavior.

## GREEN and Full-Suite Verification

Focused GREEN:

```console
uv run pytest tests/xhtml/test_document.py -v
```

Result: `4 passed in 0.01s`.

Full suite:

```console
uv run pytest -q
```

Result: `104 passed in 0.17s` (100 baseline plus 4 Task 1 tests).

Quality checks:

```console
uv run ruff check gdocs_patch tests
uv run ruff format --check gdocs_patch tests
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Results:

- Ruff lint: all checks passed.
- Ruff format: 45 Python files already formatted.
- Fixit: 48 files clean.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Pre-commit: Ruff check, Ruff format, Pyright, Fixit, and gitleaks all passed.

## Self-Review

- Re-read the Task 1 brief and checked every required file, public export, envelope behavior, validation case, helper category, formatting requirement, and future extension point.
- Confirmed exact expected XML output, including escaping, namespace prefixes, canonical attribute insertion, indentation, self-closing child tab, declaration, Unicode emoji, and trailing newline.
- Confirmed decoder validation rejects malformed XML, wrong gdocs namespace usage, duplicate body, unknown attributes/children, non-whitespace structural text, duplicate child wrappers, and invalid scalar/constants with path context.
- Confirmed absent optional fields decode to `UNSET`, omitted nesting level decodes to `0`, and omitted child tabs decode to `[]`.
- Confirmed only the requested worktree paths were changed and no external reference JSON was accessed or modified.

## Commits

- `89aa759 feat: add XHTML document envelope codec`
- The report itself is committed separately after this entry so it can record the implementation commit SHA; its SHA is included in the final response.

## Concerns

- No Task 1 implementation concerns.
- A literal `uv run ruff format --check .` also examines Python snippets embedded in pre-existing committed Markdown and reports those docs as unformatted. The Python source/test scope and the repository's actual pre-commit Ruff format hook both pass; the committed spec and plan were intentionally not modified.
