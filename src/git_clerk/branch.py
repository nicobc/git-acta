import re

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


_BRANCH_RE = re.compile(r"([^/]+)/([^/]+)")
_SCOPE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


def parse(branch: str) -> tuple[str, str]:
    m = _BRANCH_RE.fullmatch(branch)
    if not m:
        raise ValueError(f"Branch '{branch}' does not follow type/scope convention")
    type_ = m.group(1)
    if type_ not in TYPES:
        raise ValueError(
            f"'{type_}' is not a conventional commit type. Use one of: {', '.join(sorted(TYPES))}"
        )
    scope = m.group(2)
    if not _SCOPE_RE.fullmatch(scope):
        raise ValueError(
            f"'{scope}' is not a valid scope. Use letters, digits, hyphens, and underscores."
        )
    return type_, scope
