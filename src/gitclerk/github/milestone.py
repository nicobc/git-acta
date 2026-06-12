import json
from dataclasses import dataclass

from gitclerk.github import gh, repo

_SCOPE_PREFIX = "scope: "
_NOTES_SEPARATOR = "\nNotes:\n"


@dataclass
class MilestoneListItem:
    number: int
    title: str
    scope: str
    description: str
    notes: list[str]
    open_issues: int
    closed_issues: int


@dataclass
class MilestoneDetail:
    number: int
    title: str
    scope: str
    description: str
    notes: list[str]
    open_issues: int
    state: str


def milestone_create(
    title: str,
    scope: str,
    description: str = "",
    notes: list[str] | None = None,
) -> int:
    gh_description = _build_description(scope, description, notes or [])
    out = gh(
        "api",
        f"repos/{repo()}/milestones",
        "--method",
        "POST",
        "-f",
        f"title={title}",
        "-f",
        f"description={gh_description}",
        capture=True,
    )
    return int(json.loads(out)["number"])


def milestone_list() -> list[MilestoneListItem]:
    out = gh("api", f"repos/{repo()}/milestones", "-X", "GET", "-f", "state=open", capture=True)
    items: list[MilestoneListItem] = []
    for m in json.loads(out):
        scope, description, notes = _parse_description(str(m.get("description") or ""))
        items.append(
            MilestoneListItem(
                number=int(m["number"]),
                title=str(m["title"]),
                scope=scope,
                description=description,
                notes=notes,
                open_issues=int(m["open_issues"]),
                closed_issues=int(m["closed_issues"]),
            )
        )
    return items


def milestone_view(number: int) -> MilestoneDetail:
    out = gh("api", f"repos/{repo()}/milestones/{number}", capture=True)
    raw = json.loads(out)
    scope, description, notes = _parse_description(str(raw.get("description") or ""))
    return MilestoneDetail(
        number=int(raw["number"]),
        title=str(raw["title"]),
        scope=scope,
        description=description,
        notes=notes,
        open_issues=int(raw["open_issues"]),
        state=str(raw["state"]),
    )


def milestone_reopen(number: int) -> None:
    gh("api", f"repos/{repo()}/milestones/{number}", "--method", "PATCH", "-f", "state=open")


def milestone_close(number: int) -> None:
    gh("api", f"repos/{repo()}/milestones/{number}", "--method", "PATCH", "-f", "state=closed")


def parse_epic_body(text: str) -> tuple[str, list[str]]:
    """Parse editor or inline body into (description, notes)."""
    if _NOTES_SEPARATOR in text:
        desc_part, notes_part = text.split(_NOTES_SEPARATOR, 1)
        description = desc_part.strip()
        notes = [line[2:] for line in notes_part.splitlines() if line.strip().startswith("- ")]
    else:
        description = text.strip()
        notes = []
    return description, notes


def _build_description(scope: str, description: str, notes: list[str]) -> str:
    parts = [f"scope: {scope}"]
    if description:
        parts.append(description)
    if notes:
        parts.append("Notes:\n" + "\n".join(f"- {n}" for n in notes))
    return "\n\n".join(parts)


def _parse_description(raw: str) -> tuple[str, str, list[str]]:
    """Returns (scope, description, notes) from a GitHub milestone description."""
    lines = raw.split("\n")
    scope = ""
    if lines and lines[0].startswith(_SCOPE_PREFIX):
        scope = lines[0][len(_SCOPE_PREFIX) :]
        rest = "\n".join(lines[1:]).strip()
    else:
        rest = raw.strip()
    description, notes = parse_epic_body(rest)
    return scope, description, notes
