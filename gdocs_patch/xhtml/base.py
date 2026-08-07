from collections.abc import Collection, Iterable
from typing import Never
from xml.etree import ElementTree

from gdocs_patch.models import UNSET, UnsetType

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
GDOCS_NAMESPACE = "urn:gdocs-patch:xhtml:1"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'


class XHTMLParseError(ValueError):
    pass


def xhtml_name(local_name: str) -> str:
    return f"{{{XHTML_NAMESPACE}}}{local_name}"


def gdocs_name(local_name: str) -> str:
    return f"{{{GDOCS_NAMESPACE}}}{local_name}"


def parse_error(path: str, message: str) -> Never:
    raise XHTMLParseError(f"{path}: {message}")


def required_string(element: ElementTree.Element, name: str, path: str) -> str:
    value = element.get(name)
    if value is None:
        parse_error(path, f"missing required attribute {display_name(name)}")
    return value


def optional_string(element: ElementTree.Element, name: str) -> str | UnsetType:
    value = element.get(name)
    return UNSET if value is None else value


def parse_boolean(value: str, path: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    parse_error(path, f"expected 'true' or 'false', got {value!r}")


def parse_integer(value: str, path: str) -> int:
    try:
        return int(value)
    except ValueError:
        parse_error(path, f"expected an integer, got {value!r}")


def parse_float(value: str, path: str) -> float:
    try:
        result = float(value)
    except ValueError:
        parse_error(path, f"expected a float, got {value!r}")
    if result != result or result in (float("inf"), float("-inf")):
        parse_error(path, f"expected a finite float, got {value!r}")
    return result


def parse_allowed(value: str, allowed: Collection[str], path: str) -> str:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        parse_error(path, f"expected one of {choices}, got {value!r}")
    return value


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
