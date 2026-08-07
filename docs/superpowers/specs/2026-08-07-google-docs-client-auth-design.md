# Google Docs Client and Authentication Design

## Goal

Connect `gdocs-patch` to Google Docs through a small transport client and add `gdocs-patch auth login` for obtaining refreshable user credentials.

Authentication supports two environments:

- a desktop or remote interactive login using Google OAuth;
- a sandbox-provided bearer token in `GDOCS_PATCH_BEARER_TOKEN`.

The client remains a dumb transport boundary. It does not parse API responses, compile document changes, or choose credentials.

## Package structure

Add a semantic client package:

```text
gdocs_patch/client/
├── __init__.py
├── auth.py
└── google_docs.py
```

`gdocs_patch.client` exports `AuthenticationError`, `GoogleDocsClient`, `load_credentials`, and `login`.

Add `google-auth-oauthlib` for installed-application OAuth and `google-api-python-client` for the Google Docs service.

## Public API

### Authentication

```python
DOCS_SCOPE = "https://www.googleapis.com/auth/documents"


class AuthenticationError(Exception):
    pass


def login(*, client_secrets: Path | None = None) -> Path:
    """Complete interactive OAuth, save credentials, and return their path."""


def load_credentials() -> google.auth.credentials.Credentials:
    """Return credentials suitable for Google API clients."""
```

`login()` uses an explicit client-secrets path when provided. Otherwise it reads:

```text
~/.config/gdocs-patch/client_secret.json
```

It saves refreshable user credentials at:

```text
~/.config/gdocs-patch/credentials.json
```

The credentials file receives owner-only permissions where supported. An explicit login always runs OAuth even when `GDOCS_PATCH_BEARER_TOKEN` is set.

`load_credentials()` applies this precedence:

1. If `GDOCS_PATCH_BEARER_TOKEN` is present, return fixed Google credentials containing that token. The loader does not validate or refresh a sandbox token.
2. Otherwise load the saved authorized-user credentials.
3. If the saved access token is expired, refresh it and rewrite the credential file.
4. If neither source exists, raise `AuthenticationError` instructing the user to run `gdocs-patch auth login`.

### Google Docs transport

```python
class GoogleDocsClient:
    def __init__(self, *, credentials: Credentials) -> None: ...

    def get_document(self, *, document_id: str) -> dict[str, Any]: ...

    def batch_update(
        self,
        *,
        document_id: str,
        body: dict[str, object],
    ) -> dict[str, Any]: ...
```

Credentials are explicit rather than loaded by the client. `get_document()` calls `documents.get` with `includeTabsContent=True`. `batch_update()` forwards its body unchanged to `documents.batchUpdate`. Both methods return Google's decoded response dictionary.

The client does not depend on `gdocs_patch.models`, parsers, or the compiler.

## Interactive OAuth flow

`auth login` uses one Google installed-application authorization transaction with two concurrent ways to receive its loopback callback:

```text
localhost HTTP callback ─┐
                         ├─ first callback URL → token exchange
terminal paste ──────────┘
```

The flow is:

1. Read the desktop OAuth client configuration.
2. Create one authorization URL, OAuth state, and PKCE verifier.
3. Start a temporary loopback HTTP callback server.
4. print the authorization URL and attempt to open it in the user's browser.
5. Simultaneously prompt for the complete callback URL from the browser's address bar.
6. Use whichever valid callback arrives first, exchange its one-time code, and stop the callback server.
7. Save the resulting access and refresh credentials.

On a desktop, Google's redirect reaches the loopback server and no paste is needed. On a remote or headless host, the user opens the printed URL elsewhere. The browser's loopback redirect may show a connection failure, but the user can copy that complete URL and paste it into the waiting CLI.

This avoids unreliable headless detection, separate login modes, Google's deprecated out-of-band flow, and a hosted authentication relay. The terminal reader may remain blocked when the browser callback wins; it is a daemon used only by the short-lived login command and ends when that process exits.

## CLI

The CLI adds nested argparse commands:

```console
gdocs-patch auth login
gdocs-patch auth login --client-secrets ~/Downloads/client_secret.json
```

On success it prints the saved credentials path. `auth status` and `auth logout` are out of scope.

The call stack is:

```text
gdocs-patch auth login
    → client.auth.login()
    → Google OAuth authorization
    → ~/.config/gdocs-patch/credentials.json
```

## Application call stacks

Reading a document remains explicit:

```python
credentials = load_credentials()
client = GoogleDocsClient(credentials=credentials)
response = client.get_document(document_id=document_id)
document = document_parser.parse(response)
```

Applying a target document also keeps transport separate from compilation:

```python
batch = compile_document(source=source, target=target)
client.batch_update(document_id=source.document_id, body=batch)
```

## Errors

- A missing default or supplied client-secrets file raises `AuthenticationError` and names the expected path.
- Missing runtime credentials raise `AuthenticationError` with the login command needed to recover.
- OAuth denial and refresh failures preserve Google's underlying error details.
- `GoogleDocsClient` preserves Google API `HttpError` failures rather than translating them.
- OAuth state and PKCE protect both loopback and pasted callbacks.
- A sandbox bearer token is accepted as supplied; authorization failures occur on the actual API request.

## Documentation and verification

README documentation covers:

- creating a Google desktop OAuth client with the Docs API enabled;
- the optional `--client-secrets` argument and default path;
- browser and remote callback behavior;
- credential storage;
- `GDOCS_PATCH_BEARER_TOKEN` precedence;
- direct `GoogleDocsClient` usage.

No automated tests are added for this increment. Mocking the OAuth server and dynamic Google SDK would primarily test wiring rather than prove the integration. Verification is manual against Google and includes both callback paths, credential permissions, sandbox-token loading, `documents.get`, and `documents.batchUpdate`. The existing test and static-analysis suites still run to catch regressions.

## Out of scope

- document-specific CLI commands;
- parsing or compiling inside `GoogleDocsClient`;
- service accounts;
- Drive scopes or Drive API operations;
- credential status, logout, or revocation commands;
- bearer-token refresh or validation;
- a hosted OAuth callback service.
