import re
from collections.abc import Callable, Collection, Iterable
from typing import Never, cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    BookmarkLink,
    Color,
    Dimension,
    HeadingLink,
    Link,
    TabLink,
    TextStyle,
    UnsetType,
    UrlLink,
)

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


def optional_string(element: ElementTree.Element, name: str) -> str | UnsetType:
    value = element.get(name)
    return UNSET if value is None else value


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


_TEXT_STYLE_BOOLEAN_FIELDS = {
    "bold": gdocs_name("bold"),
    "italic": gdocs_name("italic"),
    "underline": gdocs_name("underline"),
    "strikethrough": gdocs_name("strikethrough"),
    "small_caps": gdocs_name("small-caps"),
}
_TEXT_STYLE_ATTRIBUTES = {
    *_TEXT_STYLE_BOOLEAN_FIELDS.values(),
    gdocs_name("baseline-offset"),
    gdocs_name("font-size"),
    gdocs_name("font-family"),
    gdocs_name("font-weight"),
    gdocs_name("foreground-red"),
    gdocs_name("foreground-green"),
    gdocs_name("foreground-blue"),
    gdocs_name("foreground-color"),
    gdocs_name("background-red"),
    gdocs_name("background-green"),
    gdocs_name("background-blue"),
    gdocs_name("background-color"),
}
_LINK_ATTRIBUTES = {
    "href",
    gdocs_name("tab-id"),
    gdocs_name("bookmark-id"),
    gdocs_name("heading-id"),
}


def text_style_attributes() -> set[str]:
    return set(_TEXT_STYLE_ATTRIBUTES)


def encode_link(element: ElementTree.Element, link: Link) -> ElementTree.Element:
    anchor = ElementTree.Element(xhtml_name("a"))
    if isinstance(link, UrlLink):
        anchor.set("href", require_string(link.url, "UrlLink.url"))
    elif isinstance(link, TabLink):
        anchor.set(gdocs_name("tab-id"), require_string(link.tab_id, "TabLink.tab_id"))
    elif isinstance(link, BookmarkLink):
        anchor.set(
            gdocs_name("bookmark-id"),
            require_string(link.bookmark_id, "BookmarkLink.bookmark_id"),
        )
        if link.tab_id is not UNSET:
            anchor.set(
                gdocs_name("tab-id"),
                require_string(link.tab_id, "BookmarkLink.tab_id"),
            )
    elif isinstance(link, HeadingLink):
        anchor.set(
            gdocs_name("heading-id"),
            require_string(link.heading_id, "HeadingLink.heading_id"),
        )
        if link.tab_id is not UNSET:
            anchor.set(
                gdocs_name("tab-id"),
                require_string(link.tab_id, "HeadingLink.tab_id"),
            )
    else:
        raise ValueError(f"unsupported link type {type(link).__name__}")
    anchor.append(element)
    return anchor


def encode_text_style(
    element: ElementTree.Element, style: TextStyle | UnsetType
) -> ElementTree.Element:
    if style is UNSET:
        return element
    style = cast(TextStyle, style)
    boolean_values = (
        (style.bold, gdocs_name("bold")),
        (style.italic, gdocs_name("italic")),
        (style.underline, gdocs_name("underline")),
        (style.strikethrough, gdocs_name("strikethrough")),
        (style.small_caps, gdocs_name("small-caps")),
    )
    for value, attribute in boolean_values:
        if value is not UNSET:
            boolean = require_boolean(value, f"TextStyle.{display_name(attribute)}")
            element.set(attribute, "true" if boolean else "false")
    if style.baseline_offset is not UNSET:
        element.set(
            gdocs_name("baseline-offset"),
            require_enum(
                style.baseline_offset,
                {"BASELINE_OFFSET_UNSPECIFIED", "NONE", "SUPERSCRIPT", "SUBSCRIPT"},
                "TextStyle.baseline_offset",
            ),
        )
    if style.font_size is not UNSET:
        if not isinstance(style.font_size, Dimension):
            raise ValueError("TextStyle.font_size must be a Dimension")
        element.set(
            gdocs_name("font-size"),
            format_number(
                require_number(style.font_size.magnitude, "Dimension.magnitude")
            ),
        )
    if style.font_family is not UNSET:
        element.set(
            gdocs_name("font-family"),
            require_string(style.font_family, "TextStyle.font_family"),
        )
    if style.font_weight is not UNSET:
        element.set(
            gdocs_name("font-weight"),
            str(require_integer(style.font_weight, "TextStyle.font_weight")),
        )
    encode_text_color(element, "foreground", style.foreground_color)
    encode_text_color(element, "background", style.background_color)
    if style.link is not UNSET:
        return encode_link(element, cast(Link, style.link))
    return element


def encode_text_color(
    element: ElementTree.Element, prefix: str, color: Color | None | UnsetType
) -> None:
    if color is UNSET:
        return
    if color is None:
        element.set(gdocs_name(f"{prefix}-color"), "transparent")
        return
    if not isinstance(color, Color):
        raise ValueError(f"TextStyle.{prefix}_color must be a Color or None")
    element.set(
        gdocs_name(f"{prefix}-red"),
        format_number(require_number(color.red, f"Color.{prefix}.red")),
    )
    element.set(
        gdocs_name(f"{prefix}-green"),
        format_number(require_number(color.green, f"Color.{prefix}.green")),
    )
    element.set(
        gdocs_name(f"{prefix}-blue"),
        format_number(require_number(color.blue, f"Color.{prefix}.blue")),
    )


