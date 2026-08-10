from gdocs_patch.models import ListDefinition

GlyphSignature = tuple[tuple[str | None, str | None, str], ...]

PRESET_SIGNATURES: dict[str, GlyphSignature] = {
    "BULLET_DISC_CIRCLE_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("●○■●○■●○■")
    ),
    "BULLET_DIAMONDX_ARROW3D_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("❖➢■●◆➢■●◆")
    ),
    "BULLET_CHECKBOX": tuple(
        (None, "GLYPH_TYPE_UNSPECIFIED", f"%{level}") for level in range(9)
    ),
    "BULLET_ARROW_DIAMOND_DISC": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("➔◆●○◆●○◆●")
    ),
    "BULLET_STAR_CIRCLE_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("★○■●○■●○■")
    ),
    "BULLET_ARROW3D_CIRCLE_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("➢○■●○■●○■")
    ),
    "BULLET_LEFTTRIANGLE_DIAMOND_DISC": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("◄◆●○◆●○◆●")
    ),
    "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("❖◇■●◆◇■●◆")
    ),
    "BULLET_DIAMOND_CIRCLE_SQUARE": tuple(
        (symbol, None, f"%{level}") for level, symbol in enumerate("◆○■●○■●○■")
    ),
    "NUMBERED_DECIMAL_ALPHA_ROMAN": (
        (None, "DECIMAL", "%0."),
        (None, "ALPHA", "%1."),
        (None, "ROMAN", "%2."),
        (None, "DECIMAL", "%3."),
        (None, "ALPHA", "%4."),
        (None, "ROMAN", "%5."),
        (None, "DECIMAL", "%6."),
        (None, "ALPHA", "%7."),
        (None, "ROMAN", "%8."),
    ),
    "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS": (
        (None, "DECIMAL", "%0)"),
        (None, "ALPHA", "%1)"),
        (None, "ROMAN", "%2)"),
        (None, "DECIMAL", "(%3)"),
        (None, "ALPHA", "(%4)"),
        (None, "ROMAN", "(%5)"),
        (None, "DECIMAL", "%6."),
        (None, "ALPHA", "%7."),
        (None, "ROMAN", "%8."),
    ),
    "NUMBERED_DECIMAL_NESTED": tuple(
        (None, "DECIMAL", "".join(f"%{parent}." for parent in range(level + 1)))
        for level in range(9)
    ),
    "NUMBERED_UPPERALPHA_ALPHA_ROMAN": (
        (None, "UPPER_ALPHA", "%0."),
        (None, "ALPHA", "%1."),
        (None, "ROMAN", "%2."),
        (None, "DECIMAL", "%3."),
        (None, "ALPHA", "%4."),
        (None, "ROMAN", "%5."),
        (None, "DECIMAL", "%6."),
        (None, "ALPHA", "%7."),
        (None, "ROMAN", "%8."),
    ),
    "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL": (
        (None, "UPPER_ROMAN", "%0."),
        (None, "UPPER_ALPHA", "%1."),
        (None, "DECIMAL", "%2."),
        (None, "ALPHA", "%3)"),
        (None, "DECIMAL", "(%4)"),
        (None, "ALPHA", "(%5)"),
        (None, "ROMAN", "(%6)"),
        (None, "ALPHA", "(%7)"),
        (None, "ROMAN", "(%8)"),
    ),
    "NUMBERED_ZERODECIMAL_ALPHA_ROMAN": (
        (None, "ZERO_DECIMAL", "%0."),
        (None, "ALPHA", "%1."),
        (None, "ROMAN", "%2."),
        (None, "DECIMAL", "%3."),
        (None, "ALPHA", "%4."),
        (None, "ROMAN", "%5."),
        (None, "DECIMAL", "%6."),
        (None, "ALPHA", "%7."),
        (None, "ROMAN", "%8."),
    ),
}


def list_signature(definition: ListDefinition) -> GlyphSignature:
    return tuple(
        (
            level.glyph_symbol if isinstance(level.glyph_symbol, str) else None,
            level.glyph_type if isinstance(level.glyph_type, str) else None,
            level.glyph_format,
        )
        for level in definition.levels
    )


def exact_preset(definition: ListDefinition) -> str | None:
    signature = list_signature(definition)
    return next(
        (
            preset
            for preset, preset_signature in PRESET_SIGNATURES.items()
            if preset_signature == signature
        ),
        None,
    )


def closest_preset(definition: ListDefinition) -> str:
    signature = list_signature(definition)
    best_preset = next(iter(PRESET_SIGNATURES))
    best_score: tuple[int, tuple[bool, ...]] = (-1, ())
    for preset, preset_signature in PRESET_SIGNATURES.items():
        matches = tuple(
            actual == canonical
            for actual, canonical in zip(signature, preset_signature, strict=False)
        )
        score = (sum(matches), matches)
        if score > best_score:
            best_preset = preset
            best_score = score
    return best_preset
