from gdocs_patch.client import GoogleDocsClient
from gdocs_patch.parsers import document_parser
from gdocs_patch.xhtml import serialize_document


def read_document(
    *,
    client: GoogleDocsClient,
    doc_id: str,
    offset: int = 1,
    limit: int | None = None,
) -> str:
    """Fetch a Google document and return the requested canonical XHTML lines."""
    response = client.get_document(document_id=doc_id)
    document = document_parser.parse(response)
    lines = serialize_document(document).splitlines(keepends=True)
    start = offset - 1
    stop = None if limit is None else start + limit
    return "".join(lines[start:stop])
