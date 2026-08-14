import hashlib
import secrets

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier


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


def create_server(*, token: str) -> FastMCP:
    """Create the configured gdocs-patch MCP server."""
    return FastMCP(
        name="gdocs-patch",
        instructions=(
            "Read and update Google Docs through canonical XHTML. Read a document "
            "before editing it, and use syntax_help when XHTML syntax is unclear."
        ),
        auth=BearerTokenVerifier(token=token),
        mask_error_details=True,
        strict_input_validation=True,
    )


def run_server(*, host: str, port: int, token: str) -> None:
    """Serve gdocs-patch using FastMCP's Streamable HTTP transport."""
    server = create_server(token=token)
    server.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
    )
