import hashlib
import secrets
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]
from mcp.types import ToolAnnotations
from pydantic import Field

from gdocs_patch.client import AuthenticationError, GoogleDocsClient, load_credentials
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
)
from gdocs_patch.commands import (
    edit_document as run_edit_document,
)
from gdocs_patch.commands import (
    read_document as run_read_document,
)
from gdocs_patch.commands import (
    write_document as run_write_document,
)
from gdocs_patch.compiler import UnsupportedTransformation
from gdocs_patch.xhtml import XHTMLParseError


class BearerTokenVerifier(TokenVerifier):
    """Verify the single bearer token configured for this server."""

    def __init__(self, *, token: str) -> None:
        super().__init__()
        self._token_digest: bytes = hashlib.sha256(token.encode("utf-8")).digest()

    async def verify_token(self, token: str) -> AccessToken | None:
        candidate_digest = hashlib.sha256(token.encode("utf-8")).digest()
        if not secrets.compare_digest(candidate_digest, self._token_digest):
            return None
        return AccessToken(
            token=token,
            client_id="gdocs-patch-mcp",
            scopes=[],
        )


def read_document(
    *,
    document_id: str,
    offset: Annotated[int, Field(ge=1)] = 1,
    limit: Annotated[int | None, Field(gt=0)] = None,
) -> str:
    """Read canonical XHTML lines from a Google document."""
    try:
        client = GoogleDocsClient(credentials=load_credentials())
        return run_read_document(
            client=client,
            doc_id=document_id,
            offset=offset,
            limit=limit,
        )
    except (AuthenticationError, GoogleAuthError, HttpError) as error:
        raise ToolError(str(error)) from None


def edit_document(
    *,
    document_id: str,
    edits: list[XhtmlEdit],
    allow_bullet_normalization: bool = False,
) -> str:
    """Apply exact canonical-XHTML replacements to a Google document."""
    if not edits:
        raise ToolError("edits must contain at least one replacement.")
    for edit_index, edit in enumerate(edits):
        if not edit.old_text:
            raise ToolError(
                f"edits[{edit_index}].old_text must not be empty in {document_id}."
            )

    try:
        client = GoogleDocsClient(credentials=load_credentials())
        count = run_edit_document(
            client=client,
            doc_id=document_id,
            edits=edits,
            allow_bullet_normalization=allow_bullet_normalization,
        )
    except (
        XhtmlEditError,
        XHTMLParseError,
        UnsupportedTransformation,
        AuthenticationError,
        GoogleAuthError,
        HttpError,
    ) as error:
        raise ToolError(str(error)) from None

    noun = "block" if count == 1 else "blocks"
    return f"Successfully replaced {count} {noun} in {document_id}."


def write_document(
    *,
    document_id: str,
    content: str,
    allow_bullet_normalization: bool = False,
) -> str:
    """Apply complete target XHTML to a Google document."""
    try:
        client = GoogleDocsClient(credentials=load_credentials())
        run_write_document(
            client=client,
            doc_id=document_id,
            content=content,
            allow_bullet_normalization=allow_bullet_normalization,
        )
    except (
        XHTMLParseError,
        UnsupportedTransformation,
        AuthenticationError,
        GoogleAuthError,
        HttpError,
    ) as error:
        raise ToolError(str(error)) from None

    return f"Successfully wrote to {document_id}."


def create_server(*, token: str) -> FastMCP:
    """Create the configured gdocs-patch MCP server."""
    server = FastMCP(
        name="gdocs-patch",
        instructions=(
            "Read and update Google Docs through canonical XHTML. Read a document "
            "before editing it, and use syntax_help when XHTML syntax is unclear."
        ),
        auth=BearerTokenVerifier(token=token),
        mask_error_details=True,
        strict_input_validation=True,
    )
    server.tool(
        title="Read Document",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(read_document)
    server.tool(
        title="Edit Document",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )(edit_document)
    server.tool(
        title="Write Document",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(write_document)
    return server


def run_server(*, host: str, port: int, token: str) -> None:
    """Serve gdocs-patch using FastMCP's Streamable HTTP transport."""
    server = create_server(token=token)
    server.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
    )
