# CI and PyPI Release Design

## Goal

Prepare `gdocs-patch` for its first public package release with continuous integration, validated distribution builds, documented versioning, and a manual GitHub Release flow that publishes to PyPI through Trusted Publishing. The flow should retain the simplicity of `slippers` while adding checks that prevent publishing an invalid or mismatched package.

## Scope

This work includes:

- CI for every push and pull request targeting `main`;
- support verification on Python 3.12, 3.13, and 3.14;
- package build, metadata, and installed-wheel smoke checks;
- release publication from a GitHub Release through PyPI Trusted Publishing;
- Python 3.14 as the default development/tooling interpreter while preserving Python 3.12 compatibility;
- complete package metadata and an MIT license;
- release documentation, including prereleases;
- a GitHub `pypi` environment and `main` branch protection.

This work does not add tox, changelog automation, TestPyPI publication, coverage thresholds, Dependabot, or automated live Google API tests. Live tests need user credentials and can mutate external documents, so they remain part of the manual exploratory process.

## Continuous Integration

Add `.github/workflows/tests.yml`, triggered by pushes to `main` and pull requests targeting `main`. The workflow uses read-only repository permissions, `uv`, locked dependencies, dependency caching, and concurrency cancellation for superseded runs on the same branch or pull request.

The workflow exposes these independently required jobs:

### `lint`

Run on Python 3.14 and verify:

- the lockfile is current;
- development dependencies and all optional extras synchronize from the lockfile;
- Ruff lint passes;
- Ruff formatting is unchanged;
- Fixit reports no violations;
- strict Pyright passes using the configured Python 3.12 language target;
- all pre-commit hooks, including Gitleaks, pass without changing files.

The existing Fixit pre-commit hook applies automatic fixes. In CI, any resulting file modification causes pre-commit to fail, while the explicit `fixit lint .` invocation provides a non-mutating diagnostic check.

### `Test - Python 3.x`

Use a matrix containing Python 3.12, 3.13, and 3.14. Each matrix entry synchronizes the locked development environment, including all optional extras, for that interpreter and runs the complete pytest suite. Installing the `mcp` extra is necessary for clean-environment analysis and testing of the optional server modules. There is no tox layer because the project has no framework or dependency-version factors; the GitHub Actions matrix supplies the only required variation.

### `package`

Run on Python 3.14 and:

1. build the wheel and source distribution with `uv build`;
2. validate both distributions strictly with Twine;
3. install the wheel into a clean base environment and smoke-test `gdocs-patch --help`, `gdocs-patch --version`, and the expected nonzero diagnostic from `gdocs-patch-mcp` when its extra is absent;
4. install the wheel with its `mcp` extra into a separate clean environment, run `gdocs-patch-mcp --help`, and import the server with a temporary bearer token to prove its optional dependencies load without starting a persistent server.

These checks verify the built artifact rather than importing the source checkout. Packaging explicitly excludes `.DS_Store` files.

## Python Support and Tooling

The package continues to declare `requires-python = ">=3.12"`. Python 3.12 remains supported through October 2028, while Python 3.13 and 3.14 cover newer active releases.

Set `.python-version` to 3.14 so local development, lockfile maintenance, and single-version CI jobs use Python 3.14 by default. Keep Ruff's target and Pyright's language version at Python 3.12. This catches syntax or typing assumptions that would violate the minimum advertised version even when tools execute under Python 3.14.

Add Twine as a locked development dependency so distribution validation is reproducible. Continue managing all dependencies and commands with `uv`.

## Package Metadata and License

Complete the `[project]` metadata with:

- author name and email matching `slippers`;
- the SPDX license expression `MIT`;
- a tracked `LICENSE` file containing the MIT License text;
- homepage, repository, and issue-tracker URLs for `mixxorz/gdocs-patch`;
- classifiers for alpha development status, OS independence, Python 3, and Python 3.12 through 3.14.

Do not add a legacy license classifier alongside the SPDX expression. Build configuration explicitly excludes `.DS_Store` files from distributions; existing ignore rules continue to exclude build directories and other local-only files from version control.

## Versioning and Release Initiation

Versions are maintained manually in `pyproject.toml`. A release change updates that version, refreshes `uv.lock`, and merges through normal protected-branch CI before a GitHub Release is created.

Tags exactly match the canonical PEP 440 version without a `v` prefix:

- alpha: `0.2.0a1`;
- beta: `0.2.0b1`;
- release candidate: `0.2.0rc1`;
- final: `0.2.0`.

A GitHub Release for an alpha, beta, or release candidate is marked as a pre-release. Publishing any of these release types triggers the same PyPI workflow. GitHub's autogenerated release notes provide the changelog for the initial process.

## PyPI Publication

Add `.github/workflows/release.yml`, triggered only when a GitHub Release is published. The publication job:

1. checks out the release tag;
2. confirms that the tag is attached to a commit contained in `main`;
3. reads the project version and requires the release tag to match it exactly;
4. verifies that `uv.lock` is current;
5. rebuilds the wheel and source distribution from the tagged source;
6. validates both distributions with Twine;
7. publishes through `pypa/gh-action-pypi-publish`.

The workflow grants `contents: read` and job-level `id-token: write`. It does not read or store a PyPI API token. The publish job uses the GitHub `pypi` environment and identifies the PyPI project URL as its deployment URL.

PyPI artifacts are immutable. If publication partially succeeds or PyPI already contains a version, the workflow must not try to replace that version. Recovery consists of diagnosing the failure, incrementing to a new PEP 440 version, and publishing a new release.

## Trusted Publisher Setup

Create the `pypi` environment in the GitHub repository. The repository owner must perform one external setup step in PyPI: register `mixxorz/gdocs-patch`, `.github/workflows/release.yml`, and environment `pypi` as a Trusted Publisher. `RELEASING.md` documents this prerequisite and the exact normal release sequence.

## Repository Protection

After the new workflow has produced its check names, configure `main` branch protection to require:

- `lint`;
- `Test - Python 3.12`;
- `Test - Python 3.13`;
- `Test - Python 3.14`;
- `package`;
- one approving review, with stale approvals dismissed;
- the branch to be up to date before merging.

Disable force pushes and branch deletion. Match `slippers` by not enforcing these rules for administrators.

## Documentation

Add `RELEASING.md` covering:

- one-time PyPI Trusted Publisher registration;
- final and prerelease PEP 440 formats;
- version and lockfile update commands;
- local verification commands;
- creation of a GitHub Release with autogenerated notes;
- the immutable-artifact recovery policy.

The README's development guidance should identify Python 3.14 as the default development version while stating that the package supports Python 3.12 and newer.

## Verification and Success Criteria

The work is complete when:

- all existing tests pass on Python 3.12, 3.13, and 3.14 in GitHub Actions;
- Ruff, Ruff format, Fixit, Pyright, pre-commit, and Gitleaks pass in CI;
- a clean wheel and source distribution build and pass strict metadata checks;
- installed-package smoke tests pass for the base package and MCP extra;
- the release workflow has only the permissions needed for checkout and OIDC publication;
- package metadata includes the approved author, URLs, classifiers, and MIT license;
- the release guide fully describes final and prerelease publication;
- the GitHub `pypi` environment and required `main` protections are configured;
- no existing user worktree files or untracked exploratory artifacts are included in the implementation commits or release distributions.
