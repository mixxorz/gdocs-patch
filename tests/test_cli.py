import io
import sys

import pytest

from gdocs_patch.cli import main


@pytest.mark.parametrize(
    ("stdin", "expected_stderr"),
    [
        ("{", "gdocs-patch: error: Input must contain one valid JSON object.\n"),
        ("[]", "gdocs-patch: error: Input must be a JSON object.\n"),
        (
            '{"docId":"doc-1","extra":true}',
            "gdocs-patch: error: Read command input has unknown field: extra.\n",
        ),
    ],
)
def test_read_rejects_invalid_json_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin: str,
    expected_stderr: str,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))

    assert main(["read"]) == 1
    assert capsys.readouterr().err == expected_stderr
