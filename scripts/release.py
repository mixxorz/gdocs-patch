"""Select one workspace distribution for a package-qualified GitHub release."""

import os
from pathlib import Path

import tomllib
from packaging.version import Version


def select_release(*, root: Path, tag: str, prerelease: bool) -> str:
    package, separator, version = tag.partition("/")
    if not separator or package not in ("gdocs-patch", "gsheets-patch"):
        raise ValueError("Use a gdocs-patch/VERSION or gsheets-patch/VERSION tag")
    metadata = root / "packages" / package / "pyproject.toml"
    project = tomllib.loads(metadata.read_text())["project"]
    if version != project["version"]:
        raise ValueError(f"Tag version {version} does not match {package}'s version")
    parsed = Version(version)
    if str(parsed) != version:
        raise ValueError("Release version must be canonical PEP 440")
    if parsed.is_prerelease != prerelease:
        raise ValueError("GitHub prerelease flag must match the package version")
    return package


if __name__ == "__main__":
    package = select_release(
        root=Path(__file__).resolve().parents[1],
        tag=os.environ["RELEASE_TAG"],
        prerelease=os.environ["RELEASE_IS_PRERELEASE"] == "true",
    )
    print(f"package={package}")
