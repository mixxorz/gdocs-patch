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

If a change needs to rebuild a customized existing list, the compiler normally
fails rather than changing its appearance. Pass `--allow-bullet-normalization`
to `write` or `edit` to convert it to the closest supported preset:

  gdocs-patch edit DOCUMENT_ID edits.json --allow-bullet-normalization
  gdocs-patch write DOCUMENT_ID document.xhtml --allow-bullet-normalization

For the complete list of presets and list-definition attributes, run:
  gdocs-patch syntax lists --reference
"""

REFERENCE = """\
List syntax reference

List containers and items
-------------------------
Every list uses `<g:list>` and must contain at least one `<li>`. Every `<li>`
contains exactly one paragraph. `g:nesting-level` is a non-negative integer and
defaults to 0.

Exactly one list identity attribute is required:

  g:list-id         identifies and preserves an existing Google list
  g:bullet-preset   creates a new list or explicitly replaces an existing list
                    with the chosen Google preset

Available presets
-----------------
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
`read` includes existing Google list definitions under the document tab. These
definitions are read-only metadata: keep them unchanged in target XHTML. The
compiler uses them to understand existing list glyphs and choose presets when
normalization is necessary, but it does not write list-definition changes.

At a high level, the wrapper contains one definition for each list ID, and each
definition contains the appearance of its nesting levels:

  <g:list-definitions>
    <g:list-definition g:list-id="LIST_ID">
      <g:list-level ... />
      <g:list-level ... />
    </g:list-definition>
  </g:list-definitions>

Treat this whole block as reference information. Do not add, remove, or modify
its definitions or levels through `write` or `edit`. To change list formatting,
use `g:bullet-preset` on the list itself instead.

Changing an existing list to a preset
-------------------------------------
To explicitly replace an existing list's formatting, change its target XHTML
from `g:list-id` to the preset you want:

  <g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">
    <li><p><span>Existing item, rebuilt with this preset</span></p></li>
  </g:list>

The compiler removes the old list membership and recreates the paragraphs with
the chosen preset. This explicit change does not require
`--allow-bullet-normalization` because the target already says which preset to
use.

Compiler limits
---------------
Keep `g:list-id` when you want to preserve an existing list. Google Docs cannot
reproduce arbitrary custom list glyphs through the batch-update API. Some edits
to a customized list, such as changing its nesting, require the compiler to
rebuild it even though the target still uses `g:list-id`.

By default, that implicit normalization fails rather than changing the list's
appearance. Pass `--allow-bullet-normalization` to `write` or `edit` to let the
compiler choose the closest supported preset from the existing list's glyphs.
"""
