class TextUnit:
    def __init__(self, *, content: str) -> None:
        self.content = content

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


class ParagraphBoundary:
    @property
    def utf16_width(self) -> int:
        return 1


class ContentStream:
    def __init__(self, *, items: list[TextUnit | ParagraphBoundary]) -> None:
        self.items = items

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)
