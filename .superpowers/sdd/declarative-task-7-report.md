# Declarative XHTML Rewrite Task 7 Final Re-review

## Verdicts

- **Specification:** **PASS.** Declarative boundaries, model-agnostic tags, module-qualified mappers, dead-code cleanup, line-count separation, and the test policy all conform to the brief.
- **Behavior:** **PASS.** The previously reported AutoText, TOC, and body diagnostic regressions are fixed; owner-specific AutoText behavior now matches the pre-Task-7 implementation.
- **Quality:** **PASS.** Behavior regressions are covered without source/AST implementation-structure tests, and the final manual boundary audit found no violations.

## Verified owner-specific AutoText behavior

`Children` now accepts owner-level `positional_path_attributes` (`gdocs_patch/xhtml/nodes.py:162-189`), and the decoder applies it while decoding that field (`nodes.py:616-628`). Only `ParagraphVocabularyTag` opts direct AutoText children into the historical positional path (`gdocs_patch/xhtml/tags.py:658-668`); `ContentAnchorTag` uses the shared child declarations without that owner-level option (`tags.py:652-655`).

Differential probes against `4eb778b` now match exactly for:

- paragraph AutoText missing `g:type`: `/*[2]/@g:type`
- anchored AutoText missing `g:type`: `/a[1]/g:auto-text[1]/@g:type`
- paragraph and anchored AutoText unknown attributes: tag-occurrence paths
- TOC forbidden-section priority/message in both sibling orders

The anchored regression is covered by `tests/xhtml/test_validation.py:109-115`; the other AutoText cases are covered at `:100-126`.

## Previously reported fixes verified

- TOC priority and exact message use `ForbiddenChild` metadata (`gdocs_patch/xhtml/tags.py:1066-1078`) and the prioritized pre-scan (`nodes.py:549-563`). Both sibling orders are behavior-tested in `tests/xhtml/test_structures.py:88-109`.
- Empty, whitespace-only, and text-only bodies preserve the body-specific minimum diagnostic through `min_cardinality_before_text` (`tags.py:1055-1063`; `nodes.py:564-568`), with text-only coverage at `tests/xhtml/test_validation.py:88-98`.
- The three Task 7 source/AST implementation tests were removed in `14bb08d`. `tests/xhtml/test_declarative_boundary.py` retains only behavior/declarative contract tests; it no longer imports `ast`/`Path` or scans implementation source.

## Manual mapper-boundary audit

- `_Encoder` and `_Decoder` contain no `ElementTree`/`SubElement` names or calls, no XML `.set()`, `.attrib`, `.text`, or `.tail` accesses, and no qualified-tag comparisons. Remaining `_Decoder` `.get()` calls are dictionary lookups, not XML operations.
- `nodes.py` owns generic ElementTree conversion. Encoder ElementTree mutation is limited to indentation/tree validation/serialization boundaries; decoder parsing and error translation are limited to the explicit parse/security/decode boundaries.
- `tags.py` has no `ElementTree` or `gdocs_patch.models` import and no XML decode/encode overrides or model mapping. Encoder and decoder model/tag references remain module-qualified.
- No dead helper, scalar parser, compatibility branch, or unused constant was found in the changed modules.

## Line counts

Measured against `4eb778b` and `9e17213` using physical file lines and AST class spans:

| Area | Before | After | Change |
|---|---:|---:|---:|
| Core mapper classes (`_Encoder` + `_Decoder`, AST class spans) | 1,414 | 1,384 | -30 |
| Reusable infrastructure (`base.py`, `nodes.py`, `attributes.py`, `tags.py`) | 2,368 | 2,237 | -131 |
| Six codec implementation files | 3,987 | 3,893 | -94 |

The core mapper reduction remains distinct from reusable declarative infrastructure.

## Findings

**No findings.**

## Verification

- `uv run pytest -q tests/xhtml` — **191 passed**
- `uv run pytest -q tests/xhtml/test_validation.py -k 'auto_text'` — **3 passed**, 22 deselected
- `uv run pytest -q` — **291 passed**
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — 74 files already formatted
- `uv run fixit lint .` — 57 files clean
- `uv run pyright` — 0 errors, 0 warnings
- `uv run pre-commit run --all-files` — all hooks passed
- Differential probes against `4eb778b` produced no output differences for the reviewed diagnostic cases.

The only pre-existing unrelated source change is `M .superpowers/sdd/declarative-task-2-report.md`; the Task 7 review report was updated as the requested artifact.
