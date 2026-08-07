# Google Docs Client Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive Google OAuth, sandbox bearer-token loading, and a dumb Google Docs transport client.

**Architecture:** `gdocs_patch.client.auth` owns credential selection, refresh, persistence, and the dual loopback/paste OAuth callback. `gdocs_patch.client.google_docs` passes explicit Google credentials and decoded dictionaries through the official SDK without knowing about document models, parsing, or compilation. The existing argparse CLI only invokes login.

**Tech Stack:** Python 3.12+, `uv`, `argparse`, `google-auth-oauthlib`, `google-api-python-client`, standard-library WSGI/threading, Ruff, Fixit, Pyright, pytest, pre-commit.

## Global Constraints

- Work only in `.worktrees/feature-google-docs-client` on branch `feature-google-docs-client`.
- Preserve the untracked sample document in the main checkout and do not commit it.
- Request only `https://www.googleapis.com/auth/documents`.
- Prefer `GDOCS_PATCH_BEARER_TOKEN` over stored OAuth credentials.
- Store client configuration at `~/.config/gdocs-patch/client_secret.json` by default and user credentials at `~/.config/gdocs-patch/credentials.json`.
- Keep `GoogleDocsClient` independent of models, parsers, and the compiler.
- Add no automated tests for this integration; run all existing tests and static checks for regressions.
- Do not add service accounts, Drive scopes, document CLI commands, logout, status, or token validation.

---

## File structure

- Create `gdocs_patch/client/auth.py`: OAuth login, callback collection, credential storage, environment precedence, and refresh.
- Create `gdocs_patch/client/google_docs.py`: dumb `documents.get` and `documents.batchUpdate` SDK wrapper.
- Create `gdocs_patch/client/__init__.py`: the package's small public API.
- Modify `gdocs_patch/cli.py`: add `auth login` and `--client-secrets`.
- Modify `pyproject.toml` and `uv.lock`: add the official Google dependencies.
- Modify `README.md`: setup, desktop/remote login, bearer token, and client usage.

### Task 1: Authentication module

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `gdocs_patch/client/auth.py`

**Interfaces:**
- Produces: `AuthenticationError`, `DOCS_SCOPE`, `login(*, client_secrets: Path | None = None) -> Path`, and `load_credentials() -> google.auth.credentials.Credentials`.
- Consumes: Google desktop client JSON, `GDOCS_PATCH_BEARER_TOKEN`, and Google OAuth callback URLs.

- [ ] **Step 1: Add the Google dependencies**

Run:

```bash
cd /Users/mixxorz/Projects/gdocs_patch/.worktrees/feature-google-docs-client
uv add google-api-python-client google-auth-oauthlib
```

Expected: `pyproject.toml` lists both packages under `[project].dependencies`, `uv.lock` is updated, and `uv sync` succeeds.

- [ ] **Step 2: Implement authentication and the dual callback flow**

Create `gdocs_patch/client/auth.py` with these concrete behaviors:

