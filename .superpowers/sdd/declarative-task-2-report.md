# Declarative XHTML Rewrite Task 2 Report

## Status

DONE

## Implementation

- Declared the document envelope and metadata vocabulary in `gdocs_patch/xhtml/tags.py`: `HtmlTag`, XHTML `BodyTag`, recursive `TabTag`/`ChildTabsTag`, `DocumentTabTag`, complete document-style/background tags, named-style wrappers, metadata anchors, and list-definition/list-level tags.
- Preserved required attributes, `UNSET`, proto defaults, canonical omission of zero/default tab and list-level values, canonical field/attribute order, unique wrapper cardinality, recursive tabs, and metadata child order.
- Added a text-style descriptor factory and used fresh descriptor instances for span, named-style, and list-level contexts.
- Changed `_Encoder.encode_document()` to return `HtmlTag`; document, tabs, document-tab metadata, named styles, and list definitions now map models to tags. `serialize_document()` renders that tag through the generic encoder before generated-tree validation and canonical indentation.
- Changed `_Decoder.decode_document()` to consume `HtmlTag`; the XML parse/security boundary now decodes `HtmlTag` before model mapping. Declaration, DTD/entity, size, character, and depth protections remain in place.
- Removed superseded imperative document-envelope, tab, document-style, named-style, and list-definition decoder methods and duplicate constants.
- Preserved existing public error wording where characterization tests require it, while retaining generic indexed paths and attribute context.
- Kept tags independent of Google Docs model classes. Temporary boundary-child fields preserve body/segment XML owned by later declarative migration tasks; XML operations are confined to their generic boundary methods and explicitly named adapter functions.

## Files Changed

- `gdocs_patch/xhtml/tags.py`
- `gdocs_patch/xhtml/encoder.py`
- `gdocs_patch/xhtml/decoder.py`
- `.superpowers/sdd/declarative-task-2-report.md`

No existing public test or syntax-reference file was changed.

## Characterization and Verification

Existing XHTML tests served as unchanged characterization throughout the migration.

Focused metadata verification:

```console
uv run pytest tests/xhtml/test_document.py tests/xhtml/test_structures.py -q
57 passed
```

XHTML suite after both mapping directions:

```console
uv run pytest tests/xhtml -q
146 passed
```

Fresh repository-wide final verification:

```console
uv run pytest -q
246 passed in 3.62s
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
uv run pre-commit run --all-files
all configured hooks passed
git diff --check
passed
```

Ruff format initially identified the three edited modules, which were formatted before final verification.

## Self-Review

- Re-read every Task 2 checkbox and compared it with the final diff.
- Confirmed `tags.py` imports no `gdocs_patch.models` classes and contains no model mapping.
- Confirmed shared text-style descriptor identities differ across span, named-style, and list-level declarations.
- Confirmed the migrated mapper signatures are tag-based and the public serializer/deserializer cross the generic encoder/decoder boundary.
- Confirmed canonical metadata ordering and default omission through the unchanged round-trip and exact-fragment tests.
- Confirmed duplicate list keys, invalid links, unsupported namespaces, duplicate body wrappers, unknown attributes/elements, and indexed errors retain characterized public behavior.
- Confirmed tests, `docs/xhtml-syntax.md`, and the excluded reference JSON are unchanged.
- Ran `git diff --check` successfully.

## Commit

- `f4f0293618b35f5b44b63da54abf5204e8208e09 refactor: map XHTML document metadata through tags`

## Concerns

Body, segment, and structural descendants remain intentionally behind explicit temporary boundary adapters because their declarative declarations and mappings belong to Task 3. The migrated document-envelope and metadata mapper methods themselves use tags; Task 3 should delete `_BoundaryChildren` and the corresponding adapters when those descendants migrate.

## Task 2 Review Fixes

- Restored the prior canonical `DocumentStyle` attribute order through `DocumentStyleTag.field_order`: document mode, header/footer IDs, booleans, page number, then dimensions.
- Added validation-before-default-omission for integer model fields introduced in Task 2. Mutated `False` and `0.0` values for `Tab.nesting_level` and `ListLevel.start_number` now raise rather than comparing equal to zero and disappearing as `UNSET`.
- Restored wrong-XHTML-namespace handling at the parse boundary.
- Generalized singular-child cardinality errors in `Children.validate()` using each child tag's declared XML local name. This restores duplicate body and all singular `DocumentTab` wrapper errors without class-specific decoder rewrites; the previous `HtmlTag` one-off was removed.
- Replaced giant model/tag symbol imports throughout both mapper modules with module-qualified `models.*` and `tags.*` references.
- Added the module-qualified mapper import rule to the declarative rewrite plan's Global Constraints.

### Review Fix TDD Evidence

Focused RED:

```console
uv run pytest tests/xhtml/test_document.py::test_round_trips_complete_document_style_and_preserves_empty_presence tests/xhtml/test_document.py::test_rejects_non_integer_default_tab_nesting_level tests/xhtml/test_document.py::test_rejects_wrong_xhtml_namespace tests/xhtml/test_document.py::test_rejects_duplicate_document_tab_wrapper tests/xhtml/test_structures.py::test_rejects_non_integer_default_list_start_number -q
```

Result: `13 failed`. The failures independently demonstrated noncanonical style ordering, silent normalization of `False`/`0.0`, generic wrong-namespace wording, and class-name-based duplicate-wrapper errors.

Focused GREEN (including the existing duplicate root-body characterization):

```console
uv run pytest tests/xhtml/test_document.py::test_round_trips_complete_document_style_and_preserves_empty_presence tests/xhtml/test_document.py::test_rejects_non_integer_default_tab_nesting_level tests/xhtml/test_document.py::test_rejects_wrong_xhtml_namespace tests/xhtml/test_document.py::test_rejects_duplicate_document_tab_wrapper tests/xhtml/test_document.py::test_rejects_duplicate_required_body_wrapper tests/xhtml/test_structures.py::test_rejects_non_integer_default_list_start_number -q
```

Result: `14 passed in 0.05s`.

Post-refactor XHTML suite:

```console
uv run pytest tests/xhtml -q
```

Result: `158 passed in 2.55s`.

Final full verification:

```console
uv run pytest -q
258 passed in 3.82s
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
git diff --check
passed
uv run pre-commit run --all-files
ruff check, Ruff format, Pyright, Fixit, and hardcoded-secret detection passed
```

Review-fix commit:

- `67700e7417a9d8a8ed21ebe00ad802287fd40bc5 fix: preserve declarative XHTML document behavior`
