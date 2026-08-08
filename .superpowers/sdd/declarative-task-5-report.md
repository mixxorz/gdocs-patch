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

## Review Fixes

- Restored list validation precedence so the list identity invariant runs before child cardinality; an empty list with no identity again reports `exactly one of g:list-id and g:bullet-preset is required` rather than emptiness.
- Added reusable declarative validation controls: tags may run relationship cleanup before field validation, fields may opt out of internal field-name diagnostic prefixes, `Children` exposes parent-text/tail diagnostics, and non-negative integer attributes may declare their domain-specific negative-value diagnostic.
- Applied those controls to list/list-item tags to preserve exact public diagnostics for item paragraph cardinality, negative nesting, non-whitespace parent text, and non-whitespace child tails without returning to payload XML parsing.
- Replaced the obsolete multi-structural `_structural_boundary_tag` dispatch with a table-only `_table_boundary_tag`; declarative `ListTag` can no longer receive a `payload` through that path.
- Added focused public behavior regressions for the reviewed diagnostics without adding declaration-permutation tests.

### Review Fix TDD Evidence

Focused RED:

```console
uv run pytest tests/xhtml/test_structures.py::test_preserves_exact_list_validation_diagnostics -q
7 failed
```

Focused GREEN:

```console
uv run pytest tests/xhtml/test_structures.py::test_preserves_exact_list_validation_diagnostics tests/xhtml/test_structures.py::test_rejects_invalid_structural_lists tests/xhtml/test_declarative_boundary.py -q
33 passed in 0.06s
```

### Review Fix Verification

```console
uv run pytest -q
272 passed
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
uv run pre-commit run --all-files
All configured hooks passed
git diff --check
passed
```

## Re-review Fixes: Generic Pre-child Validation

- Replaced validation-order/message adaptations with a generic two-phase declarative decode lifecycle.
- `Tag.decode_from()` now decodes and validates every non-`Children` field, then invokes `validate_before_children()`, before asking a child field to inspect or recurse into descendants.
- `Decoder.decode_children()` now resolves the complete direct-child type sequence, preflights aggregate/spec cardinalities, and invokes the owning tag's `validate_resolved_child_types()` hook before recursively decoding the first child.
- Preserved specialized generic child decoders through an owner context, including paragraph error-path adaptation, body diagnostics, and table-of-contents section rejection.
- `ListTag.validate_before_children()` enforces identity exclusivity before any list item validation.
- `ListItemTag.validate_resolved_child_types()` enforces exactly one paragraph across all complete paragraph alternatives before malformed paragraph contents can be decoded.
- List nesting now uses an unconstrained declarative `IntegerAttribute`; `ListItemTag.validate_before_children()` rejects negative values at the `li` path. The same hook rejects invalid negative model state during encoding.
- Removed the superseded list-specific child field subclasses, field-prefix suppression, early-clean flag, and custom non-negative attribute diagnostic shim.
- Added compound-invalid public regressions for missing/both identities with malformed items, two paragraphs with a malformed first paragraph, and the exact li-level negative-nesting path.

### Re-review TDD Evidence

Focused RED:

```console
uv run pytest tests/xhtml/test_structures.py::test_list_preflight_errors_win_over_malformed_descendants tests/xhtml/test_structures.py::test_negative_list_nesting_error_is_reported_at_item_path -q
4 failed
```

Focused GREEN and established diagnostics:

```console
uv run pytest tests/xhtml/test_structures.py::test_list_preflight_errors_win_over_malformed_descendants tests/xhtml/test_structures.py::test_negative_list_nesting_error_is_reported_at_item_path tests/xhtml/test_structures.py::test_preserves_exact_list_validation_diagnostics tests/xhtml/test_structures.py::test_rejects_invalid_structural_lists -q
19 passed
```

### Re-review Verification

```console
uv run pytest -q
276 passed in 2.89s
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
uv run pre-commit run --all-files
All configured hooks passed
git diff --check
passed
```
