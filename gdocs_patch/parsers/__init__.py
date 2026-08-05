from importlib import import_module as _import_module

from .base import GDocParseError, GDocParser, JsonObject, JsonValue

_import_module(".paragraph", __name__)
_import_module(".section", __name__)

__all__ = ["GDocParseError", "GDocParser", "JsonObject", "JsonValue"]
