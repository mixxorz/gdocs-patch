XHTML_SYNTAX_OVERVIEW = """\
gdocs-patch represents a complete Google document as canonical XHTML.

Standard XHTML elements describe familiar document content such as paragraphs,
headings, links, lists, tables, and sections. Elements and attributes in the
`g` namespace preserve Google Docs-specific structure and metadata, including
tabs, styles, document IDs, and section settings.

Use `gdocs-patch read` to get this representation. Edit the returned XHTML
without removing its surrounding document structure, then use `write` to apply
the complete result or `edit` to make exact replacements. The XML declaration
and the XHTML and gdocs-patch namespace declarations are required.

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
"""


def describe_syntax() -> str:
    """Return the introductory XHTML syntax reference."""
    return XHTML_SYNTAX_OVERVIEW
