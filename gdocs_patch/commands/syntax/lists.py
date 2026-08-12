GUIDE = """\
A list is a group of paragraphs. Each `<li>` contains one paragraph. Lists
returned by `read` have a `g:list-id`; keep it when editing the same list:

<g:list g:list-id="existing-list-id">
  <li><p><span>First item</span></p></li>
  <li><p><span>Second item</span></p></li>
</g:list>

To add a new list between ordinary paragraphs, use `g:bullet-preset` instead.
Do not give a new list a `g:list-id`:

<p><span>Before the list</span></p>
<g:list g:bullet-preset="BULLET_CHECKBOX">
  <li><p><span>First new task</span></p></li>
  <li><p><span>Second new task</span></p></li>
</g:list>
<p><span>After the list</span></p>

Use `g:nesting-level` when an item is nested. Level 0 is the default:

<g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">
  <li><p><span>Parent item</span></p></li>
  <li g:nesting-level="1"><p><span>Nested item</span></p></li>
</g:list>

Use `g:bullet-preset` for a new list and `g:list-id` for an existing one, never
both. Google Docs cannot recreate arbitrary custom bullet glyphs through its
batch-update API, so new lists must use a supported preset.

If an edit needs to change a customized existing list, the compiler normally
fails rather than changing its appearance. Set `allowBulletNormalization` to
`true` in the `write` or `edit` JSON input to convert it to the closest supported
preset:

  {"docId":"DOCUMENT_ID",
   "edits":[{"oldText":"old","newText":"new"}],
   "allowBulletNormalization":true}

For the complete list of presets and list-definition attributes, run:
  gdocs-patch syntax lists reference
"""

REFERENCE = """\
List syntax reference

List containers and items
-------------------------
Every list uses `<g:list>` and must contain at least one `<li>`. Every `<li>`
contains exactly one paragraph. `g:nesting-level` is a non-negative integer and
defaults to 0.

Exactly one list identity attribute is required:

  g:list-id         identifies an existing Google list
  g:bullet-preset   creates or normalizes a list using a Google preset

Available presets
-----------------
  BULLET_GLYPH_PRESET_UNSPECIFIED
  BULLET_DISC_CIRCLE_SQUARE
  BULLET_DIAMONDX_ARROW3D_SQUARE
  BULLET_CHECKBOX
  BULLET_ARROW_DIAMOND_DISC
  BULLET_STAR_CIRCLE_SQUARE
  BULLET_ARROW3D_CIRCLE_SQUARE
  BULLET_LEFTTRIANGLE_DIAMOND_DISC
  BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE
  BULLET_DIAMOND_CIRCLE_SQUARE
  NUMBERED_DECIMAL_ALPHA_ROMAN
  NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS
  NUMBERED_DECIMAL_NESTED
  NUMBERED_UPPERALPHA_ALPHA_ROMAN
  NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL
  NUMBERED_ZERODECIMAL_ALPHA_ROMAN

Bullet style on existing lists
------------------------------
An item in an existing `g:list-id` list may have one `<g:bullet-style>` before
its paragraph. It accepts the same bold, italic, underline, strikethrough,
small-caps, baseline, font, color, and link metadata as a text run. Preset list
items cannot contain `<g:bullet-style>`.

List definitions
----------------
`read` includes existing Google list definitions under the document tab. They
look like this:

  <g:list-definitions>
    <g:list-definition g:list-id="LIST_ID">
      <g:list-level g:glyph-format="%0."
                    g:glyph-type="DECIMAL"
                    g:alignment="START"
                    g:indent-first-line="18"
                    g:indent-start="36"
                    g:start-number="1" />
    </g:list-definition>
  </g:list-definitions>

Each level requires `g:glyph-format` and exactly one of `g:glyph-type` or
`g:glyph-symbol`. Glyph types are GLYPH_TYPE_UNSPECIFIED, NONE, DECIMAL,
ZERO_DECIMAL, UPPER_ALPHA, ALPHA, UPPER_ROMAN, and ROMAN. Alignment is
BULLET_ALIGNMENT_UNSPECIFIED, START, CENTER, or END. Indents are point values;
`g:start-number` is an integer. Levels also accept text-style attributes.

Compiler limits
---------------
Keep `g:list-id` when editing an existing list. Use `g:bullet-preset` for a new
list. Google Docs cannot reproduce arbitrary custom list glyphs through the
batch-update API. By default, an edit that requires normalization fails rather
than changing the list's appearance. Set `allowBulletNormalization` to `true`
in the `write` or `edit` JSON input to let the compiler choose the closest
supported preset based on the list's glyphs.
"""