```python
import os
import queue
import threading
import webbrowser
import wsgiref.simple_server
import wsgiref.util
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from google.auth.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (  # pyright: ignore[reportMissingTypeStubs]
    InstalledAppFlow,
)

DOCS_SCOPE = "https://www.googleapis.com/auth/documents"
TOKEN_ENVIRONMENT_VARIABLE = "GDOCS_PATCH_BEARER_TOKEN"
CONFIG_DIRECTORY = Path.home() / ".config" / "gdocs-patch"
DEFAULT_CLIENT_SECRETS_PATH = CONFIG_DIRECTORY / "client_secret.json"
DEFAULT_CREDENTIALS_PATH = CONFIG_DIRECTORY / "credentials.json"


class AuthenticationError(Exception):
    """Raised when credentials required by gdocs-patch are unavailable."""


class QuietRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    """Avoid logging the one-time OAuth code contained in the request URL."""

    def log_message(self, format_string: str, *args: object) -> None:
        pass


def save_credentials(credentials: Credentials) -> None:
    DEFAULT_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    DEFAULT_CREDENTIALS_PATH.touch(mode=0o600, exist_ok=True)
    DEFAULT_CREDENTIALS_PATH.chmod(0o600)
    DEFAULT_CREDENTIALS_PATH.write_text(credentials.to_json(), encoding="utf-8")


def login(*, client_secrets: Path | None = None) -> Path:
    client_secrets_path = client_secrets or DEFAULT_CLIENT_SECRETS_PATH
    if not client_secrets_path.is_file():
        raise AuthenticationError(
            f"Google OAuth client secrets not found at {client_secrets_path}"
        )

    callbacks: queue.Queue[str] = queue.Queue(maxsize=1)

    def submit_callback(callback_url: str) -> None:
        try:
            callbacks.put_nowait(callback_url)
        except queue.Full:
            pass

    def receive_callback(
        environment: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        callback_url = wsgiref.util.request_uri(environment)
        submit_callback(callback_url)
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Authorization received. You may close this window."]

    callback_server = wsgiref.simple_server.make_server(
        "localhost",
        0,
        receive_callback,
        handler_class=QuietRequestHandler,
    )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        scopes=[DOCS_SCOPE],
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = f"http://localhost:{callback_server.server_port}/"
    authorization_url, _ = flow.authorization_url(prompt="consent")

    print("Open this URL in a browser to authorize gdocs-patch:\n")
    print(authorization_url)
    print(
        "\nIf login does not complete automatically, paste the complete "
        "localhost callback URL below."
    )

    callback_server_thread = threading.Thread(
        target=callback_server.serve_forever,
        daemon=True,
    )
    callback_server_thread.start()

    def read_pasted_callback() -> None:
        try:
            callback_url = input("Callback URL: ").strip()
        except EOFError:
            return
        if callback_url:
            submit_callback(callback_url)

    threading.Thread(target=read_pasted_callback, daemon=True).start()
    webbrowser.open(authorization_url, new=2)

    try:
        authorization_response = callbacks.get()
    finally:
        callback_server.shutdown()
        callback_server.server_close()

    # OAuthlib rejects an HTTP authorization-response URL even though Google
    # explicitly permits loopback HTTP redirects for installed applications.
    authorization_response = authorization_response.replace("http://", "https://", 1)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = cast(Credentials, flow.credentials)
    save_credentials(credentials)
    return DEFAULT_CREDENTIALS_PATH


def load_credentials() -> GoogleCredentials:
    bearer_token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE)
    if bearer_token is not None:
        return Credentials(token=bearer_token)

    if not DEFAULT_CREDENTIALS_PATH.is_file():
        raise AuthenticationError(
            "No Google credentials found. Run `gdocs-patch auth login`."
        )

    credentials = Credentials.from_authorized_user_file(
        str(DEFAULT_CREDENTIALS_PATH),
        scopes=[DOCS_SCOPE],
    )
    if credentials.expired:
        credentials.refresh(Request())
        save_credentials(credentials)
    return credentials
```

Keep the implementation direct. The request-handler logging override is necessary because the default WSGI handler would print the one-time authorization code. `save_credentials()` centralizes the same secure write used after login and refresh; do not introduce credential-store classes or callback abstractions.

- [ ] **Step 3: Verify imports, bearer-token behavior, formatting, and types**

Run:

```bash
GDOCS_PATCH_BEARER_TOKEN=example-token uv run python - <<'PY'
from gdocs_patch.client.auth import load_credentials

credentials = load_credentials()
assert credentials.token == "example-token"
PY
uv run ruff check gdocs_patch/client/auth.py
uv run ruff format --check gdocs_patch/client/auth.py
uv run pyright
```

Expected: the script and all three checks pass. If Pyright exposes additional unknown types from the untyped OAuth library, contain casts at that library boundary rather than adding application-wide protocols or disabling strict checking.

- [ ] **Step 4: Run the existing tests**

Run:

```bash
uv run pytest
```

Expected: all 100 existing tests pass.

- [ ] **Step 5: Commit authentication**

```bash
git add pyproject.toml uv.lock gdocs_patch/client/auth.py
git commit -m "feat: add Google OAuth credentials"
```

