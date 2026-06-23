"""Track the active issue in local git config (key ``clerk.active-issue``)."""

import subprocess

from acta.git import git


def get_active_issue() -> int | None:
    """Return the issue number recorded for this repo, or None if none is set."""
    try:
        config_value = git("config", "--get", "clerk.active-issue", capture=True)
        return int(config_value) if config_value else None
    except subprocess.CalledProcessError:
        return None


def set_active_issue(number: int) -> None:
    """Record ``number`` as the active issue, so ``acta pr`` can append ``Closes #N``."""
    git("config", "clerk.active-issue", str(number))


def clear_active_issue() -> None:
    """Remove the active-issue record; a no-op if none is set."""
    try:
        git("config", "--unset", "clerk.active-issue")
    except subprocess.CalledProcessError:
        pass
