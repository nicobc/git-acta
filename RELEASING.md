# Releasing

git-acta publishes SemVer-tagged releases to PyPI. Pushing a `v*.*.*` tag fires the publish workflow. Git tags are the source of truth for the version; `pyproject.toml` mirrors the latest tag.

## Workflow

```sh
acta branch fix/export-memory
acta commit -A "stream large exports" -b "The old reader loaded the whole file
into memory and OOM'd on multi-GB exports. Stream it so peak memory stays flat."
acta pr "Stream large exports" -b "Streams exports instead of buffering them.

## Changes
- Replace the buffered reader with a streaming one

## Why
Multi-GB exports OOM'd the previous implementation."
acta ship -y
```

Descriptions are not optional, they keep the repo self-documenting. Commit bodies
are free-form and get squashed away on merge; the PR title and body are what land
on `main` and feed the release notes.

## PR body template

Base PR bodies on this structure. The `## Breaking` section is optional — include
it only for breaking changes:

```markdown
One-line summary of the change.

## Changes
- What changed, point by point

## Why
The motivation and context behind the change.

## Breaking
What breaks and the step users must take. (Omit for non-breaking changes.)
```

## Release script

Once ready to tag a new release, run
```sh
uv run scripts/release.py            # version derived from the commits since the last tag
uv run scripts/release.py --stable   # one-time promotion of a 0.x project to v1.0.0
```
