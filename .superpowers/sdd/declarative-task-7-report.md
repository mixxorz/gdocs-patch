# Declarative XHTML Rewrite Task 7 Final Re-review

## Verdicts

- **Specification:** **PASS.** The requested declarative boundaries and model-agnostic tags are present; the Task 7 source/AST implementation-structure tests were removed as required; mapper references remain module-qualified; and the updated line-count categories are accurate.
- **Behavior:** **FAIL.** The three previously reported cases are fixed, but one remaining AutoText diagnostic regression exists for AutoText nested inside a content anchor.
- **Quality:** **NEEDS FOLLOW-UP.** The behavior tests cover the requested fixes and no implementation-structure tests remain. Add one behavior regression test for the remaining anchored AutoText case.

## Verified fixes

- **AutoText conditional path:** `gdocs_patch/xhtml/nodes.py:616-624` rewrites the path only when the declared `positional_path_attribute` matches the failing attribute. `tags.py:623-627` assigns that metadata only to `g:type`; unknown attributes retain the tag-occurrence path. The paragraph `g:type` and unknown-attribute cases are covered by `tests/xhtml/test_validation.py:100-119`.
- **TOC priority and exact message:** `nodes.py:549-563` pre-scans prioritized forbidden children before normal child/text validation. `tags.py:1071-1080` marks XHTML `section` as prioritized and suppresses its element-name suffix. Both sibling orders are behavior-tested in `tests/xhtml/test_structures.py:88-108`; differential probes match the pre-Task-7 diagnostic in both orders.
- **Body minimum before text:** `nodes.py:564-568` applies the body cardinality diagnostic before text handling when there are no element children. `tags.py:1060-1065` opts `DocumentBodyTag` into that behavior. Empty, whitespace-only, and text-only bodies retain the pre-Task-7 `body must contain at least one section` diagnostic; text-only coverage is at `tests/xhtml/test_validation.py:88-98`.
- **Test policy:** `14bb08d` removes the three source/AST implementation tests and their `ast`/`Path` imports from `tests/xhtml/test_declarative_boundary.py`. The remaining tests exercise declarative behavior/contracts rather than scanning implementation source. New behavior coverage is in `test_validation.py` and `test_structures.py`.

## Finding

### P1 — AutoText `g:type` path changes inside content anchors

`tags.py:621-627` puts `positional_path_attribute=gdocs_name("type")` on the shared `Child(AutoTextTag)` declaration. That shared declaration is used both by `ParagraphVocabularyTag` and by `ContentAnchorTag` (`tags.py:651-658`). The generic decoder applies the rewrite in `nodes.py:616-624` for either owner.

Before Task 7, only `_ParagraphChildren.decode_from` performed the positional rewrite (`4eb778b:gdocs_patch/xhtml/tags.py:660-683`); `_ContentAnchorChildren` used the same child declarations but did not override decoding (`4eb778b:gdocs_patch/xhtml/tags.py:654-657`). Consequently, for `<p><a href="https://example.test"><g:auto-text /></a></p>`:

- before: `.../a[1]/g:auto-text[1]/@g:type: missing required attribute`
- after: `.../a[1]/*[1]/@g:type: missing required attribute`

The unknown-attribute anchor case remains unchanged, but the `g:type` path is still a public diagnostic regression. No current behavior test exercises AutoText inside a content anchor.

## Manual boundary audit

- `_Encoder` and `_Decoder` contain no `ElementTree`/`SubElement` names or calls, no XML `.set()`, `.get()`, `.attrib`, `.text`, or `.tail` accesses, and no qualified-tag comparisons. The `.get()` calls remaining in `_Decoder` are ordinary dictionary lookups (`counts` and `border_fields`), not XML operations.
- `nodes.py` owns the generic ElementTree conversion. In `encoder.py`, ElementTree mutation is limited to indentation/tree validation/serialization boundaries (`_indent_xml`, `_validate_generated_tree`, `_validate_encoded_tree`, `serialize_document`); in `decoder.py`, parsing and error translation are limited to `_preflight_xml`, `deserialize_document`, and `_decode_tag`.
- `tags.py` has no `ElementTree` or `gdocs_patch.models` import and contains no model mapping or XML decode/encode override. `encoder.py` and `decoder.py` use module-qualified `models` and `tags` references.
- No dead helper, scalar parser, compatibility branch, or unused constant was found in the changed modules.

## Line counts

Measured against `4eb778b` and `14bb08d` using physical file lines and AST class spans:

| Area | Before | After | Change |
|---|---:|---:|---:|
| Core mapper classes (`_Encoder` + `_Decoder`, AST class spans) | 1,414 | 1,384 | -30 |
| Reusable infrastructure (`base.py`, `nodes.py`, `attributes.py`, `tags.py`) | 2,368 | 2,236 | -132 |
| Six codec implementation files | 3,987 | 3,892 | -95 |

The core mapper reduction is therefore still distinct from the reusable infrastructure added for declarative diagnostics.

## Verification

- `uv run pytest -q tests/xhtml` — **190 passed**
- `uv run pytest -q` — **290 passed**
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — 74 files already formatted
- `uv run fixit lint .` — 57 files clean
- `uv run pyright` — 0 errors, 0 warnings
- `uv run pre-commit run --all-files` — all hooks passed
- Differential probes against `4eb778b` confirmed the three requested fixes and the remaining anchored AutoText diagnostic difference.

The only pre-existing unrelated worktree change is `M .superpowers/sdd/declarative-task-2-report.md`.

## Final Fix Report

Fixed the remaining anchored AutoText diagnostic regression. Positional path rewriting metadata now belongs to the owning `Children` context rather than the shared `Child(AutoTextTag)` declaration. `ParagraphVocabularyTag` opts direct AutoText `g:type` failures into historical `/*[n]` paths, while `ContentAnchorTag` retains `/a[n]/g:auto-text[n]/@g:type` paths.

Added a public anchored AutoText error-path regression. The focused AutoText run failed before the fix with `/*[1]`, then passed after the owner-specific metadata change with all three AutoText path behaviors covered.

Verification:

- `uv run pytest -q tests/xhtml/test_validation.py -k 'auto_text'` — 3 passed.
- `uv run pytest -q tests/xhtml` — 191 passed.
- `uv run pytest -q` — recorded in final verification.
- Ruff lint/format, Fixit, and Pyright — passed.
- `uv run pre-commit run --all-files` — recorded in final verification.
