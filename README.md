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