### Task 2: Dumb Google Docs client

**Files:**
- Create: `gdocs_patch/client/google_docs.py`
- Create: `gdocs_patch/client/__init__.py`

**Interfaces:**
- Consumes: an explicit `google.auth.credentials.Credentials` object and decoded request dictionaries.
- Produces: `GoogleDocsClient.get_document(*, document_id: str) -> dict[str, Any]` and `GoogleDocsClient.batch_update(*, document_id: str, body: dict[str, object]) -> dict[str, Any]`.

- [ ] **Step 1: Implement the transport wrapper**

Create `gdocs_patch/client/google_docs.py`:

```python
from typing import Any, cast

from google.auth.credentials import Credentials
from googleapiclient.discovery import (  # pyright: ignore[reportMissingTypeStubs]
    Resource,
    build,
)


class GoogleDocsClient:
    """Thin transport wrapper around the Google Docs API."""

    def __init__(self, *, credentials: Credentials) -> None:
        self._service = cast(
            Resource,
            build("docs", "v1", credentials=credentials),
        )

    def get_document(self, *, document_id: str) -> dict[str, Any]:
        response = (
            self._service.documents()
            .get(documentId=document_id, includeTabsContent=True)
            .execute()
        )
        return cast(dict[str, Any], response)

    def batch_update(
        self,
        *,
        document_id: str,
        body: dict[str, object],
    ) -> dict[str, Any]:
        response = (
            self._service.documents()
            .batchUpdate(documentId=document_id, body=body)
            .execute()
        )
        return cast(dict[str, Any], response)
```

The three casts stay at the dynamic SDK boundary. Do not add parsing, compilation, runtime response validation, retry policy, or a custom service protocol.

- [ ] **Step 2: Export the client package API**

Create `gdocs_patch/client/__init__.py`:

```python
from .auth import AuthenticationError, load_credentials, login
from .google_docs import GoogleDocsClient

__all__ = [
    "AuthenticationError",
    "GoogleDocsClient",
    "load_credentials",
    "login",
]
```

`DOCS_SCOPE` and path constants remain implementation details and are not re-exported.

- [ ] **Step 3: Verify the public imports and static checks**

Run:

```bash
uv run python - <<'PY'
from gdocs_patch.client import GoogleDocsClient, load_credentials, login

assert GoogleDocsClient
assert load_credentials
assert login
PY
uv run ruff check gdocs_patch/client
uv run ruff format --check gdocs_patch/client
uv run pyright
uv run pytest
```

Expected: imports succeed, static checks pass, and all 100 existing tests pass. This check intentionally does not construct the client because SDK construction may perform discovery setup; real transport behavior is verified manually against Google.

- [ ] **Step 4: Commit the client**

```bash
git add gdocs_patch/client/__init__.py gdocs_patch/client/google_docs.py
git commit -m "feat: add Google Docs transport client"
```

### Task 3: CLI, documentation, and final verification

