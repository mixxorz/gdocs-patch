import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import cast

from gdocs_patch.models import (
    UNSET,
    Body,
    Bullet,
    Document,
    DocumentTab,
    Equation,
    IndexedNode,
    ListDefinition,
    PageBreak,
    Paragraph,
    ParagraphElement,
    SectionBreak,
    Segment,
    Tab,
    Table,
    TableCell,
    TableCellStyle,
    TextRun,
    TextStyle,
    TreeNode,
    UnsetType,
)

from .content_stream import (
    ContentStream,
    ContentUnit,
    EquationUnit,
    OpaqueUnit,
    PageBreakUnit,
    ParagraphBoundary,
    SectionBreakUnit,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
)
from .edit_script import (
    EditScriptContext,
    UnsupportedTransformation,
    generate_edit_script,
)
from .lowering import lower_edit_script


@dataclass(frozen=True, kw_only=True)
class TabContent:
    body: ContentStream
    headers: dict[str, ContentStream]
    footers: dict[str, ContentStream]
    footnotes: dict[str, ContentStream]


@dataclass(frozen=True, kw_only=True)
class DocumentContent:
    tabs: dict[str, TabContent]


def normalize_tree(
    tree: TreeNode,
    *,
    list_definitions: dict[str, ListDefinition] | None = None,
) -> ContentStream:
    if isinstance(tree, TextRun):
        return ContentStream(
            items=[
                TextUnit(content=character, text_style=tree.text_style)
                for character in tree.content
            ]
        )

    if isinstance(tree, Equation):
        return ContentStream(items=[EquationUnit()])

    if isinstance(tree, PageBreak):
        return ContentStream(items=[PageBreakUnit(text_style=tree.text_style)])

    if isinstance(tree, SectionBreak):
        return ContentStream(items=[SectionBreakUnit(style=tree.style)])

    if isinstance(tree, Paragraph):
        items: list[ContentUnit] = []
        for child in tree.children:
            items.extend(normalize_tree(child, list_definitions=list_definitions).items)

        boundary_text_style: TextStyle | UnsetType = UNSET
        if items:
            terminal_item = items[-1]
            if isinstance(terminal_item, TextUnit) and terminal_item.content == "\n":
                boundary_text_style = terminal_item.text_style
                items.pop()

        items.append(
            ParagraphBoundary(
                text_style=boundary_text_style,
                paragraph_style=tree.style,
                bullet=tree.bullet,
                list_definition=(
                    list_definitions.get(tree.bullet.list_id, UNSET)
                    if isinstance(tree.bullet, Bullet) and list_definitions is not None
                    else UNSET
                ),
            )
        )
        return ContentStream(items=items)

    if isinstance(tree, Table):
        rows: list[TableRowUnit] = []
        for row in tree.rows:
            cells: list[TableCellUnit] = []
            for cell in row.cells:
                if isinstance(cell.style, TableCellStyle):
                    row_span = cell.style.row_span
                    column_span = cell.style.column_span
                else:
                    row_span = 1
                    column_span = 1
                cells.append(
                    TableCellUnit(
                        cell_key=cell.cell_key,
                        content=normalize_tree(
                            cell,
                            list_definitions=list_definitions,
                        ),
                        row_span=row_span,
                        column_span=column_span,
                        style=cell.style,
                    )
                )
            rows.append(
                TableRowUnit(
                    row_key=row.row_key,
                    cells=cells,
                    min_height=row.min_height,
                    prevent_overflow=row.prevent_overflow,
                    is_header=row.is_header,
                )
            )
        return ContentStream(
            items=[
                TableUnit(
                    table_key=tree.table_key,
                    rows=rows,
                    column_properties=tree.column_styles,
                )
            ]
        )

    # Body, Segment, and TableCell do not represent content of their own; they
    # only hold content that belongs directly in this stream. We need to unwrap
    # them here or the fallback below would turn the whole container into one
    # OpaqueUnit and hide all of its editable children. Other unknown containers
    # stay opaque because we do not know how to edit their contents safely.
    if isinstance(tree, (Body, Segment, TableCell)):
        items: list[ContentUnit] = []
        for child in tree.children:
            items.extend(normalize_tree(child, list_definitions=list_definitions).items)
        return ContentStream(items=items)

    # OpaqueUnits let unsupported elements be retained or deleted, but not
    # inserted. Prefer a model ID so retained elements still match across an
    # XHTML round-trip, falling back to the full representation when no ID exists.
    object_identity = next(
        (
            f"{field_name}={value!r}"
            for field_name, value in vars(tree).items()
            if field_name.endswith("_id") and isinstance(value, str)
        ),
        None,
    )
    semantic_value = (
        f"{type(tree).__name__}:{object_identity}"
        if object_identity is not None
        else f"{type(tree).__name__}:{tree!r}"
    )
    return ContentStream(
        items=[
            OpaqueUnit(
                key=(
                    f"opaque-{hashlib.sha256(semantic_value.encode()).hexdigest()[:8]}"
                ),
                width=cast("IndexedNode", tree).utf16_width,
                is_inline=isinstance(tree, ParagraphElement),
                element_type=type(tree).__name__,
                object_identity=object_identity,
            )
        ]
    )


