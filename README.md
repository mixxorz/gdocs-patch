# gdocs-patch

A Python CLI for applying structured patches to Google Docs.

## Setup

Install Python 3.12 and the project dependencies with [uv](https://docs.astral.sh/uv/):

```console
uv sync --dev
```

## Usage

```console
uv run gdocs-patch --help
uv run gdocs-patch --version
```

## Read a document

The `read` command accepts one JSON object on standard input and writes canonical
XHTML directly to standard output:

```console
printf '%s\n' '{"docId":"DOCUMENT_ID","offset":8,"limit":4}' \
  | uv run gdocs-patch read
```

`offset` is an optional one-based line number, and `limit` is an optional line
count. The output is raw, unnumbered XHTML, so it can be redirected to a file or
passed directly to another tool without stripping line prefixes.

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

## Development

Run the test and static-analysis tools:

```console
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Install and run the Git hooks:

```console
uv run pre-commit install
uv run pre-commit run --all-files
```