**Files:**
- Modify: `gdocs_patch/cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `gdocs_patch.client.login(*, client_secrets: Path | None) -> Path`.
- Produces: `gdocs-patch auth login [--client-secrets PATH]`.

- [ ] **Step 1: Add the auth command to argparse**

Update `gdocs_patch/cli.py` to preserve `--help` and `--version` while adding nested auth routing:

```python
"""Command-line interface for gdocs-patch."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from gdocs_patch.client import AuthenticationError, login


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="gdocs-patch",
        description="Apply structured patches to Google Docs.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('gdocs-patch')}",
    )

    commands = parser.add_subparsers(dest="command")
    auth_parser = commands.add_parser("auth", help="Manage Google authentication.")
    auth_commands = auth_parser.add_subparsers(dest="auth_command", required=True)
    login_parser = auth_commands.add_parser(
        "login",
        help="Log in with Google OAuth.",
    )
    login_parser.add_argument(
        "--client-secrets",
        type=Path,
        help=(
            "Google desktop OAuth client JSON; defaults to "
            "~/.config/gdocs-patch/client_secret.json."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "auth" and args.auth_command == "login":
        try:
            credentials_path = login(client_secrets=args.client_secrets)
        except AuthenticationError as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        print(f"Credentials saved to {credentials_path}")
        return 0

    parser.print_help()
    return 0
```

Do not add handler registries, dynamic command dispatch, status, logout, or API commands.

- [ ] **Step 2: Check command discovery without starting OAuth**

Run:

```bash
uv run gdocs-patch --help
uv run gdocs-patch auth login --help
uv run gdocs-patch auth login --client-secrets /path/that/does/not/exist
```

Expected:

- root help lists `auth`;
- login help lists `--client-secrets` and its default;
- the missing-file command prints the named path and exits with status 1 without opening a browser.

- [ ] **Step 3: Document Google setup and usage**

Expand `README.md` with these concrete instructions after Setup and before Development:

````markdown
## Google authentication

Enable the Google Docs API in a Google Cloud project, configure its OAuth
consent screen, and create an OAuth client with application type **Desktop
app**. Download its client JSON.

Pass that file explicitly:

```console
uv run gdocs-patch auth login --client-secrets ~/Downloads/client_secret.json
```

Or save it at the default location and omit the option:

```console
mkdir -p ~/.config/gdocs-patch
cp ~/Downloads/client_secret.json ~/.config/gdocs-patch/client_secret.json
uv run gdocs-patch auth login
```

The command prints and opens Google's authorization URL. On a remote or
headless host, open the printed URL in another browser. After authorization,
the browser may fail to connect to localhost; copy its complete callback URL
from the address bar and paste it into the waiting command.

Refreshable user credentials are saved at
`~/.config/gdocs-patch/credentials.json`. Treat this file as a secret.

Sandbox environments can instead provide an automatically updated bearer
token:

```console
export GDOCS_PATCH_BEARER_TOKEN="..."
```

The environment token takes precedence over saved user credentials.

## Google Docs client

The client returns decoded Google API responses and accepts batch-update
request dictionaries without parsing or compiling them:

```python
from gdocs_patch.client import GoogleDocsClient, load_credentials
from gdocs_patch.compiler import compile_document
from gdocs_patch.parsers import document_parser

client = GoogleDocsClient(credentials=load_credentials())
response = client.get_document(document_id="DOCUMENT_ID")
source = document_parser.parse(response)

target = source  # Replace with an independently transformed document.
batch = compile_document(source=source, target=target)
client.batch_update(document_id=source.document_id, body=batch)
```
````

Keep the existing Usage and Development commands. Do not document service accounts or Drive authorization.

- [ ] **Step 4: Run complete regression verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
```

Expected: all 100 existing tests and every static/pre-commit check pass.

Also verify branch isolation:

```bash
git status --short --branch
git -C ../.. status --short --branch
```

Expected: feature changes exist only on `feature-google-docs-client`; main contains only its pre-existing untracked sample JSON.

- [ ] **Step 5: Commit CLI and documentation**

```bash
git add gdocs_patch/cli.py README.md
git commit -m "feat: add Google authentication command"
```

## Developer-run Google verification

After implementation, the developer manually verifies the external integration with their Google desktop client and a document they can edit:

```console
uv run gdocs-patch auth login --client-secrets /secure/path/client_secret.json
```

Complete login once through the automatic localhost callback and once from a remote shell by pasting the browser callback URL. Confirm:

```console
stat -f '%Lp %N' ~/.config/gdocs-patch/credentials.json
```

Expected on macOS: mode `600`.

Then run a no-change read/compile/update cycle with a real document ID:

```python
from gdocs_patch.client import GoogleDocsClient, load_credentials
from gdocs_patch.compiler import compile_document
from gdocs_patch.parsers import document_parser

client = GoogleDocsClient(credentials=load_credentials())
source = document_parser.parse(client.get_document(document_id="DOCUMENT_ID"))
batch = compile_document(source=source, target=source)
client.batch_update(document_id=source.document_id, body=batch)
```

The read must return tabs, parsing must succeed, and the no-change batch must complete without altering document content.
