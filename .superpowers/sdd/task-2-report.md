# Task 2 Report: Page Break Handling

## Status

Implemented and committed Task 2 page-break normalization, reconciliation, insertion, formatting, export, and Google request lowering. The requested live round-trip check was **not performed** and is handed to the main agent.

## Commits

- `c2a0c76 feat: compile page break edits`
- Report commit: recorded separately after this report is committed.

## Files changed

- `gdocs_patch/compiler/content_stream.py`
- `gdocs_patch/compiler/document.py`
- `gdocs_patch/compiler/edit_script.py`
- `gdocs_patch/compiler/lowering.py`
- `gdocs_patch/compiler/__init__.py`
- `tests/compiler/test_document.py`
- `tests/compiler/test_edit_script.py`
- `tests/compiler/test_lowering.py`
- `.superpowers/sdd/task-2-report.md` (report-only follow-up commit)

## Implementation

- Added exported `PageBreakUnit` with text style and UTF-16 width 1.
- Added stable page-break comparison values.
- Normalized model `PageBreak` explicitly before the Task 1 opaque fallback.
- Added exported `InsertPageBreak` edit generation at source-coordinate insertion offsets.
- Treated page breaks as inline paragraph content and generated text-style edits.
- Lowered `InsertPageBreak` to `insertPageBreak` with tab/segment context.
- Updated only the existing behavior tests named by the brief; no test functions were added.

## TDD red evidence

### Normalization and edit script

Command:

```bash
uv run pytest tests/compiler/test_document.py tests/compiler/test_edit_script.py -q
```

Observed expected collection failures before implementation:

```text
ImportError: cannot import name 'PageBreakUnit' from 'gdocs_patch.compiler'
ImportError: cannot import name 'InsertPageBreak' from 'gdocs_patch.compiler'
ERROR tests/compiler/test_document.py
ERROR tests/compiler/test_edit_script.py
2 errors in 0.17s
```

### Lowering

Command:

```bash
uv run pytest tests/compiler/test_lowering.py::test_lowers_content_paragraph_and_bullet_edits -q
```

Observed expected failure before lowering implementation:

```text
NotImplementedError: InsertPageBreak
1 failed in 0.07s
```

## Green verification

Command:

```bash
uv run pytest tests/compiler/test_document.py tests/compiler/test_edit_script.py -q
```

Output:

```text
....................                                                     [100%]
20 passed in 0.07s
```

Command:

```bash
uv run pytest tests/compiler/test_lowering.py tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -q
```

Output:

```text
.....                                                                    [100%]
5 passed in 0.06s
```

Final repeated affected-test output:

```text
....................                                                     [100%]
20 passed in 0.04s
```

## Full verification

Commands and final outputs:

```bash
uv run pytest -q
```

```text
........................................................................ [ 37%]
........................................................................ [ 74%]
..................................................                       [100%]
194 passed in 0.64s
```

```bash
uv run ruff check .
```

```text
All checks passed!
```

```bash
uv run ruff format --check .
```

```text
unformatted: File would be reformatted
  --> docs/superpowers/plans/2026-08-13-page-break-opaque-unit-compilation.md:47:24
...
1 file would be reformatted, 100 files already formatted
```

This remaining failure is in a pre-existing committed planning document outside the Task 2 file list. Task 2's changed Python files pass Ruff's format check through pre-commit. It was intentionally not modified to keep this task focused on the exact required files.

```bash
uv run fixit lint .
```

```text
🧼 76 files clean 🧼
```

```bash
uv run pyright
```

```text
0 errors, 0 warnings, 0 informations
```

```bash
uv run pre-commit run --all-files
```

```text
ruff check...............................................................Passed
ruff format check........................................................Passed
pyright..................................................................Passed
Fixit - lint and apply autofixes.........................................Passed
Detect hardcoded secrets.................................................Passed
```

```bash
git diff --check
```

```text
(no output; exit 0)
```

The feature commit's commit-time hooks also all passed.

## Self-review

Reviewed the complete 381-line diff against every brief step and existing compiler patterns.

- Confirmed `PageBreak` normalization precedes the opaque fallback without changing fallback behavior.
- Confirmed comparison ignores style while preserving first-class page-break identity.
- Confirmed insertion indices use the same source insertion plus target-range UTF-16 offset convention as structural inserts.
- Confirmed retained and deleted page breaks reconcile by one-unit widths.
- Confirmed inserted and changed page-break styles use target coordinates.
- Confirmed lowering preserves tab/segment context via the existing context mapping.
- Confirmed public exports include both new interfaces.
- Confirmed no extra test functions or unrelated production changes were introduced.
- No correctness issue was found in the Task 2 diff.

