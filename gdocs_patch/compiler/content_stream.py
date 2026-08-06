from dataclasses import dataclass
from typing import Literal

from gdocs_patch.models import UNSET, Bullet, ParagraphStyle, TextStyle, UnsetType


@dataclass(frozen=True, kw_only=True)
class BulletPreset:
    preset: Literal[
        "BULLET_GLYPH_PRESET_UNSPECIFIED",
        "BULLET_DISC_CIRCLE_SQUARE",
        "BULLET_DIAMONDX_ARROW3D_SQUARE",
        "BULLET_CHECKBOX",
        "BULLET_ARROW_DIAMOND_DISC",
        "BULLET_STAR_CIRCLE_SQUARE",
        "BULLET_ARROW3D_CIRCLE_SQUARE",
        "BULLET_LEFTTRIANGLE_DIAMOND_DISC",
        "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE",
        "BULLET_DIAMOND_CIRCLE_SQUARE",
        "NUMBERED_DECIMAL_ALPHA_ROMAN",
        "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
        "NUMBERED_DECIMAL_NESTED",
        "NUMBERED_UPPERALPHA_ALPHA_ROMAN",
        "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
        "NUMBERED_ZERODECIMAL_ALPHA_ROMAN",
    ]
    nesting_level: int = 0


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
        bullet: Bullet | BulletPreset | UnsetType = UNSET,
    ) -> None:
        self.text_style = text_style
        self.paragraph_style = paragraph_style
        self.bullet = bullet

    @property
    def utf16_width(self) -> int:
        return 1


class ContentStream:
    def __init__(self, *, items: list[TextUnit | ParagraphBoundary]) -> None:
        self.items = items

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)
