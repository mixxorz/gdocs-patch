# Declarative XHTML Rewrite Task 7 Review

## Verdicts

- **Specification:** **PASS** for the requested architecture. `ElementTree` access is confined to `gdocs_patch/xhtml/nodes.py` and the explicit decode/render/security boundary functions in `decoder.py` and `encoder.py`; `_Encoder`/`_Decoder` contain no XML-element mechanics, `tags.py` is model-agnostic, and mapper references remain module-qualified (`models`/`tags`). The commit message is also `refactor: complete declarative XHTML codec`.
- **Behavior:** **FAIL**. The cleanup changes public parse diagnostics for invalid XHTML, despite the brief requiring exact public behavior.
- **Quality:** **NEEDS FOLLOW-UP**. The implementation is lint/type/test clean, but the new structural tests do not cover every prohibited operation named in the brief.

## Findings

### P1 — Auto-text diagnostics changed for non-`g:type` failures

`gdocs_patch/xhtml/tags.py:623` sets `path_by_position=True` for every `AutoTextTag`. `gdocs_patch/xhtml/nodes.py:575-580` therefore rewrites every nested AutoText failure to `/*[position]`.

Before Task 7, `4eb778b:gdocs_patch/xhtml/tags.py:660-683` rewrote the path only for an AutoText `g:type` failure. For example, the same invalid document with `<g:auto-text g:unknown="x" />` produced:

- before: `.../p[1]/g:auto-text[1]/@g:unknown: unknown attribute g:unknown`
- after: `.../p[1]/*[1]/@g:unknown: unknown attribute g:unknown`

The input is still rejected, but the externally visible path/diagnostic is not preserved. The added regression test covers only ordinary repeated-span paths (`tests/xhtml/test_declarative_boundary.py:134-146`); existing AutoText coverage exercises only missing `g:type` (`tests/xhtml/test_validation.py:67-73`), so this regression is untested.

### P1 — Table-of-contents forbidden-section diagnostics and precedence changed

`gdocs_patch/xhtml/nodes.py:545-550` now handles the `TableOfContentsTag` forbidden section through the generic unknown-child path and always supplies `element_name`. `_decode_tag` appends that name to the message at `gdocs_patch/xhtml/decoder.py:54-55`.

Before Task 7, `4eb778b:gdocs_patch/xhtml/tags.py:1106-1110` performed a pre-scan and called `decoder.fail("section elements are only valid in a body")` without an element name. Differential probes show both changes:

- unknown child before `<section />`: before `section elements are only valid in a body`; after `unknown child element g:unknown`
- `<section />` before an unknown child: before `section elements are only valid in a body`; after `section elements are only valid in a body section`

This is a public behavior/diagnostic regression, not merely an internal refactor.

### P1 — Non-empty text in an empty document body loses the body-specific diagnostic

`gdocs_patch/xhtml/nodes.py:540` validates parent text before applying the `min_num` rule. The old `_DocumentBodyChildren` checked `not list(element)` first (`4eb778b:gdocs_patch/xhtml/tags.py:1093-1097`), so any body with no section children reported `body must contain at least one section`.

For `<g:body>text</g:body>`:

- before: `.../g:body: body must contain at least one section`
- after: `.../g:body: unexpected text`

The current empty/whitespace-only cases happen to retain the old error because whitespace is ignored, but non-whitespace text does not. This precedence change is not covered by `tests/xhtml/test_validation.py:75-88`, which tests only an empty body.

### P2 — Boundary regression tests do not enforce all listed prohibitions

`tests/xhtml/test_declarative_boundary.py:18-23` only searches three modules for the strings `ElementTree`/`xml.etree`. The mapper test at `:37-49` only rejects AST attributes named `attrib`, `text`, and `tail`. It does not detect `ElementTree` calls/types, `.get()`, `.set()`, `SubElement`, or raw qualified-tag comparisons inside `_Encoder`/`_Decoder`, all of which are explicitly listed in the brief.

The current implementation passes a manual/AST audit for those operations, so this is a test-enforcement gap rather than evidence of a current mapper violation. Extend the AST test to inspect the mapper class bodies for all prohibited names and comparison forms.

## Verified non-findings

- `tags.py` has no `gdocs_patch.models` import and no `decode_from`/`encode_into` override (`gdocs_patch/xhtml/tags.py:1-23`; structural test at `tests/xhtml/test_declarative_boundary.py:25-34`).
- No direct XML-element operations were found in `_Encoder` or `_Decoder`; generic XML handling remains in `nodes.py` and explicit boundary functions.
- No dead helper/constant usage was identified in the changed modules; Ruff's unused-name checks pass.
- The reported physical line counts are accurate when measured against `4eb778b` and `d11bdea`:

  | Area | Before | After | Change |
  |---|---:|---:|---:|
  | Core mapper classes (`_Encoder` + `_Decoder`, AST class spans) | 1,414 | 1,384 | -30 |
  | Reusable infrastructure (`base.py`, `nodes.py`, `attributes.py`, `tags.py`) | 2,368 | 2,186 | -182 |
  | Six codec implementation files | 3,987 | 3,842 | -145 |

## Verification performed

- `uv run pytest -q` — **289 passed**
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — 74 files already formatted
- `uv run fixit lint .` — 57 files clean
- `uv run pyright` — 0 errors, 0 warnings
- `uv run pre-commit run --all-files` — all hooks passed
- Differential probes against `4eb778b` confirmed all three diagnostic regressions above.

The only pre-existing worktree change remains `M .superpowers/sdd/declarative-task-2-report.md`; no source files were modified during review.

## Fix Report

Addressed all Task 7 review findings with public behavior regressions:

- AutoText uses positional `/*[n]` paths only when the failing attribute is `g:type`; unknown attributes retain `/g:auto-text[n]` paths.
- Declarative forbidden-child metadata now supports priority and element-name inclusion. TOC sections take precedence over unknown siblings in either order and preserve the exact diagnostic without an appended element name.
- Declarative child metadata now supports minimum-cardinality validation before text handling. A text-only document body preserves `body must contain at least one section`.
- Removed the Task 7 source/AST implementation-structure tests. Boundary compliance was re-audited manually instead: `_Encoder` and `_Decoder` contain no XML element mechanics, and `tags.py` remains model-agnostic.

Behavior-first red/green evidence:

- Initial focused run: 4 failed and 1 passed; failures reproduced text-only body precedence, AutoText unknown-attribute path, and both TOC sibling orders. The existing/new AutoText `g:type` positional case passed.
- After the declarative fixes: all 5 focused behavior cases passed.

Final verification:

- `uv run pytest -q tests/xhtml` — 190 passed.
- `uv run pytest -q` — recorded in the final commit verification.
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — passed.
- `uv run fixit lint .` — passed.
- `uv run pyright` — 0 errors, 0 warnings.
- `uv run pre-commit run --all-files` — recorded in the final commit verification.
