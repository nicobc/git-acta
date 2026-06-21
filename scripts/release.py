#!/usr/bin/env python3
"""Cut a git-clerk release: bump the version, ship it, tag it, and watch the publish job.

Maintainer-only — this script is not part of the published package. Run from the repo root:

    uv run scripts/release.py            # version derived from commits since the last tag
    uv run scripts/release.py --stable   # one-time promotion of a 0.x project to v1.0.0

Git tags are the source of truth for the version; pyproject.toml is overwritten to mirror
the new tag. The tag is computed with the same function `git clerk release` uses, so the
script and the tag it pushes always agree.
"""

import argparse
import re
import subprocess
import time
from pathlib import Path

from gitclerk.git.tag import fetch_tags, list_tags, next_release_tag

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
PUBLISH_WORKFLOW = "publish.yml"
RUN_POLL_INTERVAL = 5  # seconds between checks for the publish run to appear
RUN_QUEUE_TIMEOUT = 60  # give up if the publish run has not appeared within this many seconds

_VERSION_RE = re.compile(r'^version = ".*"', re.MULTILINE)


def run(*command: str) -> None:
    subprocess.run(command, check=True)


def capture(*command: str) -> str:
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def write_pyproject_version(new_version: str) -> None:
    new_text, replaced = _VERSION_RE.subn(
        f'version = "{new_version}"', PYPROJECT.read_text(), count=1
    )
    if not replaced:
        raise SystemExit("release: no version line found in pyproject.toml")
    PYPROJECT.write_text(new_text)


def wait_for_publish_run(tag: str) -> str:
    """Poll until the publish run triggered by `tag` appears, then return its id."""
    deadline = time.monotonic() + RUN_QUEUE_TIMEOUT
    while time.monotonic() < deadline:
        run_id = capture(
            "gh",
            "run",
            "list",
            "--workflow",
            PUBLISH_WORKFLOW,
            "--branch",
            tag,
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[0].databaseId // empty",
        )
        if run_id:
            return run_id
        time.sleep(RUN_POLL_INTERVAL)
    raise SystemExit(f"release: publish run for {tag} did not start within {RUN_QUEUE_TIMEOUT}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive the version, ship, tag, and publish.")
    parser.add_argument(
        "--stable", action="store_true", help="Promote a 0.x project to v1.0.0 (one-time)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the version and steps without changing anything.",
    )
    args = parser.parse_args()
    stable: bool = args.stable
    dry_run: bool = args.dry_run

    fetch_tags()
    try:
        new_tag = next_release_tag(list_tags(), stable)
    except ValueError as error:
        raise SystemExit(f"release: {error}")
    new_version = new_tag.removeprefix("v")
    title = f"bump version to {new_version}"

    if dry_run:
        print(f"release: would tag {new_tag}")
        print(f"  set pyproject.toml + uv.lock to {new_version}")
        print(f'  git-clerk branch/commit/pr/ship for "{title}"')
        print(f"  git-clerk release{' --stable' if stable else ''} -y, then watch the publish job")
        return

    write_pyproject_version(new_version)
    run("uv", "lock")  # keep uv.lock's self-version in sync so the bump commit carries it

    run("git-clerk", "branch", "chore/bump-version")
    run("git-clerk", "commit", "-A", title)
    run("git-clerk", "pr", title)
    run("git-clerk", "ship", "-y")
    run("git-clerk", "release", *(["--stable"] if stable else []), "-y")

    print(f"release: watching publish job for {new_tag}")
    run("gh", "run", "watch", wait_for_publish_run(new_tag), "--exit-status")


if __name__ == "__main__":
    main()
