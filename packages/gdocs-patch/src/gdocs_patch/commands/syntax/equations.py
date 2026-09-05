GUIDE = """\
An equation is represented by one opaque marker inside a paragraph:

<p>
  <span>The result is </span>
  <g:equation />
  <span>.</span>
</p>

Google's document response does not expose the equation expression, so the XHTML
cannot show or edit its formula. Keeping the marker in the target preserves an
existing equation, and removing it deletes the equation.

The Google Docs batch-update API cannot insert an equation. Adding a new
`<g:equation />` where the source document did not already have one will make
compilation fail rather than silently produce the wrong document.

For the exact equation contract and compiler behavior, run:
  gdocs-patch syntax equations --reference
"""

REFERENCE = """\
Equation syntax reference

The complete equation representation is:

  <g:equation />

It has no attributes, children, text style, formula text, or identity key. It
must appear directly inside a paragraph and cannot be wrapped in a link.

The marker represents one UTF-16 content unit. If the same marker remains in
aligned source and target content, the existing equation is preserved. Removing
the marker deletes it.

Google's document response does not expose the underlying expression, and the
batch-update API has no request for inserting an equation. For that reason,
adding a new marker is unsupported and compilation fails with:

  Google Docs cannot insert Equation elements
"""
