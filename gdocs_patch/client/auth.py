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

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def save_credentials(credentials: Credentials) -> None:
    DEFAULT_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    DEFAULT_CREDENTIALS_PATH.touch(mode=0o600, exist_ok=True)
    DEFAULT_CREDENTIALS_PATH.chmod(0o600)
    to_json = cast(Callable[[], str], cast(Any, credentials).to_json)
    DEFAULT_CREDENTIALS_PATH.write_text(to_json(), encoding="utf-8")


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

    from_client_secrets_file = cast(
        Callable[..., InstalledAppFlow],
        cast(Any, InstalledAppFlow).from_client_secrets_file,
    )
    flow = from_client_secrets_file(
        str(client_secrets_path),
        scopes=[DOCS_SCOPE],
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = f"http://localhost:{callback_server.server_port}/"
    get_authorization_url = cast(
        Callable[..., tuple[str, str]],
        cast(Any, flow).authorization_url,
    )
    authorization_url, _ = get_authorization_url(prompt="consent")

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
    fetch_token = cast(Callable[..., Any], cast(Any, flow).fetch_token)
    fetch_token(authorization_response=authorization_response)
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

    from_authorized_user_file = cast(
        Callable[..., Credentials],
        cast(Any, Credentials).from_authorized_user_file,
    )
    credentials = from_authorized_user_file(
        str(DEFAULT_CREDENTIALS_PATH),
        scopes=[DOCS_SCOPE],
    )
    if credentials.expired:
        refresh = cast(Callable[[Request], None], cast(Any, credentials).refresh)
        refresh(Request())
        save_credentials(credentials)
    return credentials
