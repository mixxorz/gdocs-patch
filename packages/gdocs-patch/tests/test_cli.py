import io
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from gdocs_patch import cli
from gdocs_patch.commands import XhtmlEdit


def test_read_command_supports_file_and_standard_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    credentials = object()
    client = object()
    load_credentials = Mock(return_value=credentials)
    google_docs_client = Mock(return_value=client)
    read_document = Mock(return_value="<html />\n")
    monkeypatch.setattr(cli, "load_credentials", load_credentials)
    monkeypatch.setattr(cli, "GoogleDocsClient", google_docs_client)
    monkeypatch.setattr(cli, "read_document", read_document)
    output = tmp_path / "document.xhtml"

    file_result = cli.main(
        [
            "read",
            "document-id",
            "--output",
            str(output),
            "--offset",
            "8",
            "--limit",
            "4",
        ]
    )

    assert file_result == 0
    assert output.read_text(encoding="utf-8") == "<html />\n"
    assert capsys.readouterr() == ("", "")

    stdout_result = cli.main(["read", "document-id"])

    assert stdout_result == 0
    assert capsys.readouterr() == ("<html />\n", "")
    assert load_credentials.call_count == 2
    assert google_docs_client.call_args_list == [
        call(credentials=credentials),
        call(credentials=credentials),
    ]
    assert read_document.call_args_list == [
        call(
            client=client,
            doc_id="document-id",
            offset=8,
            limit=4,
        ),
        call(
            client=client,
            doc_id="document-id",
            offset=1,
            limit=None,
        ),
    ]


def test_edit_command_supports_file_and_standard_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    credentials = object()
    client = object()
    load_credentials = Mock(return_value=credentials)
    google_docs_client = Mock(return_value=client)
    edit_document = Mock(return_value=2)
    monkeypatch.setattr(cli, "load_credentials", load_credentials)
    monkeypatch.setattr(cli, "GoogleDocsClient", google_docs_client)
    monkeypatch.setattr(cli, "edit_document", edit_document)
    edits_file = tmp_path / "edits.json"
    edits_file.write_text(
        '{"edits":[{"oldText":"file old","newText":"file new"}]}',
        encoding="utf-8",
    )

    file_result = cli.main(
        [
            "edit",
            "document-id",
            str(edits_file),
            "--allow-bullet-normalization",
        ]
    )

    assert file_result == 0
    assert capsys.readouterr() == (
        "Successfully replaced 2 blocks in document-id.\n",
        "",
    )

    monkeypatch.setattr(
        cli.sys,
        "stdin",
        io.StringIO('{"edits":[{"oldText":"stdin old","newText":"stdin new"}]}'),
    )
    stdin_result = cli.main(["edit", "document-id", "-"])

    assert stdin_result == 0
    assert capsys.readouterr() == (
        "Successfully replaced 2 blocks in document-id.\n",
        "",
    )
    assert load_credentials.call_count == 2
    assert google_docs_client.call_args_list == [
        call(credentials=credentials),
        call(credentials=credentials),
    ]
    assert edit_document.call_args_list == [
        call(
            client=client,
            doc_id="document-id",
            edits=[XhtmlEdit(old_text="file old", new_text="file new")],
            allow_bullet_normalization=True,
        ),
        call(
            client=client,
            doc_id="document-id",
            edits=[XhtmlEdit(old_text="stdin old", new_text="stdin new")],
            allow_bullet_normalization=False,
        ),
    ]


def test_write_command_supports_file_and_standard_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    credentials = object()
    client = object()
    load_credentials = Mock(return_value=credentials)
    google_docs_client = Mock(return_value=client)
    write_document = Mock()
    monkeypatch.setattr(cli, "load_credentials", load_credentials)
    monkeypatch.setattr(cli, "GoogleDocsClient", google_docs_client)
    monkeypatch.setattr(cli, "write_document", write_document)
    xhtml_file = tmp_path / "document.xhtml"
    xhtml_file.write_text("<html>file</html>\n", encoding="utf-8")

    file_result = cli.main(
        [
            "write",
            "document-id",
            str(xhtml_file),
            "--allow-bullet-normalization",
        ]
    )

    assert file_result == 0
    assert capsys.readouterr() == (
        "Successfully wrote to document-id.\n",
        "",
    )

    monkeypatch.setattr(cli.sys, "stdin", io.StringIO("<html>stdin</html>\n"))
    stdin_result = cli.main(["write", "document-id", "-"])

    assert stdin_result == 0
    assert capsys.readouterr() == (
        "Successfully wrote to document-id.\n",
        "",
    )
    assert load_credentials.call_count == 2
    assert google_docs_client.call_args_list == [
        call(credentials=credentials),
        call(credentials=credentials),
    ]
    assert write_document.call_args_list == [
        call(
            client=client,
            doc_id="document-id",
            content="<html>file</html>\n",
            allow_bullet_normalization=True,
        ),
        call(
            client=client,
            doc_id="document-id",
            content="<html>stdin</html>\n",
            allow_bullet_normalization=False,
        ),
    ]
