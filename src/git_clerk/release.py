import re
from datetime import date
from typing import Final, Literal, TypeAlias

CALVER: Final = "CalVer"
SEMVER: Final = "SemVer"
Scheme: TypeAlias = Literal["CalVer", "SemVer"]

_CALVER_RE = re.compile(r"v\d{4}\.\d{2}\.\d+")
_SEMVER_RE = re.compile(r"v\d+\.\d+\.\d+")


def detect_scheme(tags: list[str]) -> Scheme | None:
    found: set[Scheme] = set()
    for t in tags:
        if _CALVER_RE.fullmatch(t):
            found.add(CALVER)
        elif _SEMVER_RE.fullmatch(t):
            found.add(SEMVER)
    if not found:
        return None
    if len(found) > 1:
        raise ValueError(
            f"mixed {CALVER} and {SEMVER} tags found — pass --calver or --semver to proceed"
        )
    return next(iter(found))


def next_calver(tags: list[str], today: date) -> str:
    prefix = f"v{today.year}.{today.month:02d}."
    existing = [t for t in tags if re.fullmatch(rf"{re.escape(prefix)}\d+", t)]
    last = max((int(t[len(prefix) :]) for t in existing), default=0)
    return f"{prefix}{last + 1}"


def next_semver(tags: list[str], bump: str) -> str:
    semver_tags = sorted(
        [t for t in tags if _SEMVER_RE.fullmatch(t) and not _CALVER_RE.fullmatch(t)],
        key=lambda t: tuple(int(x) for x in t[1:].split(".")),
    )
    if not semver_tags:
        return "v0.1.0"
    major, minor, patch = (int(x) for x in semver_tags[-1][1:].split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"
