# Temporary-Anchor Reconciliation Refactor — Task 1 Report

## Status

Implemented the behavior-preserving reconciliation simplification on `fix/table-structural-reconciliation`. Rows and columns now use one pure `_plan_table_axis_operations(...)` planner. The no-retained-row column path remains dimension-based. No tests were added, and mixed-case expectations were unchanged.

## Baseline

Verified the linked worktree and branch before edits:

- Worktree: `/Users/mixxorz/Projects/gdocs_patch/.worktrees/fix-table-structural-reconciliation`
- Branch: `fix/table-structural-reconciliation`
- Git directory differed from the common Git directory, confirming linked-worktree isolation.

Ran the four required focused tests before implementation:

```text
4 passed in 0.04s
```

## Intentional Failure Evidence

After implementing the planner and before changing expectations, reran the same four tests:

```text
.F.F
2 failed, 2 passed in 0.06s
```

Only these complete-replacement boundary expectations failed:

- `test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor`
- `test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor`

The mixed row and mixed column tests remained green. The failures showed only the intended safe scheduling change: delete non-anchor source index 1, insert target indices 0 and 1, then delete the shifted temporary anchor at index 2.

## Implementation and Expectations

- Added the pure `TableAxisOperation` plan type and `_plan_table_axis_operations(...)` helper.
- Replaced separate complete-row-replacement scheduling with one planner translation loop.
- Replaced separate retained-row and dimension-fallback column operation loops with one planner translation loop.
- Preserved first-retained-row identity matching.
- Preserved dimension-derived column inputs when no row is retained.
- Updated only the two existing complete-replacement hard-coded operation sequences.
- Added no tests and made no mixed-case expectation changes.
- Reviewed the existing design spec; no update was needed because it already specifies the shared temporary-anchor policy and dimension-based fallback.

## Green and Full Verification

Commands and results:

```text
uv run pytest -q <four required focused tests>
4 passed in 0.04s

uv run pytest -q
200 passed in 0.60s

uv run ruff check .
All checks passed!

uv run ruff format --check .
108 files already formatted

uv run fixit lint .
78 files clean

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pre-commit run --all-files
All hooks passed

git diff --check
Exit 0, no output
```

The commit-time pre-commit hooks also passed.

## Files

- `gdocs_patch/compiler/edit_script.py`
- `tests/compiler/test_table_edit_script.py`
- `.superpowers/sdd/table-temporary-anchor-refactor-task-1-report.md`

## Commits

- `e9db0be refactor: share table axis anchor planning`
- Report commit: the commit containing this file.

## Self-Review

The planner has one narrow interface and owns the temporary-anchor scheduling decision. Callers only translate abstract delete/insert axis operations into existing concrete edit classes. No additional abstraction or unrelated cleanup was introduced.

## Concerns

None. No external Google document was accessed or modified. The branch was not merged or pushed, and the worktree is preserved.
