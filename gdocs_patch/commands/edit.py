from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from gdocs_patch.client import GoogleDocsClient
from gdocs_patch.compiler import compile_document
from gdocs_patch.parsers import document_parser
from gdocs_patch.xhtml import deserialize_document, serialize_document


class XhtmlEditError(Exception):
    """Raised when exact XHTML replacements cannot be applied safely."""


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
        starts: list[int] = []
        start = -1
        while (start := xhtml.find(edit.old_text, start + 1)) >= 0:
            starts.append(start)

        if not starts:
            raise XhtmlEditError(
                f"Could not find the exact text for edits[{edit_index}] in "
                f"{document_id}. The old text must match exactly including all "
                "whitespace and newlines."
            )
        if len(starts) > 1:
            raise XhtmlEditError(
                f"Found {len(starts)} occurrences of the text for edits[{edit_index}] "
                f"in {document_id}. The text must be unique. Please provide more "
                "context to make it unique."
            )

        locations.append((starts[0], starts[0] + len(edit.old_text), edit_index))

    locations.sort()
    for left, right in pairwise(locations):
        _, left_end, left_index = left
        right_start, _, right_index = right
        if right_start < left_end:
            raise XhtmlEditError(
                f"edits[{left_index}] and edits[{right_index}] overlap in "
                f"{document_id}. Merge them into one edit or target disjoint regions."
            )

    result = xhtml
    for start, end, edit_index in reversed(locations):
        result = result[:start] + edits[edit_index].new_text + result[end:]
    if result == xhtml:
        raise XhtmlEditError(
            f"No changes made to {document_id}. The replacements produced identical "
            "content."
        )
    return result


def edit_document(
    *,
    client: GoogleDocsClient,
    doc_id: str,
    edits: Sequence[XhtmlEdit],
    allow_bullet_normalization: bool = False,
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
    identity_fields = (
        "document_id",
        "title",
        "revision_id",
        "suggestions_view_mode",
    )
    changed_identity_fields = [
        field
        for field in identity_fields
        if getattr(target, field) != getattr(source, field)
    ]
    if changed_identity_fields:
        fields = ", ".join(changed_identity_fields)
        raise XhtmlEditError(
            f"Cannot change read-only root metadata in {doc_id}: {fields}."
        )

    batch = compile_document(
        source=source,
        target=target,
        allow_bullet_normalization=allow_bullet_normalization,
    )
    if not batch["requests"]:
        raise XhtmlEditError(
            f"Edits to {doc_id} produced no writable Google Docs changes."
        )
    client.batch_update(document_id=doc_id, body=batch)
    return len(edits)
