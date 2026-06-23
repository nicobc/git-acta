"""Thin wrappers around the GitHub CLI (`gh`) and origin-repo resolution."""

import functools
import subprocess
from urllib.parse import urlparse

from acta.git import get_remote_url


def parse_repo_from_url(url: str) -> str:
    """Extract the ``owner/repo`` slug from a git remote URL.

    Handles both SSH (``git@github.com:owner/repo.git``) and HTTPS
    (``https://github.com/owner/repo.git``) forms.

    Args:
        url: The remote URL.

    Returns:
        The ``owner/repo`` slug.

    Raises:
        ValueError: If the URL has no parseable ``owner/repo`` path.

    Example:
        >>> parse_repo_from_url("git@github.com:nicobc/git-acta.git")
        'nicobc/git-acta'
    """
    if "://" in url:
        path = urlparse(url).path.lstrip("/")
    else:
        _, _, path = url.partition(":")
    repo_slug = path.removesuffix(".git")
    repo_parts = repo_slug.split("/")
    if len(repo_parts) != 2 or not all(repo_parts):
        raise ValueError(f"cannot parse GitHub repo from remote URL: {url}")
    return repo_slug


def gh(*args: str, capture: bool = False) -> str:
    """Run a `gh` (GitHub CLI) command.

    `capture` returns stdout. Raises RuntimeError if `gh` is not installed; on
    command failure the CalledProcessError propagates (CLIGroup surfaces its
    stderr).
    """
    try:
        completed_process = subprocess.run(
            ["gh", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
        return completed_process.stdout.strip() if completed_process.stdout else ""
    except FileNotFoundError:
        raise RuntimeError(
            "'gh' not found in PATH — install the GitHub CLI: https://cli.github.com"
        )
    except subprocess.CalledProcessError:
        raise


@functools.cache
def get_repo() -> str:
    """Return the ``owner/repo`` slug for the origin remote, cached for the process.

    Raises:
        RuntimeError: If origin's URL can't be parsed into ``owner/repo``.
    """
    origin_url = get_remote_url("origin")
    try:
        return parse_repo_from_url(origin_url)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
