# Releasing

git-clerk publishes SemVer-tagged releases to PyPI. Pushing a `v*.*.*` tag fires the publish workflow. Git tags are the source of truth for the version; `pyproject.toml` mirrors the latest tag.

## Workflow

```sh
git clerk branch type/scope
git clerk commit -A "description" "Context for why."
git clerk pr "PR title" "What changed and why."
git clerk ship -y
```

Descriptions are not optional, they keep the repo self-documenting.

## Release script

Once ready to tag a new release, run
```sh
uv run scripts/release.py patch   # or: minor, major
```
