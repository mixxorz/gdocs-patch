import argparse
import sys
from collections.abc import Sequence


class MCPTokenNotConfiguredError(RuntimeError):
    """Raised when the MCP bearer token is missing."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gsheets-patch-mcp",
        description="Serve gsheets-patch tools over authenticated MCP HTTP.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        # Keep the optional MCP dependency out of base CLI imports.
        # lint-ignore: NoInlineImport
        from gsheets_patch.mcp_server.server import run_server
    except MCPTokenNotConfiguredError as error:
        print(f"gsheets-patch-mcp: error: {error}", file=sys.stderr)
        return 1
    except ModuleNotFoundError as error:
        if error.name != "fastmcp":
            raise
        print(
            "gsheets-patch-mcp: error: MCP support is not installed. "
            "Install it with: uv tool install 'gsheets-patch[mcp]'",
            file=sys.stderr,
        )
        return 1
    run_server(host=args.host, port=args.port)
    return 0
