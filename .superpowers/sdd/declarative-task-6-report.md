# Declarative XHTML Rewrite Task 6 Review

## Verdicts

- **Spec: FAIL** — the table vocabulary and mapper structure are declarative, but canonical span enforcement is incomplete at the tag boundary and some required-child diagnostics are no longer exact.
- **Behavior: FAIL** — malformed mutable table keys can be silently dropped during serialization.
- **Quality: CONCERNS** — the full suite and static checks pass, but the missing regression tests allowed the issues below.

## Findings

### P2 — Invalid `UNSET` table keys are silently omitted

**Location:** `gdocs_patch/xhtml/encoder.py:447`, `:454`, `:483`

The mapper converts only `None` to `models.UNSET` before constructing the tag. If a mutable model is corrupted with `models.UNSET` in `table_key`, `row_key`, or `cell_key`, the optional `StringAttribute` treats it as absent and serialization succeeds while dropping the key. The previous imperative mapper called `require_string` for every value other than `None`, so this invalid model state was rejected. This also violates the repository's invalid-mutable-model invariant and can cause silent metadata loss.

A direct probe confirmed that each of these mutations serializes successfully with the corresponding key omitted. Validate the model value as a string before passing it to the tag (while retaining `None` as the intentional omission).

### P2 — Declarative tags can emit the explicitly noncanonical span value `1`

**Location:** `gdocs_patch/xhtml/tags.py:842-847`, `:960-962`

`_CellSpanAttribute` rejects `1` only in `decode`; it inherits `PositiveIntegerAttribute.encode`, which accepts `1`, and its validation does not reject it. Consequently, `tags.TableCellTag(row_span=1, children=[]).dumps()` emits `rowspan="1"`, even though the same tag grammar rejects that XML when decoding. The model mapper correctly omits model defaults at `gdocs_patch/xhtml/encoder.py:474-476`, but the declarative tag interface itself does not enforce the required canonical invariant. Add matching encode/validation rejection (or otherwise make the tag canonicalization symmetric).

### P2 — Required-child error diagnostics changed from the characterized exact messages

**Locations:** `gdocs_patch/xhtml/tags.py:878-884`, `:984-988`

The declarative cardinality declarations enforce the constraints, but they use the generic `Children` cardinality error. Missing `<tbody>` now reports `children requires at least 1 TableBodyTag child(ren); got 0` instead of the prior `missing required tbody child`. A border without `<g:color>` similarly reports a generic `ColorTag` cardinality message instead of `missing required g:color child`. Since Task 6 binds exact errors, preserve the specific diagnostics with field-specific `min_error` values or equivalent declarative validation.

## Binding checklist

- Full table grammar: **PASS**, subject to the canonical/error findings above.
- Canonical model output and default normalization: **PASS** for the model mapper; **FAIL** for direct tag span-one emission.
- Fixed-width consistency: **PASS**; both decode and encode validation enforce the width/type relationship.
- Positive and noncanonical spans: **PASS** for XML decoding and model output; **FAIL** for direct tag encoding of explicit one.
- Recursive structural cells: **PASS**.
- Module-qualified mappers: **PASS** (`models.*` and `tags.*`).
- Model-agnostic tags: **PASS**; `tags.py` does not import model classes.
- No `ElementTree` in table mapper methods: **PASS**; XML remains at the document/tag boundaries.
- Superseded table boundary and duplicate table helpers: **PASS**; no opaque table payload/boundary remains.

## Verification

- `uv run pytest -p no:cacheprovider tests/xhtml/test_declarative_boundary.py tests/xhtml/test_structures.py tests/xhtml/test_validation.py -q` — **101 passed**
- `uv run pytest -p no:cacheprovider -q` — **280 passed**
- `uv run ruff check ...` — **passed**
- `uv run ruff format --check .` — **passed**
- `uv run fixit lint .` — **57 files clean**
- `uv run pyright` — **0 errors, 0 warnings, 0 informations**

# Task 6 Review Fix Report

## Fixes

- Restored strict mutable-model key validation: `None` remains intentional absence, while `table_key`, `row_key`, and `cell_key` values other than strings now pass through `require_string` and fail serialization, including `UNSET`.
- Made `_CellSpanAttribute` symmetric by enforcing the explicit-one prohibition during decode, direct tag validation, and attribute encoding. The model mapper continues to omit default span one.
- Added reusable per-`Child` `min_error` support to declarative child cardinality validation.
- Restored exact missing-child diagnostics: `missing required tbody child` and `missing required g:color child`.

## TDD Evidence

RED:

```console
uv run pytest -q tests/xhtml/test_structures.py::test_rejects_invalid_mutated_table_keys tests/xhtml/test_declarative_boundary.py::test_direct_table_cell_tag_rejects_explicit_span_one tests/xhtml/test_structures.py::test_preserves_missing_required_table_child_diagnostics
6 failed
```

GREEN:

```console
uv run pytest -q tests/xhtml/test_structures.py::test_rejects_invalid_mutated_table_keys tests/xhtml/test_declarative_boundary.py::test_direct_table_cell_tag_rejects_explicit_span_one tests/xhtml/test_structures.py::test_preserves_missing_required_table_child_diagnostics
6 passed
```

## Focused Verification

```console
uv run pytest -p no:cacheprovider tests/xhtml/test_declarative_boundary.py tests/xhtml/test_structures.py tests/xhtml/test_validation.py -q
107 passed
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
```

## Full Verification

```console
uv run pytest -p no:cacheprovider -q
286 passed in 3.24s
uv run pre-commit run --all-files
All configured hooks passed
```
