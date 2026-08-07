# XHTML document codec final-review fixes

## Scope

Work completed only in `feature/xhtml-document-codec`; no main/controller files were edited. Production changes are limited to `gdocs_patch/xhtml/{base,decoder,encoder}.py`, with public regressions in `tests/xhtml/test_final_review.py`.

## RED evidence

Initial focused run:

```text
uv run pytest tests/xhtml/test_final_review.py -q
39 failed, 13 passed
```

Observed failures covered expanded internal entities, missing named size/depth constants, illegal XML characters, mutable encoder state, and permissive integer/float lexical forms. A test-fixture construction error (`Tab.children`) was corrected before using those cases as behavioral RED evidence.

## GREEN evidence

Focused regressions:

```text
uv run pytest tests/xhtml/test_final_review.py -q
52 passed
```

XHTML suite after integration:

```text
uv run pytest tests/xhtml -q
248 passed
```

## Deserialization hardening audit

- `MAX_XHTML_INPUT_CHARACTERS = 10_000_000`, measured as Python input characters before parsing.
- `MAX_XML_ELEMENT_DEPTH = 256`, measured iteratively by expat start/end callbacks, root included.
- stdlib expat preflight rejects DOCTYPE and general/unparsed/external entity declarations before ElementTree parsing and expansion.
- malformed preflight/ElementTree input and recursion failures become `XHTMLParseError`; parser/recursion causes are chained where applicable.
- Boundary, exceed, monkeypatched size, internal entity, external DTD, stray entity declaration, and uncaught-recursion regressions are public.

## XML 1.0 output audit

Before indentation or `ElementTree.tostring`, `_validate_xml_characters` iteratively visits every generated element and checks text, tail, and every attribute value against XML 1.0 legal character ranges. Tests cover NUL, control U+000B, and lone surrogate in document title, tab attribute, text-run text, and text-run-generated `<br>` tail.

## Encoder mutable-state invariant audit

The encoded tree is explicitly passed through the XHTML decoder grammar before output. This avoids reflection and makes the encoder's accepted output a subset of decoder-accepted XHTML. The audit covers:

- nonnegative Tab/Bullet/BulletPreset nesting;
- positive table row/column spans and canonical omission of span 1;
- all emitted enum fields through the decoder's explicit allowed-value sets;
- finite/in-range opaque colors and valid transparent/opaque forms;
- TableColumn width type/width coupling;
- ListLevel exactly-one glyph form plus glyph/alignment enums;
- required dimensions, colors, links, identifiers, and structured metadata;
- malformed mutated object shapes translated from attribute/key/type failures to `ValueError`.

Public parameterized mutations exercise tab and bullet nesting, bullet preset and paragraph named-style enums, color range, table span, table-column coupling, and list-level glyph exclusivity. Existing XHTML parameterized tests retain full decoder enum and structured-invariant category coverage.

## Canonical number audit

- Integers accept only `0` or a nonzero decimal integer with optional leading minus.
- Floats accept only serializer-compatible decimal/exponent forms: no whitespace, underscores, leading plus/zeros, nonfinite values, leading-dot/trailing-dot forms, uppercase exponent, or hexadecimal alternatives.
- `format_number` rejects nonfinite values and canonicalizes both signs of zero to `0`.
- Idempotence tests include negative zero, integral floats, fractional values, small/large exponent output, and full-precision repr output.

## Ignored and untracked report

At audit time, the only untracked source file was `tests/xhtml/test_final_review.py`. Ignored paths were existing/generated environment and cache content: `.pytest_cache/`, `.ruff_cache/`, `.venv/`, Python `__pycache__/` directories, `.superpowers/`, and ignored codemod cache content. This report is itself under ignored `.superpowers/` and must be force-added. No unrelated ignored artifact is intended for commit.

## Final verification

Fresh pre-commit verification wave:

```text
uv run pytest tests/xhtml/test_final_review.py -q  # 52 passed
uv run pytest tests/xhtml -q                       # 248 passed
uv run pytest -q                                   # 348 passed
uv run ruff check .                                # All checks passed
uv run ruff format --check .                       # 69 files already formatted
uv run fixit lint .                                # 53 files clean
uv run pyright                                     # 0 errors, 0 warnings
uv run pre-commit run --all-files                  # all hooks passed
```
