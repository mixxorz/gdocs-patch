"""Codemod: ban `from __future__ import annotations`.

This project requires Python 3.12 or newer and deliberately avoids postponed
annotation evaluation so runtime annotation behavior stays explicit. Keeping
the import can silently change runtime behaviour for code that calls
typing.get_type_hints().

Autofix: removes the `annotations` name from the import. If it was the only
name, the entire import statement is removed.
"""

import libcst as cst
import libcst.matchers as m
from fixit import Invalid, LintRule, Valid
from libcst.metadata import ParentNodeProvider


class NoFutureAnnotations(LintRule):
    """Ban `from __future__ import annotations`.

    This project requires Python 3.12 or newer and deliberately avoids
    postponed annotation evaluation so runtime annotation behavior stays
    explicit. The ``from __future__ import annotations`` shim (PEP 563) can
    silently alter runtime behaviour for anything that inspects annotations
    via ``typing.get_type_hints()``. Remove it and quote forward references
    where needed.

    Autofix removes the ``annotations`` name. If it was the only import in the
    statement, the whole line is removed.
    """

    MESSAGE = (
        "`from __future__ import annotations` is disallowed because it can "
        "change runtime annotation behaviour. Remove it."
    )

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        Valid("import os"),
        Valid("from __future__ import generator_stop"),
        Valid("from typing import TYPE_CHECKING"),
    ]

    INVALID = [
        Invalid(
            "from __future__ import annotations",
            expected_replacement="",
        ),
        Invalid(
            "from __future__ import annotations, generator_stop",
            expected_replacement="from __future__ import generator_stop",
        ),
    ]

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not m.matches(node, m.ImportFrom(module=m.Name("__future__"))):
            return
        if isinstance(node.names, cst.ImportStar):
            return

        annotations_aliases = [
            alias
            for alias in node.names
            if m.matches(alias, m.ImportAlias(name=m.Name("annotations")))
        ]
        if not annotations_aliases:
            return

        remaining = [
            alias
            for alias in node.names
            if not m.matches(alias, m.ImportAlias(name=m.Name("annotations")))
        ]

        if not remaining:
            # Only import in this statement — remove the enclosing SimpleStatementLine.
            parent = self.get_metadata(ParentNodeProvider, node)
            self.report(parent, replacement=cst.RemovalSentinel.REMOVE)
        else:
            # Other names remain — strip annotations alias and fix trailing comma.
            new_aliases = [
                alias.with_changes(comma=cst.MaybeSentinel.DEFAULT)
                for alias in remaining
            ]
            replacement = node.with_changes(names=new_aliases)
            self.report(node, replacement=replacement)
