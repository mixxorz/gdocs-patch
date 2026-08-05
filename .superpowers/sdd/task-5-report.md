# Task 5 Report: Table parsers and recursive cell content

## Status

Implemented all six table parsers on branch `feature-google-docs-parser` in the dedicated worktree and attached them through `gdocs_patch.parsers`.

## Changes

- Created `gdocs_patch/parsers/table.py` with:
  - `TableCellBorderParser`
  - `TableCellStyleParser`
  - `TableCellParser`
  - `TableRowParser`
  - `TableColumnParser`
  - `TableParser`
- Modified `gdocs_patch/parsers/__init__.py` to load and attach table parsers.
- Created `tests/parsers/test_table.py` with six direct behavior-only happy-path cases.
- Implemented recursive table-cell structural dispatch inline for exactly one of `paragraph`, `sectionBreak`, `table`, or `tableOfContents`; no shared structural parser/helper was introduced.
- Ignored source indices, counts, and suggestion metadata as required.
- Preserved strict literal parsing, `UNSET`, proto defaults, empty-list defaults, optional-color normalization, and constructor invariant errors wrapped at the parsed object path.

## TDD evidence

### RED

Command:

```bash
uv run pytest tests/parsers/test_table.py -v
```

Result: expected failure, exit 1. All 6 tests failed with `AttributeError` because each table model lacked its attached `gdoc_parser`.

### GREEN

Command:

```bash
uv run pytest tests/parsers/test_table.py tests/parsers/test_paragraph.py -v
```

Result: exit 0, `31 passed`.

The six new tests prove:

1. Border color, width, and dash style mapping.
2. Cell style spans, transparent background, four distinct borders, four padding dimensions, and content alignment.
3. Recursive real paragraph parsing in a cell plus ignored index/suggestion metadata.
4. Two row cells and complete row style plus ignored index/suggestion metadata.
5. Fixed-width column parsing.
6. Table rows and column properties plus ignored numeric row/column counts.

## Verification

Required focused checks:

```bash
uv run pytest tests/parsers/test_table.py tests/parsers/test_paragraph.py -v
uv run ruff check gdocs_patch/parsers/table.py tests/parsers/test_table.py
uv run ruff format --check gdocs_patch/parsers/table.py tests/parsers/test_table.py
uv run pyright
```

Results: 31 passed; Ruff lint passed; both files formatted; Pyright reported 0 errors, 0 warnings.

Repository checks:

```bash
uv run pytest
uv run ruff check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
test "$(git branch --show-current)" = "feature-google-docs-parser"
git diff --check
```

Results: 58 passed; Ruff lint passed; Fixit reported 26 files clean; Pyright reported 0 errors; every pre-commit hook passed; branch assertion and whitespace check passed.

A direct repository-wide `uv run ruff format --check .` exits 1 only for two pre-existing documentation code blocks:

- `docs/superpowers/plans/2026-08-05-google-docs-parser.md`
- `docs/superpowers/specs/2026-08-05-google-docs-parser-design.md`

Those files were not changed by Task 5. The required focused format check and the repository's pre-commit Ruff format hook both pass.

## Self-review

- Compared every brief mapping against implementation and tests.
- Confirmed all six parsers are attached.
- Confirmed structural dispatch is duplicated inline in `TableCellParser`, exact-one, and has no shared `StructuralElementParser` or helper.
- Confirmed `rows`, `columns`, indices, and suggestion fields are never consumed.
- Confirmed missing collections become fresh empty lists and absent `tableStyle` remains `UNSET`, while present style with missing column properties becomes `[]`.
- Confirmed model invariant `ValueError`s for cell styles and columns are translated to `GDocParseError` at the object path without masking nested parse errors.
- No task-specific defects found.

## Remaining concerns

- Recursive `tableOfContents` content relies on its concrete parser being attached by its owning parser task; this task intentionally dispatches through the typed `TableOfContents.gdoc_parser` attribute as specified.
- The two unrelated documentation format findings remain outside Task 5 scope.
