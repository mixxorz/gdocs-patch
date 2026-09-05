from gdocs_patch.client import GoogleDocsClient
from gdocs_patch.compiler import compile_document
from gdocs_patch.parsers import document_parser
from gdocs_patch.xhtml import deserialize_document


def write_document(
    *,
    client: GoogleDocsClient,
    doc_id: str,
    content: str,
    allow_bullet_normalization: bool = False,
) -> None:
    """Compile target XHTML against a Google document and apply its changes."""
    target = deserialize_document(content)
    response = client.get_document(document_id=doc_id)
    source = document_parser.parse(response)
    batch = compile_document(
        source=source,
        target=target,
        allow_bullet_normalization=allow_bullet_normalization,
    )
    if batch["requests"]:
        client.batch_update(document_id=doc_id, body=batch)
