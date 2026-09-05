SKILL = """\
---
name: gdocs-patch
description: Read and safely modify Google Docs through canonical XHTML.
---

# gdocs-patch

Use `gdocs-patch` to modify an existing Google document while preserving the
structure and formatting represented by its canonical XHTML.

## Work from one local snapshot

1. Read the complete document once into a local file:

   gdocs-patch read DOCUMENT_ID --output working.xhtml

2. Inspect `working.xhtml` with local tools such as `rg`, `read`, or a script.
   Do not stream the complete XHTML into model context when local inspection is
   sufficient.
3. Make one replacement for each element explicitly named by the task. Do not
   replace a broad conceptual region just because its visible paragraphs are
   nearby.
4. Apply one `edit` or `write`. After it succeeds, stop unless the user asks for
   verification or a reported failure requires recovery.

Use `--offset` and `--limit` only for small inspection reads. Their output is
partial XHTML and must never be passed to `write`.

## Prefer exact edits for localized changes

Use `edit` when a task changes a few exact strings, attributes, or isolated XHTML
fragments. Create `edits.json`:

  {"edits":[{"oldText":"exact old XHTML","newText":"replacement XHTML"}]}

Then run:

  gdocs-patch edit DOCUMENT_ID edits.json

Every `oldText` must be non-empty, exact, and unique in `working.xhtml`. Copy it
from that file. Include only enough surrounding content to make it unique. All
edits are matched against the original document, so they must be disjoint and
must not depend on earlier edits in the same file.

For text-only changes, replace the smallest unique text inside its existing
markup. Plain escaped text is a valid edit when it is unique. Do not replace a
paragraph, list item, link, table cell, or object wrapper merely to change its
text.

## Preserve existing structure during text edits

Canonical XHTML records structure that may not be obvious in the rendered
Google Doc. Follow these rules when the task does not explicitly request a
structural or formatting change:

- Keep every existing element, attribute, namespace, key, and style unchanged.
- Keep `<g:list>`, `<li>`, `<g:bullet-style>`, and their paragraph elements when
  changing list-item text. Replace text inside the existing item; never rebuild
  the list or turn its items into ordinary paragraphs.
- Keep styled span boundaries. When visible text is split across spans, edit the
  text within those spans and retain their attributes. Do not collapse the spans
  into one run unless the task explicitly changes formatting.
- For links, change only the requested visible text or target attribute. Preserve
  the link element and every unrelated style attribute.
- Never include an inline or positioned object element in a replacement unless
  the task explicitly removes that object.
- Preserve leading control characters, line breaks, repeated spaces, and trailing
  whitespace unless the task explicitly changes them. If whitespace is unclear,
  inspect the source text with a representation that makes invisible characters
  visible before editing it.
- In tables, keep table, row, and cell wrappers and their opaque keys when only
  cell contents change.

These constraints apply equally in the body, headers, footers, footnotes, table
cells, captions, and styled quotes.

## Use write for structural or numerous changes

Use `write` when changes are structural, coordinated, or too numerous for a
small set of exact edits:

  cp working.xhtml original.xhtml
  # Modify working.xhtml locally.
  diff -u original.xhtml working.xhtml
  gdocs-patch write DOCUMENT_ID working.xhtml

Start from the complete XHTML returned by `read`; never recreate the document
from scratch. Review the local diff before writing. It should contain only the
requested changes. If unrelated list wrappers, paragraphs, styles, links,
objects, tables, headers, or footers disappear, correct the local file first.

Use `-` only when a pipeline is clearer than a file:

  gdocs-patch edit DOCUMENT_ID - < edits.json
  gdocs-patch write DOCUMENT_ID - < working.xhtml

## Learn syntax only when structure changes

Do not guess unfamiliar elements, attributes, namespaces, or nesting. Before
creating or restructuring content, use the focused guide:

  gdocs-patch syntax paragraphs
  gdocs-patch syntax lists
  gdocs-patch syntax tables
  gdocs-patch syntax equations
  gdocs-patch syntax sections

Add `--reference` for the detailed grammar. Customized list appearance is
preserved by default. Use `--allow-bullet-normalization` only when changing such
a list is necessary and conversion to the closest Google preset is acceptable.

## Handle failures deliberately

Expected failures are printed to standard error. Do not retry unchanged input.
Correct the exact replacement or local XHTML first. If the document revision is
stale, read a fresh complete snapshot and rebuild the change against it.
"""


def describe_skill() -> str:
    """Return agent-oriented best practices for using gdocs-patch."""
    return SKILL
