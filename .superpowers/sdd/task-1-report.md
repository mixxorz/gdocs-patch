# Task 1 Report: OpaqueUnit

## Status

DONE_WITH_CONCERNS

## Commits

- `fab890e45ccb6ab26fc933cc451c3230ca841832` — `feat: preserve opaque content during compilation`
- The report itself is committed separately after this file is written.

## Files changed

- `gdocs_patch/compiler/content_stream.py`
- `gdocs_patch/compiler/document.py`
- `gdocs_patch/compiler/edit_script.py`
- `gdocs_patch/compiler/__init__.py`
- `tests/compiler/test_document.py`
- `tests/compiler/test_edit_script.py`
- `.superpowers/sdd/task-1-report.md` (this report)

## Implementation summary

- Added exported `OpaqueUnit(key, width, is_inline)` with width-preserving UTF-16 behavior and key-based stream comparison.
- Normalized unsupported paragraph elements as inline opaque units and unsupported structural nodes as single block opaque units.
- Limited generic normalization recursion to `Body`, `Segment`, and `TableCell`.
- Retained equal opaque keys, included opaque widths in source deletion indices, rejected opaque insertions/replacements, treated inline opaque units as paragraph content, reset paragraph tracking after block opaque units, and skipped retained opaque units during formatting.

## TDD red evidence

### Normalization RED

Command:

```bash
uv run pytest tests/compiler/test_document.py::test_normalize_tree_normalizes_kitchen_sink_body_in_document_order -q
```

Output before implementation (exit 4):

```text
ERROR: found no collectors for .../tests/compiler/test_document.py::test_normalize_tree_normalizes_kitchen_sink_body_in_document_order
ImportError: cannot import name 'OpaqueUnit' from 'gdocs_patch.compiler'
1 error in 0.05s
```

This was the expected missing-export/implementation failure.

### Edit-script RED

Command:

```bash
uv run pytest tests/compiler/test_edit_script.py::test_generate_edit_script_preserves_and_deletes_equations tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_equation_insertion -q
```

Output before reconciliation implementation (exit 1):

```text
F.                                                                       [100%]
FAILED tests/compiler/test_edit_script.py::test_generate_edit_script_preserves_and_deletes_equations
NotImplementedError: OpaqueUnit
1 failed, 1 passed in 0.08s
```

The insertion assertion already reached the generic unsupported-content error containing `OpaqueUnit`; the retained opaque formatting path produced the expected missing-feature failure.

## Green and verification evidence

Focused document GREEN:

```bash
uv run pytest tests/compiler/test_document.py::test_normalize_tree_normalizes_kitchen_sink_body_in_document_order -q
```

```text
.                                                                        [100%]
1 passed in 0.04s
```

Required compiler test files:

```bash
uv run pytest tests/compiler/test_document.py tests/compiler/test_edit_script.py -q
```

```text
....................                                                     [100%]
20 passed in 0.06s
```

Final quality gate:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check gdocs_patch tests
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
git diff --check
```

Outputs:

```text
194 passed in 0.60s
All checks passed!
73 files already formatted
🧼 76 files clean 🧼
0 errors, 0 warnings, 0 informations
ruff check...............................................................Passed
ruff format check........................................................Passed
pyright..................................................................Passed
Fixit - lint and apply autofixes.........................................Passed
Detect hardcoded secrets.................................................Passed
```

`git diff --check` produced no output and exited successfully.

The commit hook reran Ruff, Pyright, Fixit, and gitleaks; all passed.

## Self-review

- Reviewed the complete six-file implementation diff and ran `git diff --check`.
- Confirmed changes are limited to the brief's production/test files plus this required report.
- Confirmed opaque identity comparison uses only the opaque key while width remains available for UTF-16 indexing.
- Confirmed unsupported containers become one opaque unit rather than exposing recursively traversed children.
- Confirmed target opaque rejection occurs before edit generation, preventing partial scripts.
- Confirmed no extra tests were added; only the two existing tests named by the brief were expanded.
- Kept implementation local to existing compiler abstractions without adding unnecessary helper layers.

## Concerns

- A repository-wide `uv run ruff format --check .` also checks the pre-existing plan file `docs/superpowers/plans/2026-08-13-page-break-opaque-unit-compilation.md`, which Ruff reports would be reformatted. It was outside Task 1's listed files and was intentionally not modified. Source/tests formatting and the repository pre-commit suite pass.
- The required opaque key resembles a generic API key to gitleaks when written as one literal. The assertion carries `# gitleaks:allow` so the required hard-coded value can remain while commit hooks pass.
