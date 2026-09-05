import json
import os
import secrets
from collections.abc import Callable
from typing import Any, cast

import httplib2
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.tools import ToolResult
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]

from gsheets_patch.auth import AuthenticationError, load_credentials
from gsheets_patch.client import GoogleSheetsClient
from gsheets_patch.errors import api_error_value, error_json, error_value
from gsheets_patch.mcp_server import MCPTokenNotConfiguredError
from gsheets_patch.schema import describe_schema


class BearerTokenVerifier(TokenVerifier):
    def __init__(self) -> None:
        super().__init__()
        token = os.environ.get("GSHEETS_PATCH_MCP_TOKEN")
        if not token:
            raise MCPTokenNotConfiguredError("GSHEETS_PATCH_MCP_TOKEN must be set.")
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._token):
            return None
        return AccessToken(token=token, client_id="gsheets-patch-mcp", scopes=[])


server = FastMCP(
    name="gsheets-patch",
    instructions=(
        "Call selected Google Sheets v4 methods with native request bodies and "
        "responses. Use schema to inspect native method and body definitions."
    ),
    auth=BearerTokenVerifier(),
    mask_error_details=False,
    strict_input_validation=True,
)


def call_api(native_method: str, **params: Any) -> ToolResult:
    # Keep transport/error adaptation here so tools only describe their API call.
    try:
        result = GoogleSheetsClient(credentials=load_credentials()).call(
            native_method, **params
        )
    except HttpError as error:
        raise ToolError(error_json(api_error_value(error))) from None
    except (ValueError, TypeError) as error:
        raise ToolError(error_json(error_value(error, kind="input"))) from None
    except (AuthenticationError, GoogleAuthError) as error:
        raise ToolError(error_json(error_value(error, kind="auth"))) from None
    except (httplib2.HttpLib2Error, OSError) as error:
        raise ToolError(error_json(error_value(error, kind="transport"))) from None
    return ToolResult(
        content=json.dumps(result, ensure_ascii=False), structured_content=result
    )


def tool(*, read_only: bool = False) -> Callable[[Callable[..., ToolResult]], Any]:
    return cast(
        Callable[[Callable[..., ToolResult]], Any],
        server.tool(
            annotations={
                "readOnlyHint": read_only,
                "destructiveHint": not read_only,
                "idempotentHint": read_only,
                "openWorldHint": True,
            }
        ),
    )


@tool(read_only=True)
def get_spreadsheet(
    *,
    spreadsheet_id: str,
    include_grid_data: bool | None = None,
    exclude_tables_in_banded_ranges: bool | None = None,
    ranges: list[str] | None = None,
    fields: str | None = None,
) -> ToolResult:
    """Get spreadsheet metadata, properties, and optionally grid data."""
    return call_api(
        "spreadsheets.get",
        spreadsheet_id=spreadsheet_id,
        include_grid_data=include_grid_data,
        exclude_tables_in_banded_ranges=exclude_tables_in_banded_ranges,
        ranges=ranges,
        fields=fields,
    )


