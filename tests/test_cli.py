import io
import sys

import pytest

from gdocs_patch.cli import main


@pytest.mark.parametrize(
    ("command", "stdin", "expected_stderr"),
    [
        (
            "read",
            "{",
            "gdocs-patch: error: Input must contain one valid JSON object.\n",
        ),
        ("read", "[]", "gdocs-patch: error: Input must be a JSON object.\n"),
        (
            "read",
            '{"docId":"doc-1","extra":true}',
            "gdocs-patch: error: Read command input has unknown field: extra.\n",
        ),
        (
            "edit",
            '{"docId":"doc-1","edits":[]}',
            "gdocs-patch: error: Edit command input is invalid. edits must contain "
            "at least one replacement.\n",
        ),
        (
            "edit",
            '{"docId":"doc-1","edits":[{"oldText":"","newText":"replacement"}]}',
            "gdocs-patch: error: edits[0].oldText must not be empty in doc-1.\n",
        ),
    ],
)
def test_rejects_invalid_json_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    stdin: str,
    expected_stderr: str,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))

    assert main([command]) == 1
    assert capsys.readouterr().err == expected_stderr
