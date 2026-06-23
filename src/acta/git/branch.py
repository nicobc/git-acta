import re

from acta.git import git

TYPES = frozenset(
    [
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    ]
)

# type/scope, with an optional third descriptive segment (e.g. an issue topic);
# the conventional-commit type and scope are derived from the first two.
_BRANCH_RE = re.compile(r"([^/]+)/([^/]+)(?:/.+)?")
_SCOPE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


def parse(branch: str) -> tuple[str, str]:
    """Extract the conventional-commit type and scope from a branch name.

    Branch names follow ``type/scope`` with an optional third descriptive
    segment (``type/scope/topic``); only the first two segments are significant.

    Args:
        branch: Branch name to parse, e.g. ``fix/auth`` or ``feat/auth/sso``.

    Returns:
        The ``(type, scope)`` pair.

    Raises:
        ValueError: If the name doesn't match ``type/scope``, the type is not a
            conventional-commit type, or the scope has invalid characters.

    Example:
        >>> parse("feat/auth/sso")
        ('feat', 'auth')
    """
    branch_match = _BRANCH_RE.fullmatch(branch)
    if not branch_match:
        raise ValueError(f"Branch '{branch}' does not follow type/scope convention")
    type_ = branch_match.group(1)
    if type_ not in TYPES:
        raise ValueError(
            f"'{type_}' is not a conventional commit type. Use one of: {', '.join(sorted(TYPES))}"
        )
    scope = branch_match.group(2)
    if not _SCOPE_RE.fullmatch(scope):
        raise ValueError(
            f"'{scope}' is not a valid scope. Use letters, digits, hyphens, and underscores."
        )
    return type_, scope


def get_current_branch() -> str:
    """Return the name of the currently checked-out branch."""
    return git("branch", "--show-current", capture=True)


def fetch_origin() -> None:
    """Download the latest state from origin and clean up stale branch pointers.

    Git keeps a local read-only pointer for each branch on origin, named
    ``origin/<branch>`` (a "remote-tracking ref") — its snapshot of where that
    branch was at the last fetch. ``--prune`` deletes the pointers for branches
    that have since been removed on origin (for example after their PR merged),
    so they don't pile up and shadow names a new branch may want to reuse.
    """
    git("fetch", "--prune", "origin", quiet=True)


def prune_origin() -> None:
    """Delete local pointers to branches that no longer exist on origin.

    Like the prune half of ``fetch_origin`` but without downloading anything:
    it only removes the local ``origin/<branch>`` pointers whose branch is gone
    on origin. Used right after merging a PR (whose branch was deleted) to keep
    the local view in sync.
    """
    git("remote", "prune", "origin", quiet=True)


def switch_new_branch(name: str) -> None:
    """Create branch ``name`` from origin/main and check it out."""
    git("switch", "-c", name, "origin/main", quiet=True)


def switch_main() -> None:
    """Check out the main branch."""
    git("switch", "main", quiet=True)


def pull_origin_main() -> None:
    """Update the current branch with the latest commits from origin/main."""
    git("pull", "origin", "main", quiet=True)


def branch_exists(name: str) -> bool:
    """Return True if a local branch named ``name`` exists."""
    return bool(git("branch", "--list", name, capture=True))


def delete_branch(name: str) -> None:
    """Force-delete the local branch ``name``, discarding unmerged commits."""
    git("branch", "-D", name, quiet=True)


def switch_branch(name: str) -> None:
    """Check out the existing branch ``name``."""
    git("switch", name, quiet=True)


def merge_origin_main() -> None:
    """Merge origin/main into the current branch."""
    git("merge", "origin/main", quiet=True)
