# SDD Task 6 Report: List Parsers

## Status

Implemented and attached `ListLevelParser` and `ListDefinitionParser` on branch `feature-google-docs-parser` in the dedicated feature worktree.

## RED

Created two direct happy-path behavior tests in `tests/parsers/test_list.py`:

1. `ListLevel` maps `glyphFormat`, `glyphSymbol`, dimensions, and `textStyle`, while preserving `UNSET` for `glyph_type` and applying the proto defaults for alignment and start number.
2. `ListDefinition` maps two nesting levels (one symbol and one glyph type) and ignores suggestion metadata.

Command:

```bash
uv run pytest tests/parsers/test_list.py -v
```

Observed expected failure: 2 failed because neither model had an attached `gdoc_parser` (`AttributeError` for `ListLevel.gdoc_parser` and `ListDefinition.gdoc_parser`).

## GREEN

Added `gdocs_patch/parsers/list.py` with:

- required string validation for `glyphFormat`;
- independent optional parsing for `glyphType` and `glyphSymbol`;
- exact `BULLET_ALIGNMENT_UNSPECIFIED` and `0` defaults;
- optional `Dimension.gdoc_parser` delegation for both indentation fields;
- optional `TextStyle.gdoc_parser` delegation;
- model invariant `ValueError` wrapping as `GDocParseError` at the list-level path, without replacing nested parser errors;
- `ListDefinition` object validation and empty-list behavior when `listProperties` or `nestingLevels` is absent;
- indexed nesting-level parsing through `ListLevel.gdoc_parser`.

Attached both parsers by importing `.list` from `gdocs_patch/parsers/__init__.py` and assigning parser instances to the model classes.

Focused GREEN command:

```bash
uv run pytest tests/parsers/test_list.py tests/models/test_list.py -v
```

Result: 6 passed.

## Exact Defaults, UNSET, and Invariant Review

The complete-equality `ListLevel` test verifies:

- omitted `glyphType` remains `UNSET`;
- omitted `bulletAlignment` becomes `BULLET_ALIGNMENT_UNSPECIFIED`;
- omitted `startNumber` becomes `0`;
- nested dimensions and text style are complete model values, including their own omitted-field `UNSET` state.

Additional direct verification checked:

- absent `listProperties` produces `levels=[]`;
- present `listProperties` with absent `nestingLevels` produces `levels=[]`;
- a missing glyph representation raises `GDocParseError` at `$.listProperties.nestingLevels[2]` with the original model invariant message.

## Checks

Required focused checks:

```text
uv run pytest tests/parsers/test_list.py tests/models/test_list.py -v  -> 6 passed
uv run ruff check gdocs_patch/parsers/list.py tests/parsers/test_list.py -> passed
uv run ruff format --check gdocs_patch/parsers/list.py tests/parsers/test_list.py -> 2 files formatted
uv run pyright -> 0 errors, 0 warnings, 0 informations
test "$(git branch --show-current)" = "feature-google-docs-parser" -> passed
```

Repository checks:

```text
uv run pytest -> 60 passed
uv run ruff check . -> passed
uv run ruff format --check gdocs_patch tests -> 25 files formatted
uv run fixit lint . -> 28 files clean
uv run pyright -> 0 errors, 0 warnings, 0 informations
uv run pre-commit run --all-files -> all hooks passed
```

A broader `uv run ruff format --check .` also inspected Markdown code blocks and reported two pre-existing formatting differences in:

- `docs/superpowers/plans/2026-08-05-google-docs-parser.md`
- `docs/superpowers/specs/2026-08-05-google-docs-parser-design.md`

Those unrelated documentation files were not modified. The configured pre-commit Ruff format hook passed all files in its intended scope.

## Files

- Created `gdocs_patch/parsers/list.py`
- Modified `gdocs_patch/parsers/__init__.py`
- Created `tests/parsers/test_list.py`
- Created `.superpowers/sdd/task-6-report.md`

## Self-Review

Reviewed the task brief against the implementation and inspected the complete diff. No critical, important, or minor implementation issues were found. The parser stays within Task 6 scope, uses existing validators and path helpers, delegates nested parsing through attached parsers, preserves model defaults and `UNSET`, and ignores unsupported suggestion metadata naturally.

## Commits

- `dab3bee` — `Parse Google Docs lists`
- Report commit: committed separately after this report was written.
