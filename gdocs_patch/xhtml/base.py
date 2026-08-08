import re
from collections.abc import Callable, Collection, Iterable
from typing import Never
from xml.etree import ElementTree

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
GDOCS_NAMESPACE = "urn:gdocs-patch:xhtml:1"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
MAX_XHTML_CHARACTERS = 10_000_000
MAX_ELEMENT_DEPTH = 256


class XHTMLParseError(ValueError):
    pass


def construct_model[ModelT](path: str, factory: Callable[[], ModelT]) -> ModelT:
    try:
        return factory()
    except ValueError as error:
        parse_error(path, str(error), cause=error)


def xhtml_name(local_name: str) -> str:
    return f"{{{XHTML_NAMESPACE}}}{local_name}"


def gdocs_name(local_name: str) -> str:
    return f"{{{GDOCS_NAMESPACE}}}{local_name}"


def parse_error(path: str, message: str, *, cause: ValueError | None = None) -> Never:
    error = XHTMLParseError(f"{path}: {message}")
    if cause is None:
        raise error
    raise error from cause


def required_string(element: ElementTree.Element, name: str, path: str) -> str:
    value = element.get(name)
    if value is None:
        parse_error(path, f"missing required attribute {display_name(name)}")
    return value


def parse_boolean(value: str, path: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    parse_error(path, f"expected 'true' or 'false', got {value!r}")


_CANONICAL_INTEGER = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
_CANONICAL_FLOAT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?\Z")


def parse_integer(value: str, path: str) -> int:
    if _CANONICAL_INTEGER.fullmatch(value) is None:
        parse_error(path, f"expected a canonical integer, got {value!r}")
    return int(value)


def parse_float(value: str, path: str) -> float:
    if _CANONICAL_FLOAT.fullmatch(value) is None:
        parse_error(path, f"expected a float in canonical finite form, got {value!r}")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        parse_error(path, f"expected a float in canonical finite form, got {value!r}")
    if format_number(result) != value:
        parse_error(path, f"expected a float in canonical finite form, got {value!r}")
    return result


def parse_allowed(value: str, allowed: Collection[str], path: str) -> str:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        parse_error(path, f"expected one of {choices}, got {value!r}")
    return value


def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def require_boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean")
    return value


def require_integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    return value


def require_number(value: object, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be an integer or float")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{field} must be finite")
    return value


def require_enum(value: object, allowed: Collection[str], field: str) -> str:
    result = require_string(value, field)
    if result not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{field} must be one of {choices}")
    return result


def require_list(value: object, field: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")


def require_dict(value: object, field: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a dictionary")


def validate_attributes(
    element: ElementTree.Element, allowed: Collection[str], path: str
) -> None:
    unknown = set(element.attrib) - set(allowed)
    if unknown:
        name = min(unknown)
        if name.startswith("{") and not name.startswith(
            (f"{{{XHTML_NAMESPACE}}}", f"{{{GDOCS_NAMESPACE}}}")
        ):
            parse_error(
                path, f"unsupported namespace in attribute {display_name(name)}"
            )
        parse_error(path, f"unknown attribute {display_name(name)}")


def extract_one_child(
    children: Iterable[ElementTree.Element],
    name: str,
    path: str,
    *,
    required: bool = False,
) -> ElementTree.Element | None:
    matches = [child for child in children if child.tag == name]
    if len(matches) > 1:
        parse_error(path, f"expected at most one {display_name(name)} child")
    if not matches:
        if required:
            parse_error(path, f"missing required {display_name(name)} child")
        return None
    return matches[0]


def validate_whitespace(element: ElementTree.Element, path: str) -> None:
    if element.text is not None and element.text.strip():
        parse_error(path, "unexpected text content")
    for child in element:
        if child.tail is not None and child.tail.strip():
            parse_error(path, "unexpected text after child element")


def format_number(value: int | float) -> str:
    value = require_number(value, "number")
    if value == 0:
        return "0"
    text = repr(value)
    return text[:-2] if text.endswith(".0") else text


def display_name(name: str) -> str:
    if name.startswith(f"{{{GDOCS_NAMESPACE}}}"):
        return f"g:{name.removeprefix(f'{{{GDOCS_NAMESPACE}}}')}"
    if name.startswith(f"{{{XHTML_NAMESPACE}}}"):
        return name.removeprefix(f"{{{XHTML_NAMESPACE}}}")
    return name


def _indent_xml(element: ElementTree.Element, level: int = 0) -> None:
    if element.tag == xhtml_name("span"):
        return
    children = list(element)
    if not children:
        return

    indentation = "\n" + "  " * (level + 1)
    if element.text is None or not element.text.strip():
        element.text = indentation
    for child in children:
        _indent_xml(child, level + 1)
        if child.tail is None or not child.tail.strip():
            child.tail = indentation
    children[-1].tail = "\n" + "  " * level
