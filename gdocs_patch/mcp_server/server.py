import secrets
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.tools import ToolResult
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]
from mcp.types import ToolAnnotations
from pydantic import Field

from gdocs_patch.client import AuthenticationError, GoogleDocsClient, load_credentials
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
    describe_syntax,
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


# FastMCP's static verifier is intended for development and uses a regular
# dictionary lookup. Keep this small verifier so the server compares its one
# configured secret in constant time.
class BearerTokenVerifier(TokenVerifier):
    """Verify the single bearer token configured for this server."""

    def __init__(self, *, token: str) -> None:
        super().__init__()
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._token):
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
) -> ToolResult:
    """Read canonical XHTML lines from a Google document."""
    try:
        client = GoogleDocsClient(credentials=load_credentials())
        content = run_read_document(
            client=client,
            doc_id=document_id,
            offset=offset,
            limit=limit,
        )
    except (AuthenticationError, GoogleAuthError, HttpError) as error:
        raise ToolError(str(error)) from None

    return ToolResult(
        content=content,
        structured_content={
            "document_id": document_id,
            "content": content,
        },
    )


def edit_document(
    *,
    document_id: str,
    edits: list[XhtmlEdit],
    allow_bullet_normalization: bool = False,
) -> ToolResult:
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
    return ToolResult(
        content=f"Successfully replaced {count} {noun} in {document_id}.",
        structured_content={
            "document_id": document_id,
            "blocks_replaced": count,
        },
    )


def write_document(
    *,
    document_id: str,
    content: str,
    allow_bullet_normalization: bool = False,
) -> ToolResult:
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

    return ToolResult(
        content=f"Successfully wrote to {document_id}.",
        structured_content={"document_id": document_id},
    )


def syntax_help(
    *,
    topic: Literal[
        "paragraphs",
        "lists",
        "tables",
        "equations",
        "sections",
    ]
    | None = None,
    reference: bool = False,
) -> ToolResult:
    """Explain the canonical XHTML syntax accepted by gdocs-patch."""
    content = describe_syntax(topic, reference=reference)
    return ToolResult(
        content=content,
        structured_content={
            "topic": topic,
            "reference": reference,
            "content": content,
        },
    )


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
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["document_id", "content"],
            "additionalProperties": False,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(read_document)
    server.tool(
        title="Edit Document",
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "blocks_replaced": {"type": "integer", "minimum": 1},
            },
            "required": ["document_id", "blocks_replaced"],
            "additionalProperties": False,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )(edit_document)
    server.tool(
        title="Write Document",
        output_schema={
            "type": "object",
            "properties": {"document_id": {"type": "string"}},
            "required": ["document_id"],
            "additionalProperties": False,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )(write_document)
    server.tool(
        title="Syntax Help",
        output_schema={
            "type": "object",
            "properties": {
                "topic": {
                    "anyOf": [
                        {
                            "type": "string",
                            "enum": [
                                "paragraphs",
                                "lists",
                                "tables",
                                "equations",
                                "sections",
                            ],
                        },
                        {"type": "null"},
                    ]
                },
                "reference": {"type": "boolean"},
                "content": {"type": "string"},
            },
            "required": ["topic", "reference", "content"],
            "additionalProperties": False,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )(syntax_help)
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
