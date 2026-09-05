# Releasing workspace packages

`gdocs-patch` and `gsheets-patch` have independent versions. Publishing a GitHub
Release triggers `.github/workflows/release.yml`, which builds and uploads only
the package named by the tag. A branch push or pull request never publishes.

## Prepare a release

From a feature branch based on current `main`, update the selected member:

```console
uv version --package gsheets-patch 0.1.0
uv lock
uv sync --locked --all-packages --all-extras --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m fixit lint .
uv run pyright
uv run pre-commit run --all-files
bash scripts/smoke-package.sh gsheets-patch
```

Use canonical PEP 440 versions: `0.1.0a1`, `0.1.0b1`, `0.1.0rc1`, or `0.1.0`.
Check the selected member's `pyproject.toml` and the root lockfile. The other
package's version does not need to change.

Commit, open a PR, and merge only after all required checks pass. Release-tooling
tests run under development Python 3.14; package CI covers Python 3.10–3.14.

## Trusted Publishing prerequisite

Configure a PyPI Trusted Publisher for **each distribution** using:

- GitHub owner: `mixxorz`
- Repository: `gdocs-patch`
- Workflow: `release.yml`
- GitHub environment: `pypi`

For a new distribution, configure a pending publisher before its first release.
The existing Docs publisher can keep the same repository/workflow/environment.
The `pypi` GitHub environment may require approval according to its existing rules.
These account settings are external setup, not something the workflow creates.

## Publish

In GitHub Releases, create a tag targeting the merged commit:

```text
gdocs-patch/0.2.1
gsheets-patch/0.1.0
```

The version suffix must exactly match the selected member's version. Mark alpha,
beta, and release-candidate versions as GitHub pre-releases. Use the package and
version in the release title and describe only that package's changes.

Publishing the release verifies:

1. The tagged commit is contained in `main`.
2. The tag selects an allowed workspace member.
3. The version matches its metadata and is canonical PEP 440.
4. The GitHub prerelease flag agrees with that version.
5. The shared lockfile is current and built distributions have valid metadata.

Only that member's wheel and sdist are passed to PyPI through GitHub OIDC.
Existing historical unqualified Docs tags remain untouched. New workspace
releases reject unqualified tags; do not reuse old tags to test the new workflow.

## Failed releases

PyPI versions are immutable. If no artifact was accepted, fix the cause and rerun
the failed workflow. If any artifact reached PyPI, prepare a new version instead
of replacing, deleting, or skipping it. Never publish merely to test CI.
