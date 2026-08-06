from collections.abc import Iterator

from gdocs_patch.models import UNSET, Body, Document, DocumentTab, Tab, TreeNode

from .content_stream import ContentStream
from .edit_script import EditScript, UnsupportedTransformation, generate_edit_script


class TabContent:
    def __init__(
        self,
        *,
        body: ContentStream,
        headers: dict[str, ContentStream],
        footers: dict[str, ContentStream],
        footnotes: dict[str, ContentStream],
    ) -> None:
        self.body = body
        self.headers = headers
        self.footers = footers
        self.footnotes = footnotes


class DocumentContent:
    def __init__(self, *, tabs: dict[str, TabContent]) -> None:
        self.tabs = tabs


def normalize_tree(tree: TreeNode) -> ContentStream:
    raise NotImplementedError


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


def lower_edit_script(
    *,
    edit_script: EditScript,
    tab_id: str,
    segment_id: str | None = None,
) -> list[dict[str, object]]:
    raise NotImplementedError


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

        body_script = generate_edit_script(
            source=source_tab.body,
            target=target_tab.body,
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