def walk_tabs(tabs: list[Tab]) -> Iterator[Tab]:
    for tab in tabs:
        yield tab
        yield from walk_tabs(tab.children)


def normalize_document(document: Document) -> DocumentContent:
    tabs: dict[str, TabContent] = {}

    for tab in walk_tabs(document.tabs):
        if not isinstance(tab.content, DocumentTab):
            continue
        body = tab.content.body
        if not isinstance(body, Body):
            raise ValueError("tab body must be loaded")
        content = tab.content
        list_definitions = content.lists if isinstance(content.lists, dict) else {}
        normalized_body = normalize_tree(body, list_definitions=list_definitions)
        tabs[tab.tab_id] = TabContent(
            body=normalized_body,
            headers=(
                {
                    segment_id: normalize_tree(
                        segment,
                        list_definitions=list_definitions,
                    )
                    for segment_id, segment in content.headers.items()
                }
                if isinstance(content.headers, dict)
                else {}
            ),
            footers=(
                {
                    segment_id: normalize_tree(
                        segment,
                        list_definitions=list_definitions,
                    )
                    for segment_id, segment in content.footers.items()
                }
                if isinstance(content.footers, dict)
                else {}
            ),
            footnotes=(
                {
                    segment_id: normalize_tree(
                        segment,
                        list_definitions=list_definitions,
                    )
                    for segment_id, segment in content.footnotes.items()
                }
                if isinstance(content.footnotes, dict)
                else {}
            ),
        )

    return DocumentContent(tabs=tabs)


def compile_document(
    *,
    source: Document,
    target: Document,
    allow_bullet_normalization: bool = False,
    prevent_table_indent_inheritance: bool = True,
) -> dict[str, object]:
    source_content = normalize_document(source)
    target_content = normalize_document(target)
    context = EditScriptContext(
        allow_bullet_normalization=allow_bullet_normalization,
        prevent_table_indent_inheritance=prevent_table_indent_inheritance,
    )

    if source_content.tabs.keys() != target_content.tabs.keys():
        raise UnsupportedTransformation("tab creation and deletion are not supported")

    requests: list[dict[str, object]] = []
    for tab_id, target_tab in target_content.tabs.items():
        source_tab = source_content.tabs[tab_id]
        if (
            source_tab.headers.keys() != target_tab.headers.keys()
            or source_tab.footers.keys() != target_tab.footers.keys()
            or source_tab.footnotes.keys() != target_tab.footnotes.keys()
        ):
            raise UnsupportedTransformation(
                "segment creation and deletion are not supported"
            )

        body_script = generate_edit_script(
            source=source_tab.body,
            target=target_tab.body,
            context=context,
        )
        requests.extend(
            lower_edit_script(
                edit_script=body_script,
                tab_id=tab_id,
            )
        )

        for source_segments, target_segments in (
            (source_tab.headers, target_tab.headers),
            (source_tab.footers, target_tab.footers),
            (source_tab.footnotes, target_tab.footnotes),
        ):
            for segment_id, target_segment in target_segments.items():
                segment_script = generate_edit_script(
                    source=source_segments[segment_id],
                    target=target_segment,
                    context=replace(context, inside_non_body_segment=True),
                )
                requests.extend(
                    lower_edit_script(
                        edit_script=segment_script,
                        tab_id=tab_id,
                        segment_id=segment_id,
                    )
                )

    batch: dict[str, object] = {"requests": requests}
    if source.revision_id is not UNSET:
        batch["writeControl"] = {"requiredRevisionId": source.revision_id}
    return batch
