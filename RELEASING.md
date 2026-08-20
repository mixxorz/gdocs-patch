# Releasing gdocs-patch

Releases are created manually in GitHub after a version change passes CI on
`main`. Publishing a GitHub Release builds the distributions again and uploads
them to PyPI through Trusted Publishing.

## Choose a version

Use canonical PEP 440 versions and tags without a `v` prefix:

- Alpha: `0.2.0a1`
- Beta: `0.2.0b1`
- Release candidate: `0.2.0rc1`
- Final: `0.2.0`

PyPI distributions are immutable. Never reuse a version that has been uploaded.

## Prepare the release

Create a branch from the latest `main`, then update the project version and
lockfile:

```console
uv version VERSION
uv lock
```

Replace `VERSION` with the exact PEP 440 version. Verify that both
`pyproject.toml` and `uv.lock` contain it.

Synchronize all development and optional dependencies and run the complete
local checks:

```console
uv sync --locked --dev --all-extras
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run fixit lint .
uv run pyright
uv run pre-commit run --all-files
rm -rf dist
uv build
uv run twine check --strict dist/*
```

Commit the version change, open a pull request, and merge it only after all
required CI checks pass.

## Publish the release

From GitHub's **Releases** page:

1. Draft a new release.
2. Create a tag that exactly matches the version in `pyproject.toml` and target
   the merged commit on `main`.
3. Use the version as the release title.
4. Generate the release notes and edit them if needed.
5. For an alpha, beta, or release candidate, select **Set as a pre-release**.
6. Publish the release.

Publishing triggers `.github/workflows/release.yml`. The workflow verifies the
tag, version, lockfile, and relationship to `main`; builds and validates the
wheel and source distribution; and authenticates to PyPI with GitHub OIDC.

## Recover from a failed release

If the workflow fails before PyPI accepts any artifact, correct the repository
or Trusted Publisher configuration and rerun the failed workflow.

If any artifact reached PyPI, or PyPI reports that the version already exists,
do not delete, replace, or skip that artifact. Prepare and publish a new version
instead. For example, follow `0.2.0a1` with `0.2.0a2` or follow a broken `0.2.0`
with `0.2.1`.
