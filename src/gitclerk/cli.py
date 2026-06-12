import subprocess
import sys
from datetime import date

import click

from gitclerk.git.branch import (
    TYPES,
    current_branch,
    delete_branch,
    fetch_origin,
    merge_origin_main,
    pull_origin_main,
    switch_branch,
    switch_main,
    switch_new_branch,
)
from gitclerk.git.branch import (
    parse as parse_branch,
)
from gitclerk.git.commit import add_all, push_head
from gitclerk.git.commit import commit as git_commit
from gitclerk.git.config import clear_active_issue, get_active_issue, set_active_issue
from gitclerk.git.tag import (
    CALVER,
    SEMVER,
    Scheme,
    create_tag,
    detect_scheme,
    fetch_tags,
    next_calver,
    next_semver,
    tags,
)
from gitclerk.github.issue import issue_close_not_planned, issue_create, issue_list, issue_view
from gitclerk.github.label import ensure_type_labels
from gitclerk.github.milestone import (
    milestone_close,
    milestone_create,
    milestone_list,
    milestone_reopen,
    milestone_view,
    parse_epic_body,
)
from gitclerk.github.pr import pr_checks_pass, pr_checks_watch, pr_create, pr_merge, pr_view

TYPE_CHOICE = click.Choice(sorted(TYPES))


class _Group(click.Group):
    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except RuntimeError as e:
            raise click.ClickException(str(e)) from e


