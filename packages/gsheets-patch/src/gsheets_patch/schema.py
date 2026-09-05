import json
from importlib.resources import files
from typing import Any, cast

METHODS = (
    "spreadsheets.get",
    "spreadsheets.getByDataFilter",
    "spreadsheets.batchUpdate",
    "spreadsheets.values.get",
    "spreadsheets.values.batchGet",
    "spreadsheets.values.batchGetByDataFilter",
    "spreadsheets.values.update",
    "spreadsheets.values.batchUpdate",
    "spreadsheets.values.batchUpdateByDataFilter",
    "spreadsheets.values.append",
    "spreadsheets.values.clear",
    "spreadsheets.values.batchClear",
    "spreadsheets.values.batchClearByDataFilter",
)


def _document() -> dict[str, Any]:
    path = files("googleapiclient.discovery_cache.documents").joinpath("sheets.v4.json")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def describe_schema(name: str | None = None) -> dict[str, Any]:
    """List supported methods and native schemas, or return one definition."""
    document = _document()
    schemas = cast(dict[str, Any], document["schemas"])
    if name is None:
        return {"methods": list(METHODS), "schemas": sorted(schemas)}
    if name in schemas:
        return {"name": name, "kind": "schema", "definition": schemas[name]}
    if name in METHODS:
        node: dict[str, Any] = document
        parts = name.split(".")
        for resource in parts[:-1]:
            node = cast(dict[str, Any], node["resources"])[resource]
        definition = cast(dict[str, Any], node["methods"])[parts[-1]]
        return {"name": name, "kind": "method", "definition": definition}
    raise KeyError(name)
