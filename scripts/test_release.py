from pathlib import Path

import pytest

from scripts.release import select_release


@pytest.mark.parametrize(
    ("tag", "prerelease", "accepted"),
    [
        ("gdocs-patch/0.2.0", False, True),
        ("gsheets-patch/0.1.0a1", True, True),
        ("0.2.0", False, False),
        ("other/0.2.0", False, False),
        ("gdocs-patch/0.3.0", False, False),
        ("gsheets-patch/0.1.0a1", False, False),
    ],
)
def test_release_selection(
    tmp_path: Path, tag: str, prerelease: bool, accepted: bool
) -> None:
    for package, version in [("gdocs-patch", "0.2.0"), ("gsheets-patch", "0.1.0a1")]:
        directory = tmp_path / "packages" / package
        directory.mkdir(parents=True)
        (directory / "pyproject.toml").write_text(
            f'[project]\nname = "{package}"\nversion = "{version}"\n'
        )
    if accepted:
        assert select_release(root=tmp_path, tag=tag, prerelease=prerelease) == (
            "gsheets-patch" if prerelease else "gdocs-patch"
        )
    else:
        with pytest.raises(ValueError):
            select_release(root=tmp_path, tag=tag, prerelease=prerelease)
