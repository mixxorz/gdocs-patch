# Declarative XHTML Final Rewrite Fix Report

## Status

DONE

## Summary

Restored reviewed validation precedence and sequential duplicate timing without reintroducing ElementTree mechanics into model mappers.

- Added explicit tag validation phases for post-attribute and post-descendant validation.
- Added model-agnostic declarative child uniqueness to `Children`, enforced after an entry's attributes/key are decoded and before its descendants.
- Added configurable forbidden-child priority relative to raw text.
- Moved anchor target and list-level glyph identity checks to the post-attribute phase.
- Deferred explicit `rowspan="1"` / `colspan="1"` semantic rejection until after cell descendants while retaining attribute-qualified diagnostics.
- Declared list-definition and segment-wrapper key uniqueness in `tags.py`; removed redundant mapper duplicate checks.
- Removed tests that introspected tag inheritance, fields, child specs, required descriptors, and payload absence. Retained generic scalar encoder behavior tests and public document serialization/deserialization tests.

## Files changed

- `gdocs_patch/xhtml/nodes.py`
- `gdocs_patch/xhtml/tags.py`
- `gdocs_patch/xhtml/decoder.py`
- `tests/xhtml/test_declarative_boundary.py`
- `tests/xhtml/test_structures.py`
- `tests/xhtml/test_validation.py`
- `.superpowers/sdd/declarative-final-fix-report.md`

## Differential evidence against `97610a8`

A detached temporary worktree at commit `97610a8` and the current worktree ran the same 12-case probe (`/tmp/xhtml_precedence_probe.py`). Command:

```bash
git worktree add --detach /tmp/gdocs-patch-97610a8 97610a8
uv run python /tmp/xhtml_precedence_probe.py > /tmp/probe-current.txt
(cd /tmp/gdocs-patch-97610a8 && uv run python /tmp/xhtml_precedence_probe.py) > /tmp/probe-baseline.txt
paste /tmp/probe-baseline.txt /tmp/probe-current.txt
git worktree remove --force /tmp/gdocs-patch-97610a8
```

Observed precedence:

| Compound-invalid case | `97610a8` winner | Fixed declarative winner |
|---|---|---|
| Missing anchor target + malformed content | invalid link target combination | invalid link target combination |
| Conflicting anchor targets + malformed content | invalid link target combination | invalid link target combination |
| ListLevel missing glyph identity + malformed valid-target anchor | malformed anchor child | exactly-one glyph identity (review-required correction) |
| TOC raw text + section | unexpected text content | unexpected text content |
| TOC unknown before section | unknown structural element | section forbidden message (review-required correction) |
| TOC section before unknown | section forbidden message | section forbidden message |
| Cell `rowspan="1"` + malformed descendant | malformed descendant | malformed descendant |
| Cell `colspan="1"` + malformed descendant | malformed descendant | malformed descendant |
| Duplicate second list definition + malformed second descendant | duplicate list key | duplicate list key |
| Malformed first list definition + later duplicate | malformed first descendant | malformed first descendant |
| Duplicate second segment + malformed second descendant | duplicate segment key | duplicate segment key |
| Malformed first segment + later duplicate | malformed first descendant | malformed first descendant |

The declarative rewrite's canonical tag-based paths differ from the old positional `/*[n]` paths where already established by the rewrite. Messages and precedence match the requested legacy behavior, except for the two explicitly requested corrections where the review requirement intentionally supersedes baseline sibling/metadata ordering.

## TDD evidence

Initial focused regression command:

```bash
uv run pytest -q \
  tests/xhtml/test_validation.py::test_anchor_target_validation_precedes_malformed_content \
  tests/xhtml/test_validation.py::test_duplicate_second_segment_precedes_its_malformed_descendant \
  tests/xhtml/test_validation.py::test_malformed_first_segment_precedes_later_duplicate \
  tests/xhtml/test_structures.py::test_duplicate_second_list_definition_precedes_its_malformed_descendant \
  tests/xhtml/test_structures.py::test_malformed_first_list_definition_precedes_later_duplicate \
  tests/xhtml/test_structures.py::test_list_level_identity_precedes_malformed_metadata_anchor \
  tests/xhtml/test_structures.py::test_toc_raw_text_precedes_forbidden_section \
  tests/xhtml/test_structures.py::test_toc_prioritizes_forbidden_section_over_unknown_siblings \
  tests/xhtml/test_structures.py::test_malformed_cell_descendant_precedes_explicit_default_span
```

After correcting a test decorator placement, this produced **8 failed, 4 passed**, with failures showing the reviewed regressions: anchor content errors, malformed duplicate-entry descendants, malformed metadata anchor, forbidden TOC section before raw text, and span rejection before descendants.

Post-implementation focused command (also including standalone span rejection): **14 passed**.

## Verification commands and results

```bash
uv run pytest -q tests/xhtml
```

Result: **197 passed in 2.83s**.

```bash
uv run pytest
```

Result: **297 passed in 2.87s**.

```bash
uv run ruff check .
```

Result: **All checks passed**.

```bash
uv run ruff format --check .
```

Result: **74 files already formatted**.

```bash
uv run fixit lint .
```

Result: **57 files clean**.

```bash
uv run pyright
```

Result: **0 errors, 0 warnings, 0 informations**.

```bash
uv run pre-commit run --all-files
```

Result: all hooks passed: Ruff check, Ruff format check, Pyright, Fixit, and hardcoded-secret detection.

```bash
git diff --check
```

Result: clean; no whitespace errors.

## Self-review

- `tags.py` remains model-agnostic and contains only declarative tag grammar/validation declarations.
- Mapper signatures and model/tag ownership remain unchanged; mapper duplicate checks were removed because declarative decoding now guarantees uniqueness before mapping.
- No mapper method gained ElementTree access or XML traversal.
- Uniqueness state is scoped to each active `Children` decode and is sequential: an earlier entry is fully decoded before a later key is considered; a duplicate is rejected after its attributes are decoded but before its descendants.
- Raw entry text is validated before uniqueness to preserve baseline `validate_whitespace` timing.
- Cell span lexical validation remains in the positive-integer attribute; only the explicit semantic default rejection is deferred.
- Encoding still rejects explicit span value `1`.
- TOC section diagnostics retain the exact message `section elements are only valid in a body`.
- Public tests cover every requested compound precedence case.

## Remaining concerns

No known functional concerns. The new `Children.unique_by` declaration refers to child field names by string, so a future misspelling would fail clearly at decode time rather than class-definition time; current declarations are covered by public behavior tests and Pyright cannot statically validate dynamic descriptor names.
