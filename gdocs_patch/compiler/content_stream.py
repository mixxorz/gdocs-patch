from gdocs_patch.models import UNSET, ParagraphStyle, TextStyle, UnsetType


class TextUnit:
    def __init__(
        self,
        *,
        content: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.content = content
        self.text_style = text_style

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


class ParagraphBoundary:
    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
        paragraph_style: ParagraphStyle | UnsetType = UNSET,
    ) -> None:
        self.text_style = text_style
        self.paragraph_style = paragraph_style

    @property
    def utf16_width(self) -> int:
        return 1


class ContentStream:
    def __init__(self, *, items: list[TextUnit | ParagraphBoundary]) -> None:
        self.items = items

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)
