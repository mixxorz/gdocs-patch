import json
from typing import Any, Literal, cast

from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]


def error_value(
    error: object, *, kind: Literal["input", "auth", "transport"]
) -> dict[str, Any]:
    return {"error": {"type": kind, "message": str(error)}}


def api_error_value(error: HttpError) -> dict[str, Any]:
    text = error.content.decode("utf-8", errors="replace")
    try:
        payload: Any = json.loads(text)
    except ValueError:
        payload = text
    status = cast(int, cast(Any, error).resp.status)
    return {"error": {"http_status": status, "payload": payload}}


def error_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)
