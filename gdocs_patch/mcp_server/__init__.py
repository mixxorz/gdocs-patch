import argparse
import os
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the optional hosted MCP server."""
    parser = argparse.ArgumentParser(
        prog="gdocs-patch-mcp",
        description="Serve gdocs-patch tools over authenticated MCP HTTP.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    try:
        # Keep CLI-only installs dependency-free.
        # lint-ignore: NoInlineImport
        from gdocs_patch.mcp_server.server import run_server
    except ModuleNotFoundError as error:
        if error.name != "fastmcp":
            raise
        print(
            "gdocs-patch-mcp: error: MCP support is not installed. "
            "Install it with: uv tool install 'gdocs-patch[mcp]'",
            file=sys.stderr,
        )
        return 1

    token = os.environ.get("GDOCS_PATCH_MCP_TOKEN")
    if not token:
        print(
            "gdocs-patch-mcp: error: GDOCS_PATCH_MCP_TOKEN must be set.",
            file=sys.stderr,
        )
        return 1

    run_server(host=args.host, port=args.port, token=token)
    return 0
