# Task 2 Report: Semantic SectionBreak and corrected table edits

## Status

Implemented and committed on branch `exploratory-google-docs`.

Commit: `de3adfd feat: reconcile section break edits`

## Scope completed

- Added semantic edit types:
  - `InsertSectionBreak`
  - `DeleteSectionBreak`
  - `ApplySectionStyle`
- Added required `preceding_boundary` mode to `InsertTable`.
- Exported the new public compiler edit types.
- Reconciled inserted paragraph-boundary/structure pairs for tables and section breaks.
- Generated retained-boundary section-break insertions and deletions at source/target UTF-16 indices.
- Reset paragraph range starts after tables and section breaks.
- Added the explicit writable `SectionStyle` projection, excluding section type and header/footer IDs.
- Rejected retained section-type changes, concrete-to-`UNSET` writable style transitions, and inserted breaks with unset section type.
- Ordered `ApplySectionStyle` with formatting edits after content edits and before text styles.
- Replaced the named existing table insertion test and added only the SectionBreak behavior/error tests required by the brief.
- Updated the existing lowering test's `InsertTable` construction for the required field; no Task 3 lowering behavior was implemented.

## TDD evidence

### RED

After adding the required tests first, ran:

```bash
uv run pytest tests/compiler/test_edit_script.py -k 'section_break or inserts_table_between_existing_paragraphs' -v
```

Result: collection failed as expected because `ApplySectionStyle` did not yet exist/export:

```text
ImportError: cannot import name 'ApplySectionStyle' from 'gdocs_patch.compiler'
collected 0 items / 1 error
```

This demonstrated the new semantic edit API was absent before implementation.

### Intermediate GREEN correction

The first implementation run selected four tests and produced 3 passes / 1 failure. The paragraph-split case emitted unwanted default paragraph/text style edits in addition to `InsertSectionBreak`. The compiler was corrected to treat the boundary created as part of an inserted structural pair as the synthetic retained formatting baseline.

### GREEN

Ran all seven explicitly required focused tests by node ID:

```bash
uv run pytest -v \
  tests/compiler/test_edit_script.py::test_generate_edit_script_inserts_section_break_with_inserted_boundary \
  tests/compiler/test_edit_script.py::test_generate_edit_script_inserts_section_break_after_retained_boundary \
  tests/compiler/test_edit_script.py::test_generate_edit_script_deletes_section_break_after_retained_boundary \
  tests/compiler/test_edit_script.py::test_generate_edit_script_applies_retained_section_style \
  tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_retained_section_type_change \
  tests/compiler/test_edit_script.py::test_generate_edit_script_rejects_clearing_concrete_section_style \
  tests/compiler/test_edit_script.py::test_generate_edit_script_inserts_table_between_existing_paragraphs
```

Result:

```text
7 passed in 0.03s
```

Then ran the brief's edit-script/table command:

```bash
uv run pytest tests/compiler/test_edit_script.py tests/compiler/test_table_edit_script.py -q
```

Result:

```text
21 passed in 0.03s
```

## Full verification before commit

```bash
uv run ruff format --check gdocs_patch tests
uv run ruff check .
uv run pyright
uv run fixit lint .
uv run pytest -q
```

Results:

```text
57 files already formatted
All checks passed!
0 errors, 0 warnings, 0 informations
60 files clean
180 passed in 0.27s
```

Also ran:

```bash
uv run pre-commit run --all-files
```

All configured hooks passed: Ruff check, Ruff format check, Pyright, Fixit, and hardcoded-secret detection. Commit-time hooks passed again.

A direct repository-wide `uv run ruff format --check .` reported that the pre-existing plan Markdown file `docs/superpowers/plans/2026-08-11-section-break-compilation.md` would reformat fenced examples. That file was outside Task 2 and was not modified. The configured pre-commit Ruff format check passed, and all Python source/tests passed the direct format check.

## Files changed

- `gdocs_patch/compiler/edit_script.py`
- `gdocs_patch/compiler/__init__.py`
- `tests/compiler/test_edit_script.py`
- `tests/compiler/test_lowering.py`

`tests/compiler/test_table_edit_script.py` required no constructor update because it contains no `InsertTable` construction.

## Self-review

Reviewed commit `de3adfd` with `git show --check` and inspected the semantic reconciliation paths.

Findings:

- New public edit types and exports match the brief.
- Boundary mode is required rather than defaulted.
- Inserted structure offsets remain target-opcode-relative and source-insertion-based.
- Section style projection contains exactly the requested writable fields.
- Header/footer IDs and `section_type` are excluded from writable style comparison.
- Section style edits remain formatting operations and no lowering support was added.
- No extra tests beyond the brief-required SectionBreak tests, the named replacement table test, and the necessary existing constructor update were introduced.

No blocking review findings.

## Remaining concerns

- Task 3 must lower the new semantic edits and use `preceding_boundary`; this task intentionally does not make them executable Google Docs requests.
- The out-of-scope Markdown formatting discrepancy noted above remains in the repository, while configured pre-commit checks are green.
