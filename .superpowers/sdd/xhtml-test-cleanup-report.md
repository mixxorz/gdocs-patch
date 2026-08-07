# XHTML codec test cleanup report

## Result

The XHTML suite now concentrates on observable behavior through the public `serialize_document()` and `deserialize_document()` APIs. Production code, syntax documentation, design documents, and plans were not changed.

Cleanup commit: `673c547ed57c8c9fd75f09846c8089296e32f6d0`

## Audit categories and pruning rationale

- **Validation-order coupling:** Removed parameterized cases that made several fields invalid and asserted which nested, scalar, metadata, or cross-field error happened first. These encoded decoder traversal order rather than a public invariant.
- **Private helper coupling:** Removed direct imports and monkeypatching of `gdocs_patch.xhtml.base`, `.decoder`, and `.encoder`, including direct number formatter/parser assertions and private limit constants. Replacement security tests exercise only public APIs and documented fixed limits.
- **Exhaustive definition matrices:** Removed the date-format and time-format enumeration matrices. The complete `DateElement` round trip already covers both fields, while invalid enum handling remains represented at the public parser boundary.
- **Repeated mutated-model variants:** Consolidated 22 serializer mutation cases into representative scalar and collection corruption cases. Distinct structural and cross-field serializer invariants remain covered in their behavioral files.
- **Catch-all final review organization:** Deleted `test_final_review.py`. Its distinct security behaviors moved to `test_security.py`; private-helper checks, repeated numeric variants, and redundant mutation cases were removed.
- **Security boundaries:** Retained public behavior for DTD/internal/external entity rejection, the documented 10,000,000-character input/output limit, the documented depth limit, avoidance of leaked `RecursionError`, illegal XML 1.0 characters, and invalid mutable model state.
- **Canonical syntax:** Retained canonical document/paragraph/structure serialization assertions, stable normalized round trips, and representative rejection of noncanonical integer and float lexemes.
- **Feature-family behavior:** Retained complete and representative round trips for document/tab/segment data, document and named styles, paragraph metadata and every paragraph-element family, section styles, lists, recursive tables/table-of-contents, and the maximal supported document.
- **Permissive input:** Retained metadata-child reordering tests across document, named-style, paragraph, list, table/cell, and combined metadata contexts because each protects accepted syntax at a different grammar boundary.

## Files changed

- Deleted `tests/xhtml/test_final_review.py`.
- Added `tests/xhtml/test_security.py` for cohesive public security and hardening behavior.
- Updated `tests/xhtml/test_validation.py` to remove private implementation and validation-order assertions.
- Updated `tests/xhtml/test_paragraph.py` to remove redundant exhaustive Literal matrices.
- Added this report at `.superpowers/sdd/xhtml-test-cleanup-report.md`.

## Counts

| Measure | Before | After | Change |
|---|---:|---:|---:|
| Test functions | 87 | 69 | -18 |
| Collected cases | 271 | 167 | -104 |
| Lines in `tests/xhtml/*.py` | 3,262 | 2,522 | -740 |

Counts were obtained with `rg '^def test_' tests/xhtml | wc -l`, `uv run pytest tests/xhtml --collect-only -q`, and `wc -l tests/xhtml/*.py`. The after line count includes the new focused security file.

## Verification commands and outputs

### Focused XHTML suite

Command: `uv run pytest tests/xhtml -q`

Output: `167 passed in 1.18s`

### Full suite

Command: `uv run pytest -q`

Output: `267 passed in 1.24s`

### Ruff lint

Command: `uv run ruff check tests/xhtml`

Output: `All checks passed!`

### Ruff formatting

Command: `uv run ruff format --check tests/xhtml`

Output: `7 files already formatted`

### Fixit

Command: `uv run fixit lint tests/xhtml`

Output: `🧼 7 files clean 🧼`

### Pyright

Command: `uv run pyright`

Output: `0 errors, 0 warnings, 0 informations`

### Pre-commit

Command: `uv run pre-commit run --all-files`

Output:

```text
ruff check...............................................................Passed
ruff format check........................................................Passed
pyright..................................................................Passed
Fixit - lint and apply autofixes.........................................Passed
Detect hardcoded secrets.................................................Passed
```

## Self-review against the brief

- Diff is limited to XHTML tests and this required report.
- All test imports from the XHTML package use its public API.
- No assertion depends solely on invalid-field validation order.
- `test_final_review.py` is deleted, with unique security behavior relocated by concern.
- Representative tests continue to cover every supported model feature family, canonical output, permissive documented input, public-boundary failures, security limits, and distinct regressions.
- No numeric target drove pruning; larger parameterizations remain where cases represent different tags, structural positions, model variants, or user-visible invalid forms.

## Concerns and intentionally retained repetition

- The documented 10,000,000-character boundary tests allocate large strings. They are intentionally retained because input and output limits are separate public security guarantees and private-constant monkeypatching was removed.
- Metadata-order acceptance appears in multiple files, intentionally, because document, named-style, paragraph, list, and table metadata use different grammar paths and have regressed independently.
- Structural invalid-syntax parameterizations remain relatively broad where each case protects a distinct grammar or model invariant rather than a Literal definition.
