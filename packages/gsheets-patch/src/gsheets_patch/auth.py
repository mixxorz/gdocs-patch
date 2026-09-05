import os
import queue
import socketserver
import tempfile
import threading
import webbrowser
import wsgiref.simple_server
import wsgiref.util
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from google.auth.credentials import Credentials as GoogleCredentials
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (  # pyright: ignore[reportMissingTypeStubs]
    InstalledAppFlow,
)

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_ENVIRONMENT_VARIABLE = "GSHEETS_PATCH_BEARER_TOKEN"
CONFIG_DIRECTORY = Path.home() / ".config" / "gsheets-patch"
DEFAULT_CLIENT_SECRETS_PATH = CONFIG_DIRECTORY / "client_secret.json"
DEFAULT_CREDENTIALS_PATH = CONFIG_DIRECTORY / "credentials.json"


class AuthenticationError(Exception):
    """Raised when credentials required by gsheets-patch are unavailable."""


class QuietRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    """Avoid logging the one-time OAuth code contained in the request URL."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


class ThreadingWSGIServer(
    socketserver.ThreadingMixIn,
    wsgiref.simple_server.WSGIServer,
):
    """Handle callback connections without blocking the server accept loop."""

    daemon_threads = True


def save_credentials(credentials: Credentials) -> None:
    temporary_path: Path | None = None
    try:
        credentials_directory = DEFAULT_CREDENTIALS_PATH.parent
        credentials_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        to_json = cast(Callable[[], str], cast(Any, credentials).to_json)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=credentials_directory,
            prefix=f".{DEFAULT_CREDENTIALS_PATH.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_path.chmod(0o600)
            temporary_file.write(to_json())
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, DEFAULT_CREDENTIALS_PATH)
        temporary_path = None
    except (OSError, ValueError, GoogleAuthError) as error:
        raise AuthenticationError("Could not save Google credentials.") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def login(*, client_secrets: Path | None = None) -> Path:
    client_secrets_path = client_secrets or DEFAULT_CLIENT_SECRETS_PATH
    if not client_secrets_path.is_file():
        raise AuthenticationError(
            f"Google OAuth client secrets not found at {client_secrets_path}"
        )

    callbacks: queue.Queue[str] = queue.Queue(maxsize=1)
    redirect_uri = ""
    oauth_state = ""

    def submit_callback(callback_url: str) -> bool:
        try:
            candidate = urlsplit(callback_url)
            expected = urlsplit(redirect_uri)
        except ValueError:
            return False
        query = parse_qs(candidate.query, keep_blank_values=True)
        has_oauth_result = any(query.get(name, []) for name in ("code", "error"))
        if (
            candidate.scheme != expected.scheme
            or candidate.netloc != expected.netloc
            or candidate.path != expected.path
            or candidate.fragment
            or query.get("state") != [oauth_state]
            or not has_oauth_result
        ):
            return False

        try:
            callbacks.put_nowait(callback_url)
        except queue.Full:
            pass
        return True

    def receive_callback(
        environment: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        callback_url = wsgiref.util.request_uri(environment)
        accepted = submit_callback(callback_url)
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        if accepted:
            return [b"Authorization received. You may close this window."]
        return [b"Invalid authorization callback. Waiting for authorization."]

    callback_server = wsgiref.simple_server.make_server(
        "localhost",
        0,
        receive_callback,
        server_class=ThreadingWSGIServer,
        handler_class=QuietRequestHandler,
    )

    callback_server_thread: threading.Thread | None = None
    callback_server_started = False
    try:
        from_client_secrets_file = cast(
            Callable[..., InstalledAppFlow],
            cast(Any, InstalledAppFlow).from_client_secrets_file,
        )
        flow = from_client_secrets_file(
            str(client_secrets_path),
            scopes=[SHEETS_SCOPE],
            autogenerate_code_verifier=True,
        )
        redirect_uri = f"http://localhost:{callback_server.server_port}/"
        flow.redirect_uri = redirect_uri
        get_authorization_url = cast(
            Callable[..., tuple[str, str]],
            cast(Any, flow).authorization_url,
        )
        authorization_url, oauth_state = get_authorization_url(prompt="consent")

        print("Open this URL in a browser to authorize gsheets-patch:\n")
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
        callback_server_started = True

        def read_pasted_callback() -> None:
            while True:
                try:
                    callback_url = input("Callback URL: ").strip()
                except EOFError:
                    return
                if callback_url and submit_callback(callback_url):
                    return

        threading.Thread(target=read_pasted_callback, daemon=True).start()
        webbrowser.open(authorization_url, new=2)
        authorization_response = callbacks.get()

        # OAuthlib rejects an HTTP authorization-response URL even though Google
        # explicitly permits loopback HTTP redirects for installed applications.
        authorization_response = authorization_response.replace(
            "http://", "https://", 1
        )
        fetch_token = cast(Callable[..., Any], cast(Any, flow).fetch_token)
        fetch_token(authorization_response=authorization_response)
        credentials = cast(Credentials, flow.credentials)
        save_credentials(credentials)
        return DEFAULT_CREDENTIALS_PATH
    finally:
        if callback_server_started:
            callback_server.shutdown()
            if callback_server_thread is not None:
                callback_server_thread.join()
        callback_server.server_close()


def load_credentials() -> GoogleCredentials:
    bearer_token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE)
    if bearer_token is not None:
        return Credentials(token=bearer_token)

    if not DEFAULT_CREDENTIALS_PATH.is_file():
        raise AuthenticationError(
            "No Google credentials found. Run `gsheets-patch auth login`."
        )

    from_authorized_user_file = cast(
        Callable[..., Credentials],
        cast(Any, Credentials).from_authorized_user_file,
    )
    try:
        credentials = from_authorized_user_file(
            str(DEFAULT_CREDENTIALS_PATH),
            scopes=[SHEETS_SCOPE],
        )
    except (
        OSError,
        ValueError,
        AttributeError,
        TypeError,
        GoogleAuthError,
    ) as error:
        raise AuthenticationError("Could not load saved Google credentials.") from error
    if credentials.expired:
        refresh = cast(Callable[[Request], None], cast(Any, credentials).refresh)
        try:
            refresh(Request())
        except (OSError, ValueError, GoogleAuthError) as error:
            raise AuthenticationError(
                "Could not refresh Google credentials."
            ) from error
        save_credentials(credentials)
    return credentials
