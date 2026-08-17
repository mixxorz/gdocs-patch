SKILL = """\
---
name: gdocs-patch
description: Read and safely modify Google Docs through canonical XHTML.
---

# gdocs-patch

Use `gdocs-patch` to inspect and modify an existing Google document while
preserving structure and formatting that the Google Docs API exposes.

## Default workflow

1. Read the complete document once into a working file:

   gdocs-patch read DOCUMENT_ID --output working.xhtml

2. Inspect and modify `working.xhtml` locally. Keep the complete XHTML out of
   model context when local search and editing tools are sufficient.
3. Preserve every unrelated element, attribute, style, namespace declaration,
   object reference, tab, header, footer, and footnote.
4. Collect and review all intended changes before making a remote mutation.
5. Apply one `edit` or `write`. After it succeeds, stop unless the user asks for
   verification or recovery from a reported failure requires another read.

## Choose the smallest safe mutation

Prefer `edit` for a few exact, localized replacements. Its JSON file has this
shape:

  {"edits":[{"oldText":"exact old XHTML","newText":"replacement XHTML"}]}

Run it with:

  gdocs-patch edit DOCUMENT_ID edits.json

Each `oldText` must be non-empty, exact, and unique in the canonical XHTML.
Include enough surrounding markup and whitespace to make the match unique, but
no more than needed. Edits must be disjoint and are all matched against the
original document, not against earlier replacements in the same file.

Prefer `write` for coordinated, structural, or numerous changes after editing a
complete local working file:

  gdocs-patch write DOCUMENT_ID working.xhtml

Never pass paginated or otherwise partial `read` output to `write`.

Use `-` only when a pipeline is clearer than a file:

  gdocs-patch edit DOCUMENT_ID - < edits.json
  gdocs-patch write DOCUMENT_ID - < working.xhtml

## Learn the XHTML before changing structure

Run `gdocs-patch syntax` for an overview. Focused guides are available for
`paragraphs`, `lists`, `tables`, `equations`, and `sections`:

  gdocs-patch syntax tables
  gdocs-patch syntax tables --reference

Read the relevant guide before creating or restructuring unfamiliar markup.
Do not guess element names, attributes, namespaces, or structural nesting.

## Preserve canonical document invariants

Treat the XHTML from `read` as the source of truth. Preserve the XML declaration,
the XHTML and `g` namespace declarations, root metadata, tab and segment
structure, and unsupported or opaque content. Do not recreate the document from
scratch when a targeted change will work.

Document identity and revision metadata are read-only. Existing tabs, headers,
footers, and footnotes may contain editable content, but cannot all be created or
removed. A mutation compiled against a stale revision fails instead of silently
writing at stale indices; on that failure, read the current document and rebuild
the change.

Customized list appearance is preserved by default. Use
`--allow-bullet-normalization` only when changing such a list is necessary and
conversion to the closest supported Google preset is acceptable.

## Read efficiently

A plain read writes complete canonical XHTML to standard output:

  gdocs-patch read DOCUMENT_ID

Use `--output` for a working file. Use `--offset` and `--limit` only to inspect a
small line range; those options return partial XHTML that is not a writable
document.

Expected failures are printed to standard error. Do not retry unchanged input.
Use the error to correct the local XHTML or exact replacements first.
"""


def describe_skill() -> str:
    """Return agent-oriented best practices for using gdocs-patch."""
    return SKILL