def format_number(value: int | float) -> str:
    value = require_number(value, "number")
    if value == 0:
        return "0"
    text = repr(value)
    return text[:-2] if text.endswith(".0") else text


def decode_link(element: ElementTree.Element, path: str) -> Link:
    validate_attributes(element, _LINK_ATTRIBUTES, path)
    href = element.get("href")
    tab_id = element.get(gdocs_name("tab-id"))
    bookmark_id = element.get(gdocs_name("bookmark-id"))
    heading_id = element.get(gdocs_name("heading-id"))
    primary_count = sum(value is not None for value in (href, bookmark_id, heading_id))
    if href is not None and primary_count == 1 and tab_id is None:
        return UrlLink(url=href)
    if bookmark_id is not None and primary_count == 1:
        return BookmarkLink(
            bookmark_id=bookmark_id, tab_id=UNSET if tab_id is None else tab_id
        )
    if heading_id is not None and primary_count == 1:
        return HeadingLink(
            heading_id=heading_id, tab_id=UNSET if tab_id is None else tab_id
        )
    if tab_id is not None and primary_count == 0:
        return TabLink(tab_id=tab_id)
    parse_error(path, "invalid link target attribute combination")


def parse_text_style(
    element: ElementTree.Element, path: str
) -> Callable[[Link | UnsetType], TextStyle | UnsetType]:
    def optional_boolean(name: str) -> bool | UnsetType:
        raw = element.get(gdocs_name(name))
        if raw is None:
            return UNSET
        return parse_boolean(raw, f"{path}/@g:{name}")

    bold = optional_boolean("bold")
    italic = optional_boolean("italic")
    underline = optional_boolean("underline")
    strikethrough = optional_boolean("strikethrough")
    small_caps = optional_boolean("small-caps")
    raw_baseline = element.get(gdocs_name("baseline-offset"))
    baseline_offset = (
        UNSET
        if raw_baseline is None
        else parse_allowed(
            raw_baseline,
            {"BASELINE_OFFSET_UNSPECIFIED", "NONE", "SUPERSCRIPT", "SUBSCRIPT"},
            f"{path}/@g:baseline-offset",
        )
    )
    raw_font_size = element.get(gdocs_name("font-size"))
    font_size = (
        UNSET
        if raw_font_size is None
        else Dimension(
            magnitude=parse_float(raw_font_size, f"{path}/@g:font-size"), unit="PT"
        )
    )
    font_family = optional_string(element, gdocs_name("font-family"))
    raw_weight = element.get(gdocs_name("font-weight"))
    font_weight = (
        UNSET
        if raw_weight is None
        else parse_integer(raw_weight, f"{path}/@g:font-weight")
    )
    foreground_color = decode_text_color(element, "foreground", path)
    background_color = decode_text_color(element, "background", path)
    fields = (
        bold,
        italic,
        underline,
        strikethrough,
        small_caps,
        baseline_offset,
        font_size,
        font_family,
        font_weight,
        foreground_color,
        background_color,
    )

    def construct(link: Link | UnsetType) -> TextStyle | UnsetType:
        if all(value is UNSET for value in (*fields, link)):
            return UNSET
        return construct_model(
            path,
            lambda: TextStyle(
                bold=bold,
                italic=italic,
                underline=underline,
                strikethrough=strikethrough,
                small_caps=small_caps,
                baseline_offset=baseline_offset,  # type: ignore[arg-type]
                font_size=font_size,
                font_family=font_family,
                font_weight=font_weight,
                foreground_color=foreground_color,
                background_color=background_color,
                link=link,
            ),
        )

    return construct


def decode_text_style(
    element: ElementTree.Element, link: Link | UnsetType, path: str
) -> TextStyle | UnsetType:
    return parse_text_style(element, path)(link)


def decode_text_color(
    element: ElementTree.Element, prefix: str, path: str
) -> Color | None | UnsetType:
    marker_name = gdocs_name(f"{prefix}-color")
    marker = element.get(marker_name)
    names = [
        gdocs_name(f"{prefix}-{component}") for component in ("red", "green", "blue")
    ]
    components = [element.get(name) for name in names]
    parsed_components = [
        None if value is None else parse_float(value, f"{path}/@{display_name(name)}")
        for name, value in zip(names, components, strict=True)
    ]
    if marker is not None:
        if marker != "transparent" or any(value is not None for value in components):
            parse_error(path, f"invalid {prefix} color")
        return None
    if not any(value is not None for value in components):
        return UNSET
    if not all(value is not None for value in components):
        parse_error(path, f"opaque {prefix} color requires red, green, and blue")
    red, green, blue = cast("list[float]", parsed_components)
    try:
        return Color(red=red, green=green, blue=blue)
    except ValueError as error:
        parse_error(path, str(error), cause=error)


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
