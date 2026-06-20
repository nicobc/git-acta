import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from gitclerk.cli import main
from gitclerk.git.tag import list_tags


@pytest.mark.usefixtures("git_repo")
def test_calver_creates_tag(runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--calver", "-y"])
    assert result.exit_code == 0, result.output
    assert len(list_tags(pattern="*")) == 1


@pytest.mark.usefixtures("git_repo")
def test_semver_creates_initial_tag(runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.1.0" in list_tags()


@pytest.mark.usefixtures("git_repo")
def test_semver_increments_existing_tag(runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
    result = runner.invoke(main, ["release", "--semver", "--bump", "minor", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.2.0" in list_tags()


@pytest.mark.usefixtures("git_repo")
def test_tag_is_pushed_to_remote(bare_remote: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
    remote_tags = (
        subprocess.run(
            ["git", "tag", "--list"],
            capture_output=True,
            text=True,
            cwd=bare_remote,
        )
        .stdout.strip()
        .splitlines()
    )
    assert "v0.1.0" in remote_tags
