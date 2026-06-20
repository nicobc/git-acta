import json
import subprocess
import time

from gitclerk.git.branch import get_current_branch
from gitclerk.github import get_repo, gh

_CHECKS_POLL_INTERVAL = 5  # seconds
_CHECKS_QUEUE_TIMEOUT = 90  # seconds to wait for checks to appear


def pr_create(title: str, body: str, base: str = "main") -> tuple[int, str]:
    command_args = [
        "pr",
        "create",
        "--base",
        base,
        "--title",
        title,
        "--body",
        body,
        "--repo",
        get_repo(),
    ]
    pr_url = gh(*command_args, capture=True)
    pr_number = int(pr_url.rstrip("/").split("/")[-1])
    return pr_number, pr_url


def pr_view() -> tuple[int, str]:
    response_json = gh(
        "pr",
        "view",
        get_current_branch(),
        "--repo",
        get_repo(),
        "--json",
        "number,title",
        capture=True,
    )
    pr_data = json.loads(response_json)
    return int(pr_data["number"]), str(pr_data["title"])


def pr_checks_pass(pr_number: int) -> bool:
    try:
        subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--repo", get_repo()],
            check=True,
            text=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as error:
        if "no checks reported" in (error.stderr or ""):
            print(error.stderr.strip())
            return True
        return False


def pr_merge(pr_number: int) -> None:
    gh("pr", "merge", str(pr_number), "--squash", "--delete-branch", "--repo", get_repo())


def pr_checks_watch(pr_number: int) -> None:
    for _ in range(_CHECKS_QUEUE_TIMEOUT // _CHECKS_POLL_INTERVAL):
        response_json = gh(
            "pr",
            "view",
            str(pr_number),
            "--repo",
            get_repo(),
            "--json",
            "statusCheckRollup",
            capture=True,
        )
        if json.loads(response_json).get("statusCheckRollup"):
            break
        try:
            subprocess.run(
                ["gh", "pr", "checks", str(pr_number), "--repo", get_repo()],
                check=True,
                text=True,
                capture_output=True,
            )
            break
        except subprocess.CalledProcessError as error:
            if "no checks reported" in (error.stderr or ""):
                print(error.stderr.strip())
                return
        time.sleep(_CHECKS_POLL_INTERVAL)
    gh("pr", "checks", str(pr_number), "--repo", get_repo(), "--watch")