Pi did not provide a subagent tool, so the requested code-review workflow was performed as an in-session self-review rather than delegated review.

## Concerns

- The exact repository-wide `uv run ruff format --check .` command remains red solely because of the pre-existing committed Markdown plan file noted above; Task 2 files and pre-commit formatting pass.
- The live Google Docs write/read round-trip remains unverified by design.

## Live-check handoff

Step 7 was deliberately skipped per instruction. The main agent must perform the live round-trip against document `1p0HNaILtDeJ-UH_tbi_KX7IKG2o7KW3IyIdG27XbeYU` and compare the structure around `Custom build` through `Open question` using the brief's acceptance criteria.

---

## Final-review fixes (2026-08-12)

### Status and design

Implemented all confirmed final-review findings. The selected minimal design keeps provider behavior at the lowering boundary: every `InsertPageBreak(N)` becomes `insertPageBreak(N)` followed by `deleteContentRange(N+1, N+2)`. Insertion eligibility remains in `generate_edit_script`, using the existing table flag plus one new `inside_non_body_segment` context flag. `compile_document` sets that flag with `dataclasses.replace` for headers, footers, and footnotes, avoiding duplicate stream scans. Alternatives rejected were compensating widths in edit generation (which would leak provider behavior into the compiler abstraction) and passing segment IDs into page-break lowering (invalid per the discovery contract).

### TDD red evidence

Updated existing test functions only; no test function was added.

Exact command:

```bash
uv run pytest tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_equation_insertion tests/compiler/test_lowering.py::test_lowers_content_paragraph_and_bullet_edits tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -q
```

Expected result before implementation:

```text
FAILED tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_equation_insertion
FAILED tests/compiler/test_lowering.py::test_lowers_content_paragraph_and_bullet_edits
FAILED tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch
3 failed in 0.12s
```

The failures respectively showed missing table-context rejection and missing automatic-newline deletion in direct lowering and document compilation. After implementation, an initial run exposed a test import error (`NameError: EditScriptContext is not defined`); adding the missing public import produced the intended green run.

### Affected green evidence

Exact command:

```bash
uv run pytest tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_equation_insertion tests/compiler/test_lowering.py::test_lowers_content_paragraph_and_bullet_edits tests/compiler/test_document.py::test_compile_document_lowers_every_supported_edit_in_one_batch -q
```

Result:

```text
...                                                                      [100%]
3 passed in 0.07s
```

Exact broader affected command and result:

```bash
uv run pytest tests/compiler/test_edit_script.py tests/compiler/test_lowering.py tests/compiler/test_document.py -q
```

```text
........................                                                 [100%]
24 passed in 0.06s
```

### Full verification

```bash
uv run pytest -q
# 194 passed in 0.59s

uv run ruff check .
# All checks passed!

uv run ruff format --check .
# 101 files already formatted

uv run fixit lint .
# 🧼 76 files clean 🧼

uv run pyright
# 0 errors, 0 warnings, 0 informations

uv run pre-commit run --all-files
# ruff check Passed; ruff format check Passed; pyright Passed; Fixit Passed; Detect hardcoded secrets Passed

git diff --check
# no output; exit 0
```

Commit-time pre-commit hooks also passed with the same five successful checks.

### Files

- `gdocs_patch/compiler/lowering.py`
- `gdocs_patch/compiler/edit_script.py`
- `gdocs_patch/compiler/document.py`
- `tests/compiler/test_lowering.py`
- `tests/compiler/test_edit_script.py`
- `tests/compiler/test_document.py`
- `.superpowers/sdd/task-2-report.md`

### Commits

- `8471a31 fix: enforce page break insertion semantics`
- Report follow-up commit: `docs: report final page break review fixes`

### Self-review

- Confirmed page-break lowering preserves `tabId`, omits `segmentId`, and immediately deletes exactly `N+1..N+2`.
- Confirmed table and non-body checks apply only when a target page break is inserted or replaces content; retained page breaks remain legal and retain style updates.
- Confirmed all three segment categories share the context-based rejection path and `compile_document` performs no stream scan.
- Confirmed the bullet/style alignment comment now explicitly covers page breaks and inline opaque units.
- Confirmed only existing tests were extended.

### Concerns

None. The supplied live probe resolves the prior provider-behavior uncertainty; this change does not itself repeat the live API probe.