def strip_comments(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    collapsed: list[str] = []
    prev_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = blank
    return "\n".join(collapsed).strip()


def _open_editor(hint: str) -> str:
    template = f"# {hint}\n# Lines starting with '#' are ignored.\n\n"
    raw = click.edit(template)
    result = strip_comments(raw or "")
    if not result:
        raise click.Abort()
    return result


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


@click.group(cls=_Group, invoke_without_command=True)
@click.version_option(package_name="git-clerk")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Structured git workflow: conventional commits, trunk-based branches, GitHub PR lifecycle.

    Branch names follow the type/scope convention from the conventional commits specification.
    See https://www.conventionalcommits.org for the full spec.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ── branch ───────────────────────────────────────────────────────────────────


@main.command()
@click.argument("name", metavar="TYPE/scope")
def branch(name: str) -> None:
    """Create a branch from origin/main."""
    try:
        parse_branch(name)
    except ValueError as e:
        raise click.ClickException(str(e))
    fetch_origin()
    switch_new_branch(name)


# ── commit ────────────────────────────────────────────────────────────────────


@main.command()
@click.option("-A", "stage_all", is_flag=True, help="Stage all changes before committing.")
@click.option(
    "-t",
    "--type",
    "type_override",
    default=None,
    metavar="TYPE",
    type=TYPE_CHOICE,
    help="Override the commit type inferred from the branch name.",
)
@click.option(
    "-s",
    "--scope",
    "scope_override",
    default=None,
    help="Override the commit scope inferred from the branch name.",
)
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for commit body.")
@click.argument("description")
@click.argument("body", required=False, default=None)
def commit(
    stage_all: bool,
    type_override: str | None,
    scope_override: str | None,
    edit_body: bool,
    description: str,
    body: str | None,
) -> None:
    """Create a conventional commit from the branch name.

    Type and scope are derived from the branch. By default no body is added —
    pass BODY as a second argument for an inline body, or use -e to open $EDITOR.
    BODY and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    br = current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    header = f"{type_override or type_}({scope_override or scope}): {description}"
    if edit_body:
        body = _open_editor(header)
    if stage_all:
        add_all()
    git_commit(header, body)


# ── pr ───────────────────────────────────────────────────────────────────────


@main.command()
@click.option(
    "-t",
    "--type",
    "type_override",
    default=None,
    metavar="TYPE",
    type=TYPE_CHOICE,
    help="Override the PR title type inferred from the branch name.",
)
@click.option(
    "-s",
    "--scope",
    "scope_override",
    default=None,
    help="Override the PR title scope inferred from the branch name.",
)
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the PR body.")
@click.argument("title")
@click.argument("body", required=False, default=None)
def pr(
    type_override: str | None,
    scope_override: str | None,
    edit_body: bool,
    title: str,
    body: str | None,
) -> None:
    """Push branch, open a PR against main, and watch CI.

    By default no body is added — pass BODY as a second argument for an inline
    body, or use -e to open $EDITOR. BODY and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    br = current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    pr_title = f"{type_override or type_}({scope_override or scope}): {title}"
    if edit_body:
        body = _open_editor(f"{pr_title} ({br})")
    active = get_active_issue()
    if active is not None:
        closes = f"Closes #{active}"
        body = f"{body}\n\n{closes}" if body else closes
    push_head()
    number, url = pr_create(pr_title, body or "")
    click.echo(url)
    pr_checks_watch(number)


# ── ship ─────────────────────────────────────────────────────────────────────


@main.command()
@click.option(
    "-u",
    "--update",
    "update_branch",
    default=None,
    metavar="BRANCH",
    help="After shipping, switch to BRANCH and merge origin/main.",
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def ship(update_branch: str | None, confirmed: bool) -> None:
    """Ship the PR and return to a clean main.

    Squash-merges the current branch's PR, deletes the remote branch, switches
    to local main, pulls, and force-deletes the local branch.
    """
    br = current_branch()
    if br == "main":
        raise click.ClickException("run 'git clerk ship' from the feature branch, not main")
    pr_number, title = pr_view()
    prompt = f'Ship "{title}" (#{pr_number})'
    if update_branch:
        prompt += f", then update {update_branch}"
    if not confirmed:
        click.confirm(prompt, abort=True)
    if not pr_checks_pass(pr_number):
        raise click.ClickException(
            f"PR #{pr_number} has failing or pending checks — run 'git clerk watch' to monitor"
        )
    active = get_active_issue()
    epic_number: int | None = None
    if active is not None:
        issue_data = issue_view(active)
        ms = issue_data.milestone
        if ms is not None:
            epic_number = ms.number
    pr_merge(pr_number)
    switch_main()
    pull_origin_main()
    delete_branch(br)
    if update_branch:
        switch_branch(update_branch)
        merge_origin_main()
    if active is not None:
        clear_active_issue()
    if epic_number is not None:
        m = milestone_view(epic_number)
        if m.open_issues == 0:
            milestone_close(epic_number)
            click.echo(f'Epic #{epic_number} "{m.title}" completed and closed.')


# ── watch ─────────────────────────────────────────────────────────────────────


@main.command()
def watch() -> None:
    """Watch CI checks for the current PR."""
    number, _ = pr_view()
    pr_checks_watch(number)


# ── release ───────────────────────────────────────────────────────────────────


@main.command()
@click.option(
    "--calver",
    "scheme",
    flag_value=CALVER,
    default=None,
    help="Use calendar versioning (vYYYY.MM.N).",
)
@click.option(
    "--semver",
    "scheme",
    flag_value=SEMVER,
    default=None,
    help="Use semantic versioning (vMAJOR.MINOR.PATCH).",
)
@click.option(
    "--bump",
    type=click.Choice(["patch", "minor", "major"]),
    default=None,
    help="SemVer component to increment (ignored for CalVer). Prompted if not provided.",
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def release(scheme: Scheme | None, bump: str | None, confirmed: bool) -> None:
    """Tag origin/main and push the tag.

    Auto-detects CalVer or SemVer from existing tags. Prompts for scheme on
    first use. Pass --calver or --semver to skip the prompt.
    """
    fetch_tags()
    existing = tags()
    if not scheme:
        try:
            scheme = detect_scheme(existing)
        except ValueError as e:
            raise click.ClickException(str(e))
    if not scheme:
        click.echo("No existing tags found. Choose a versioning scheme:")
        click.echo(
            f"  {CALVER}   vYYYY.MM.N         — calendar versioning, counter resets each month"
        )
        click.echo(f"  {SEMVER}   vMAJOR.MINOR.PATCH — semantic versioning")
        raw = click.prompt(
            "Scheme", type=click.Choice([CALVER, SEMVER], case_sensitive=False), show_choices=False
        )
        scheme = CALVER if raw == CALVER else SEMVER
    if scheme == CALVER:
        tag = next_calver(existing, date.today())
    else:
        resolved_bump: str = bump or click.prompt(
            "Bump", type=click.Choice(["patch", "minor", "major"]), show_choices=True
        )
        tag = next_semver(existing, resolved_bump)
    if not confirmed:
        click.confirm(f"Tag and push {tag}", abort=True)
    create_tag(tag)
    click.echo(f"Tagged and pushed {tag}")


# ── board ─────────────────────────────────────────────────────────────────────


@main.group(cls=_Group)
def board() -> None:
    """Manage the project board."""


@board.command(name="setup")
def board_setup() -> None:
    """Create type labels in the repo (idempotent)."""
    ensure_type_labels()
    click.echo("Board labels ready.")


# ── epic ──────────────────────────────────────────────────────────────────────


@main.group(cls=_Group)
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


# ── ticket ────────────────────────────────────────────────────────────────────


@main.group(cls=_Group)
def ticket() -> None:
    """Manage tickets (GitHub Issues)."""


@ticket.command(name="new")
@click.argument("title")
@click.argument("body", required=False, default=None)
@click.option("--type", "type_", default=None, type=TYPE_CHOICE, help="Ticket type label.")
@click.option(
    "--epic",
    "epic_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Epic (milestone) number.",
)
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the ticket body.")
def ticket_new(
    title: str,
    body: str | None,
    type_: str | None,
    epic_number: int | None,
    edit_body: bool,
) -> None:
    """Create a new ticket."""
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    if edit_body:
        body = _open_editor(title)
    number = issue_create(title, body or "", type_, epic_number)
    click.echo(f"Ticket #{number} created.")


@ticket.command(name="list")
@click.option(
    "--epic",
    "epic_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Filter by epic (milestone) number.",
)
def ticket_list(epic_number: int | None) -> None:
    """List open tickets."""
    issues = issue_list(epic_number)
    if not issues:
        click.echo("No open tickets.")
        return
    for i in issues:
        ms = i.milestone
        epic_str = f"epic #{ms.number}" if ms is not None else "no epic"
        click.echo(f"#{i.number:<4} [{i.type:<10}] [{epic_str:<12}] {i.title}")


@ticket.command(name="start")
@click.argument("number", type=int)
def ticket_start(number: int) -> None:
    """Start work on a ticket: create branch and record the active issue."""
    issue_data = issue_view(number)
    ms = issue_data.milestone
    if ms is None:
        raise click.ClickException(f"Ticket #{number} has no epic — assign it to an epic first")
    m = milestone_view(ms.number)
    scope = m.scope
    type_ = issue_data.type
    if not scope:
        raise click.ClickException(
            f"Epic #{ms.number} has no scope — its description must start with 'scope: SCOPE'"
        )
    branch_name = f"{type_}/{scope}"
    fetch_origin()
    switch_new_branch(branch_name)
    set_active_issue(number)
    click.echo(f"On branch '{branch_name}', active issue is #{number}.")


@ticket.command(name="discard")
@click.argument("number", type=int)
def ticket_discard(number: int) -> None:
    """Close a ticket as discarded (not planned)."""
    issue_close_not_planned(number)
    click.echo(f"Ticket #{number} discarded.")