@tool(read_only=True)
def get_spreadsheet_by_data_filter(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Get spreadsheet data selected by native data filters."""
    return call_api(
        "spreadsheets.getByDataFilter",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool()
def batch_update_spreadsheet(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Apply a native spreadsheets.batchUpdate request."""
    return call_api(
        "spreadsheets.batchUpdate",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool(read_only=True)
def get_values(
    *,
    spreadsheet_id: str,
    range: str,
    major_dimension: str | None = None,
    value_render_option: str | None = None,
    date_time_render_option: str | None = None,
    fields: str | None = None,
) -> ToolResult:
    """Get values from one range."""
    return call_api(
        "spreadsheets.values.get",
        spreadsheet_id=spreadsheet_id,
        range=range,
        major_dimension=major_dimension,
        value_render_option=value_render_option,
        date_time_render_option=date_time_render_option,
        fields=fields,
    )


@tool(read_only=True)
def batch_get_values(
    *,
    spreadsheet_id: str,
    ranges: list[str] | None = None,
    major_dimension: str | None = None,
    value_render_option: str | None = None,
    date_time_render_option: str | None = None,
    fields: str | None = None,
) -> ToolResult:
    """Get values from multiple ranges."""
    return call_api(
        "spreadsheets.values.batchGet",
        spreadsheet_id=spreadsheet_id,
        ranges=ranges,
        major_dimension=major_dimension,
        value_render_option=value_render_option,
        date_time_render_option=date_time_render_option,
        fields=fields,
    )


@tool(read_only=True)
def batch_get_values_by_data_filter(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Get values selected by native data filters."""
    return call_api(
        "spreadsheets.values.batchGetByDataFilter",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool()
def update_values(
    *,
    spreadsheet_id: str,
    range: str,
    body: dict[str, Any],
    value_input_option: str,
    include_values_in_response: bool | None = None,
    response_value_render_option: str | None = None,
    response_date_time_render_option: str | None = None,
    fields: str | None = None,
) -> ToolResult:
    """Update values in one range."""
    return call_api(
        "spreadsheets.values.update",
        spreadsheet_id=spreadsheet_id,
        range=range,
        body=body,
        value_input_option=value_input_option,
        include_values_in_response=include_values_in_response,
        response_value_render_option=response_value_render_option,
        response_date_time_render_option=response_date_time_render_option,
        fields=fields,
    )


@tool()
def batch_update_values(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Update values in multiple ranges."""
    return call_api(
        "spreadsheets.values.batchUpdate",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool()
def batch_update_values_by_data_filter(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Update values selected by native data filters."""
    return call_api(
        "spreadsheets.values.batchUpdateByDataFilter",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool()
def append_values(
    *,
    spreadsheet_id: str,
    range: str,
    body: dict[str, Any],
    value_input_option: str,
    insert_data_option: str | None = None,
    include_values_in_response: bool | None = None,
    response_value_render_option: str | None = None,
    response_date_time_render_option: str | None = None,
    fields: str | None = None,
) -> ToolResult:
    """Append values after the detected table in a range."""
    return call_api(
        "spreadsheets.values.append",
        spreadsheet_id=spreadsheet_id,
        range=range,
        body=body,
        value_input_option=value_input_option,
        insert_data_option=insert_data_option,
        include_values_in_response=include_values_in_response,
        response_value_render_option=response_value_render_option,
        response_date_time_render_option=response_date_time_render_option,
        fields=fields,
    )


@tool()
def clear_values(
    *, spreadsheet_id: str, range: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Clear values in one range."""
    return call_api(
        "spreadsheets.values.clear",
        spreadsheet_id=spreadsheet_id,
        range=range,
        body=body,
        fields=fields,
    )


@tool()
def batch_clear_values(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Clear values in multiple ranges."""
    return call_api(
        "spreadsheets.values.batchClear",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool()
def batch_clear_values_by_data_filter(
    *, spreadsheet_id: str, body: dict[str, Any], fields: str | None = None
) -> ToolResult:
    """Clear values selected by native data filters."""
    return call_api(
        "spreadsheets.values.batchClearByDataFilter",
        spreadsheet_id=spreadsheet_id,
        body=body,
        fields=fields,
    )


@tool(read_only=True)
def schema(name: str | None = None) -> ToolResult:
    """List or look up supported native Sheets methods and schemas."""
    try:
        result = describe_schema(name)
    except KeyError:
        raise ToolError(
            error_json(error_value(f"Unknown schema: {name}", kind="input"))
        ) from None
    return ToolResult(
        content=json.dumps(result, ensure_ascii=False), structured_content=result
    )


def run_server(*, host: str, port: int) -> None:
    server.run(transport="http", host=host, port=port, path="/mcp")
