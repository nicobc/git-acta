import click

from gitclerk.cli.shared import CLIGroup, strip_comments
from gitclerk.github.milestone import (
    milestone_create,
    milestone_list,
    milestone_reopen,
    parse_epic_body,
)


def _open_epic_editor(hint: str) -> tuple[str, list[str]]:
    template = (
        f"# {hint}\n# Lines starting with '#' are ignored.\n\n"
        "Description goes here.\n\n"
        "Notes:\n- note one\n- note two\n"
    )
    raw = click.edit(template)
    result = strip_comments(raw or "")
    if not result:
        raise click.Abort()
    return parse_epic_body(result)


@click.group(cls=CLIGroup)
def epic() -> None:
    """Manage epics (GitHub milestones)."""


@epic.command(name="new")
@click.argument("title")
@click.argument("description", required=False, default=None)
@click.option("--scope", required=True, help="Scope used for branch names in this epic.")
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the epic body.")
def epic_new(title: str, description: str | None, scope: str, edit_body: bool) -> None:
    """Create a new epic."""
    if description and edit_body:
        raise click.UsageError("DESCRIPTION and --edit are mutually exclusive")
    notes: list[str] = []
    if edit_body:
        description, notes = _open_epic_editor(title)
    number = milestone_create(title, scope, description or "", notes)
    click.echo(f"Epic #{number} created.")


@epic.command(name="list")
def epic_list() -> None:
    """List open epics."""
    milestones = milestone_list()
    if not milestones:
        click.echo("No open epics.")
        return
    for m in milestones:
        scope = m.scope or "—"
        click.echo(
            f"#{m.number:<4} {m.title:<40} scope: {scope:<20}"
            f" [{m.open_issues} open, {m.closed_issues} closed]"
        )


@epic.command(name="reopen")
@click.argument("number", type=int)
def epic_reopen(number: int) -> None:
    """Reopen a closed epic."""
    milestone_reopen(number)
    click.echo(f"Epic #{number} reopened.")
