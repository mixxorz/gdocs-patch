import asyncio
import json
import os
from typing import Any

import pytest
from fastmcp import Client

os.environ.setdefault("GSHEETS_PATCH_MCP_TOKEN", "offline-mcp-token")

from gsheets_patch.mcp_server import server as mcp_module  # noqa: E402

EXPECTED_TOOLS = {
    "get_spreadsheet",
    "get_spreadsheet_by_data_filter",
    "batch_update_spreadsheet",
    "get_values",
    "batch_get_values",
    "batch_get_values_by_data_filter",
    "update_values",
    "batch_update_values",
    "batch_update_values_by_data_filter",
    "append_values",
    "clear_values",
    "batch_clear_values",
    "batch_clear_values_by_data_filter",
    "schema",
}


def run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


def test_native_client_discovers_exact_tool_surface() -> None:
    async def discover() -> set[str]:
        async with Client(mcp_module.server) as client:
            return {tool.name for tool in await client.list_tools()}

    assert run(discover()) == EXPECTED_TOOLS


def test_native_client_returns_matching_structured_and_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubClient:
        def __init__(self, **_: Any) -> None:
            pass

        def call(self, method: str, **arguments: Any) -> dict[str, Any]:
            assert (method, arguments) == (
                "spreadsheets.values.get",
                {
                    "spreadsheet_id": "s",
                    "range": "'Données'!A1",
                    "major_dimension": None,
                    "value_render_option": None,
                    "date_time_render_option": None,
                    "fields": None,
                },
            )
            return {"values": [["é"]]}

    monkeypatch.setattr(mcp_module, "GoogleSheetsClient", StubClient)
    monkeypatch.setattr(mcp_module, "load_credentials", object)

    async def invoke() -> Any:
        async with Client(mcp_module.server) as client:
            return await client.call_tool(
                "get_values", {"spreadsheet_id": "s", "range": "'Données'!A1"}
            )

    result = run(invoke())
    assert result.structured_content == {"values": [["é"]]}
    assert json.loads(result.content[0].text) == result.structured_content
    assert not result.is_error


def test_native_client_marks_tool_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mcp_module,
        "load_credentials",
        lambda: (_ for _ in ()).throw(OSError("offline")),
    )

    async def invoke() -> Any:
        async with Client(mcp_module.server) as client:
            return await client.call_tool(
                "get_spreadsheet", {"spreadsheet_id": "s"}, raise_on_error=False
            )

    result = run(invoke())
    assert result.is_error
    assert json.loads(result.content[0].text) == {
        "error": {"type": "transport", "message": "offline"}
    }


def test_bearer_verifier_accepts_only_configured_token() -> None:
    verifier = mcp_module.BearerTokenVerifier()
    assert run(verifier.verify_token("wrong")) is None
    accepted = run(verifier.verify_token("offline-mcp-token"))
    assert accepted is not None and accepted.client_id == "gsheets-patch-mcp"
