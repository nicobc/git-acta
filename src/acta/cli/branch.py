"""``acta branch`` — create a type/scope branch from origin/main."""

import click

from acta.git.branch import fetch_origin, switch_new_branch
from acta.git.branch import parse as parse_branch


@click.command()
@click.argument("name", metavar="TYPE/SCOPE")
def branch(name: str) -> None:
    """Create a `type/scope` branch from the latest origin/main.

    Fetches origin, then branches off origin/main. The name sets the
    conventional-commit type and scope that `acta commit` and `acta pr` reuse —
    `feat/auth` produces `feat(auth): ...` messages. An optional third segment
    (`type/scope/topic`) adds a human-readable topic without changing type or scope.
    """
    try:
        parse_branch(name)
    except ValueError as error:
        raise click.ClickException(str(error))
    fetch_origin()
    switch_new_branch(name)
    click.echo(f"Branched {name} from origin/main.")
