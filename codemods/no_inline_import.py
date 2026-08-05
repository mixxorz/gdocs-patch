"""Codemod: ban import statements outside module top-level.

Imports that appear inside function or class bodies make dependencies implicit
and hamper static analysis. The only accepted exception is imports guarded by
`if TYPE_CHECKING:`, which are invisible at runtime and used purely for type
annotations.
"""

import libcst as cst
import libcst.matchers as m
from fixit import Invalid, LintRule, Valid
from libcst.metadata import ParentNodeProvider

# Matches `if TYPE_CHECKING:` (plain name, no attribute like typing.TYPE_CHECKING)
_TYPE_CHECKING = m.If(test=m.Name("TYPE_CHECKING"))
# Also match `if typing.TYPE_CHECKING:`
_TYPING_TYPE_CHECKING = m.If(
    test=m.Attribute(value=m.Name("typing"), attr=m.Name("TYPE_CHECKING"))
)


class NoInlineImport(LintRule):
    """Import statements must appear at the top of the module.

    Inline imports (inside functions, classes, or other blocks) hide
    dependencies and make code harder to analyse. Move them to the top of the
    file.

    The only exception is imports placed inside an ``if TYPE_CHECKING:`` block,
    which exist solely to satisfy type checkers and are never executed at
    runtime.
    """

    MESSAGE = (
        "Import statements must be at module level. "
        "Move this import to the top of the file. "
        "(Exception: imports inside `if TYPE_CHECKING:` are allowed.)"
    )

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        # Top-level imports are fine
        Valid("import os"),
        Valid("from pathlib import Path"),
        Valid("import os\nimport sys"),
        # TYPE_CHECKING guards are allowed
        Valid(
            """
            from __future__ import annotations
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                import os
            """
        ),
        Valid(
            """
            import typing
            if typing.TYPE_CHECKING:
                from pathlib import Path
            """
        ),
        # Nested under TYPE_CHECKING (e.g. with other imports in the block)
        Valid(
            """
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                import os
                from pathlib import Path
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            def foo():
                import os
            """
        ),
        Invalid(
            """
            def foo():
                from pathlib import Path
            """
        ),
        Invalid(
            """
            class MyClass:
                import os
            """
        ),
        Invalid(
            """
            if True:
                import os
            """
        ),
    ]

    def _is_under_type_checking(self, node: cst.CSTNode) -> bool:
        """Return True if node is nested inside an `if TYPE_CHECKING:` block."""
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None and not isinstance(parent, cst.Module):
            if m.matches(parent, _TYPE_CHECKING) or m.matches(
                parent, _TYPING_TYPE_CHECKING
            ):
                return True
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        return False

    def _is_module_level(self, node: cst.CSTNode) -> bool:
        """Return True if node is a direct child of the module body."""
        parent = self.get_metadata(ParentNodeProvider, node, None)
        # Import/ImportFrom sits inside a SimpleStatementLine; that line's
        # parent should be the Module for a top-level import.
        if isinstance(parent, cst.SimpleStatementLine):
            grandparent = self.get_metadata(ParentNodeProvider, parent, None)
            return isinstance(grandparent, cst.Module)
        return False

    def _check(self, node: cst.CSTNode) -> None:
        if not self._is_module_level(node) and not self._is_under_type_checking(node):
            self.report(node)

    def visit_Import(self, node: cst.Import) -> None:
        self._check(node)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        self._check(node)
