from .equations import GUIDE as EQUATIONS_GUIDE
from .equations import REFERENCE as EQUATIONS_REFERENCE
from .lists import GUIDE as LISTS_GUIDE
from .lists import REFERENCE as LISTS_REFERENCE
from .paragraphs import GUIDE as PARAGRAPHS_GUIDE
from .paragraphs import REFERENCE as PARAGRAPHS_REFERENCE
from .sections import GUIDE as SECTIONS_GUIDE
from .sections import REFERENCE as SECTIONS_REFERENCE
from .tables import GUIDE as TABLES_GUIDE
from .tables import REFERENCE as TABLES_REFERENCE

OVERVIEW = """\
gdocs-patch represents a complete Google document as canonical XHTML.

Standard XHTML elements describe familiar document content such as paragraphs,
headings, links, lists, tables, and sections. Elements and attributes in the
`g` namespace preserve Google Docs-specific structure and metadata, including
tabs, styles, document IDs, and section settings.

Use `gdocs-patch read` to get this representation. Edit the returned XHTML
without removing its surrounding document structure, then use `write` to apply
the complete result or `edit` to make exact replacements. The XML declaration
and the XHTML and gdocs-patch namespace declarations are required.

A document can also contain existing headers, footers, and footnotes. You can
edit supported content inside them, but you cannot create or remove those
regions yet.

Basic example:

<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:g="urn:gdocs-patch:xhtml:1"
      g:document-id="DOCUMENT_ID"
      g:title="Example">
  <body>
    <g:tab g:tab-id="TAB_ID" g:title="Main" g:index="0">
      <g:document-tab>
        <g:body>
          <section>
            <g:section-style />
            <h1><span>Hello</span></h1>
            <p><span>This is a paragraph.</span></p>
          </section>
        </g:body>
      </g:document-tab>
    </g:tab>
  </body>
</html>

For more detail, use one of these commands:
  gdocs-patch syntax paragraphs
  gdocs-patch syntax lists
  gdocs-patch syntax tables
  gdocs-patch syntax equations
  gdocs-patch syntax sections
"""

GUIDES = {
    "paragraphs": PARAGRAPHS_GUIDE,
    "lists": LISTS_GUIDE,
    "tables": TABLES_GUIDE,
    "equations": EQUATIONS_GUIDE,
    "sections": SECTIONS_GUIDE,
}

REFERENCES = {
    "paragraphs": PARAGRAPHS_REFERENCE,
    "lists": LISTS_REFERENCE,
    "tables": TABLES_REFERENCE,
    "equations": EQUATIONS_REFERENCE,
    "sections": SECTIONS_REFERENCE,
}


def describe_syntax(topic: str | None = None, *, reference: bool = False) -> str:
    """Return the introductory, topic guide, or detailed syntax reference."""
    if topic is None:
        return OVERVIEW
    if reference:
        return REFERENCES[topic]
    return GUIDES[topic]
