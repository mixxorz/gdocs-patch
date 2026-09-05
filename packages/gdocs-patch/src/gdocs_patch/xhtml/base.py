from typing_extensions import Never

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
GDOCS_NAMESPACE = "urn:gdocs-patch:xhtml:1"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
MAX_XHTML_CHARACTERS = 10_000_000
MAX_ELEMENT_DEPTH = 128


class XHTMLParseError(ValueError):
    pass


def xhtml_name(local_name: str) -> str:
    return f"{{{XHTML_NAMESPACE}}}{local_name}"


def gdocs_name(local_name: str) -> str:
    return f"{{{GDOCS_NAMESPACE}}}{local_name}"


def parse_error(path: str, message: str, *, cause: ValueError | None = None) -> Never:
    error = XHTMLParseError(f"{path}: {message}")
    if cause is None:
        raise error
    raise error from cause


def display_name(name: str) -> str:
    if name.startswith(f"{{{GDOCS_NAMESPACE}}}"):
        return f"g:{name.removeprefix(f'{{{GDOCS_NAMESPACE}}}')}"
    if name.startswith(f"{{{XHTML_NAMESPACE}}}"):
        return name.removeprefix(f"{{{XHTML_NAMESPACE}}}")
    return name
