# Declarative XHTML Rewrite Task 5 Report

## Status

DONE

## Implementation

- Added declarative `ListTag` and `ListItemTag` grammar with mutually exclusive existing-list ID and bullet-preset attributes, canonical attribute order, validated preset choices, non-negative zero-default nesting, at least one item, exactly one complete paragraph per item, and optional `BulletStyleTag` metadata.
- Migrated contiguous list grouping in the encoder to produce `tags.ListTag`/`tags.ListItemTag` directly while reusing the complete paragraph tag mapper.
- Migrated list decoding to consume declarative tags and project ordered `models.Paragraph` values with `models.Bullet` or `models.BulletPreset`.
- Preserved existing-ID versus target-preset sibling grouping, metadata position tolerance, canonical default omission, exact characterized errors, and preset-list bullet-style rejection.
- Removed superseded imperative list XML parsing/encoding and duplicate mapper preset constants. The preset vocabulary now has one owner in `tags.py`.
- Mapper references remain module-qualified (`models.X`, `tags.XTag`); tags remain model-agnostic; migrated list mapper methods contain no ElementTree operations.

## Files Changed

- `gdocs_patch/xhtml/tags.py`
- `gdocs_patch/xhtml/encoder.py`
- `gdocs_patch/xhtml/decoder.py`
- `tests/xhtml/test_declarative_boundary.py`
- `.superpowers/sdd/declarative-task-5-report.md`

The existing behavioral tests were unchanged; one declarative-boundary architecture test was added using TDD.

## TDD Evidence

Focused RED:

```console
uv run pytest tests/xhtml/test_declarative_boundary.py::test_lists_are_fully_declarative -q
1 failed: ListTag still inherited _OpaqueStructuralTag
```

Focused GREEN and unchanged list behavior:

```console
uv run pytest tests/xhtml/test_declarative_boundary.py tests/xhtml/test_structures.py -q
65 passed in 0.11s
```

## Verification

```console
uv run pytest -q
265 passed in 3.70s
uv run ruff check .
All checks passed!
uv run ruff format --check .
All files formatted after applying Ruff formatting
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
uv run pre-commit run --all-files
All configured hooks passed

git diff --check
passed
```

## Self-Review

- Re-read every Task 5 checkbox against the final diff.
- Confirmed list tags reuse all complete paragraph tag variants and bullet style metadata.
- Confirmed grouping remains contiguous and keyed by either existing list ID or preset.
- Confirmed list attributes encode in `g:list-id`, `g:bullet-preset`, then child order and list items encode nesting metadata before children.
- Confirmed preset validation is declared once and reused by the encoder.
- Confirmed the unchanged structural-list tests cover empty lists, identity exclusivity, invalid presets, negative nesting, exact paragraph cardinality, unknown content, style ordering, preset-style rejection, grouping, metadata, and round trips.
- Confirmed remaining ElementTree mapper code belongs to the intentionally unmigrated table boundary, not list methods.
- Preserved the pre-existing uncommitted modification to `.superpowers/sdd/declarative-task-2-report.md` and excluded it from this commit.

## Commit

- `refactor: map XHTML lists through tags`

## Concerns

- Tables remain behind the existing opaque structural boundary and still use ElementTree; this is outside Task 5 scope.
- No list-specific behavioral concerns remain after the full suite and static checks.
