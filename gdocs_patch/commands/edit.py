from collections.abc import Sequence
from dataclasses import dataclass

from gdocs_patch.client import GoogleDocsClient
from gdocs_patch.compiler import compile_document
from gdocs_patch.parsers import document_parser
from gdocs_patch.xhtml import deserialize_document, serialize_document


@dataclass(frozen=True, kw_only=True)
class XhtmlEdit:
    old_text: str
    new_text: str


def apply_xhtml_edits(
    *, xhtml: str, edits: Sequence[XhtmlEdit], document_id: str
) -> str:
    """Apply exact-text replacements located in the original canonical XHTML."""
    locations: list[tuple[int, int, int]] = []
    for edit_index, edit in enumerate(edits):
        start = xhtml.find(edit.old_text)
        if start >= 0:
            locations.append((start, start + len(edit.old_text), edit_index))
    result = xhtml
    for start, end, edit_index in sorted(locations, reverse=True):
        result = result[:start] + edits[edit_index].new_text + result[end:]
    return result


def edit_document(
    *, client: GoogleDocsClient, doc_id: str, edits: Sequence[XhtmlEdit]
) -> int:
    """Edit canonical XHTML and apply the compiled changes to a Google document."""
    response = client.get_document(document_id=doc_id)
    source = document_parser.parse(response)
    xhtml = serialize_document(source)
    edited_xhtml = apply_xhtml_edits(
        xhtml=xhtml,
        edits=edits,
        document_id=doc_id,
    )
    target = deserialize_document(edited_xhtml)
    batch = compile_document(source=source, target=target)
    if batch["requests"]:
        client.batch_update(document_id=doc_id, body=batch)
    return len(edits)
