from gdocs_patch.models.base import Model


class TextUnit(Model):
    def __init__(self, *, content: str) -> None:
        self.content = content

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


class ParagraphBoundary(Model):
    @property
    def utf16_width(self) -> int:
        return 1


class ContentStream(Model):
    def __init__(self, *, items: list[TextUnit | ParagraphBoundary]) -> None:
        self.items = items

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)
