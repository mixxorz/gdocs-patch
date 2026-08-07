from collections.abc import Iterator
from dataclasses import dataclass

from gdocs_patch.models import (
    UNSET,
    Body,
    Document,
    DocumentTab,
    Equation,
    Paragraph,
    Tab,
    Table,
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
    ParagraphBoundary,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
)
from .edit_script import UnsupportedTransformation, generate_edit_script
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


def normalize_tree(tree: TreeNode) -> ContentStream:
    if isinstance(tree, TextRun):
        return ContentStream(
            items=[
                TextUnit(content=character, text_style=tree.text_style)
                for character in tree.content
            ]
        )

    if isinstance(tree, Equation):
        return ContentStream(items=[EquationUnit()])

    if isinstance(tree, Paragraph):
        items: list[ContentUnit] = []
        for child in tree.children:
            items.extend(normalize_tree(child).items)

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
                        content=normalize_tree(cell),
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

    items: list[ContentUnit] = []
    for child in tree.children:
        items.extend(normalize_tree(child).items)
    return ContentStream(items=items)


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
        tabs[tab.tab_id] = TabContent(
            body=normalize_tree(body),
            headers=(
                {
                    segment_id: normalize_tree(segment)
                    for segment_id, segment in content.headers.items()
                }
                if isinstance(content.headers, dict)
                else {}
            ),
            footers=(
                {
                    segment_id: normalize_tree(segment)
                    for segment_id, segment in content.footers.items()
                }
                if isinstance(content.footers, dict)
                else {}
            ),
            footnotes=(
                {
                    segment_id: normalize_tree(segment)
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
) -> dict[str, object]:
    source_content = normalize_document(source)
    target_content = normalize_document(target)

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

        # Temporary until ContentStream supports SectionBreak: a Docs body
        # starts with one at index 0, so supported body content begins at 1.
        body_script = generate_edit_script(
            source=source_tab.body,
            target=target_tab.body,
            start_index=1,
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
