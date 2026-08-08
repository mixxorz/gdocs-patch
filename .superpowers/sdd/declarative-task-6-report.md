# Declarative XHTML Rewrite Task 6 Report

## Status

DONE

## Implementation

- Declared the complete table vocabulary in `tags.py`: table, optional/empty colgroup, columns, required synthetic tbody, rows, cells, cell styles, structured background colors, and four directional borders.
- Migrated table model encoding and decoding to module-qualified `models.X` / `tags.XTag` mappings.
- Preserved canonical attribute and child order, table/row/cell keys, row defaults, unset-versus-empty columns, default-only style normalization, metadata position tolerance, and recursive structural cell content.
- Enforced fixed-width consistency and canonical spans declaratively, including positive spans and rejection of explicit span one.
- Removed the opaque structural boundary, table payload field, imperative table XML parsing/encoding helpers, and duplicate table vocabularies.
- Table mapper methods contain no ElementTree operations; `tags.py` remains model-agnostic.

## Files Changed

- `gdocs_patch/xhtml/tags.py`
- `gdocs_patch/xhtml/encoder.py`
- `gdocs_patch/xhtml/decoder.py`
- `tests/xhtml/test_declarative_boundary.py`
- `.superpowers/sdd/declarative-task-6-report.md`

A pre-existing modification to `.superpowers/sdd/declarative-task-2-report.md` was preserved and excluded from the Task 6 commit.

## TDD Evidence

RED:

```console
uv run pytest tests/xhtml/test_declarative_boundary.py::test_tables_are_fully_declarative -q
1 failed: TableTag still inherited _OpaqueStructuralTag
```

GREEN plus table behavior:

```console
uv run pytest tests/xhtml/test_declarative_boundary.py tests/xhtml/test_structures.py tests/xhtml/test_validation.py -q
101 passed
```

## Verification

```console
uv run pytest -q
280 passed in 3.03s
uv run ruff check .
All checks passed!
uv run ruff format --check .
74 files already formatted
uv run fixit lint .
57 files clean
uv run pyright
0 errors, 0 warnings, 0 informations
```

Final pre-commit and post-report verification are recorded in the session result.

## Self-Review

- Checked each Task 6 brief item against the final diff.
- Confirmed tbody is required and always synthesized by the encoder.
- Confirmed colgroup preserves UNSET versus an explicit empty list.
- Confirmed canonical table, column, row, cell, style, color, and border ordering remains covered by unchanged behavioral tests.
- Confirmed cell metadata may decode around structural content without reordering that content.
- Confirmed nested paragraphs, lists, tables, and table-of-contents use the shared declarative structural vocabulary recursively.
- Confirmed exact characterized diagnostics for duplicate cell style, unknown cell structures, explicit span one, fixed-width mismatch, malformed colors, and missing border fields.
- Confirmed no opaque boundary or duplicate table XML helper remains.

## Commit

- `refactor: map XHTML tables through tags`

## Concerns

- ElementTree remains at the document parse/serialization boundary by design; no table model mapper method uses it.
- No table-specific behavioral concerns remain after the full suite and static checks.
