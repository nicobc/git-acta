import subprocess
from pathlib import Path

from click.testing import CliRunner

from gitclerk.cli import main
from gitclerk.git.tag import tags


def test_calver_creates_tag(git_repo: Path, runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--calver", "-y"])
    assert result.exit_code == 0, result.output
    assert len(tags(pattern="*")) == 1


def test_semver_creates_initial_tag(git_repo: Path, runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.1.0" in tags()


def test_semver_increments_existing_tag(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
    result = runner.invoke(main, ["release", "--semver", "--bump", "minor", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.2.0" in tags()


def test_tag_is_pushed_to_remote(git_repo: Path, bare_remote: Path, runner: CliRunner) -> None:
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
