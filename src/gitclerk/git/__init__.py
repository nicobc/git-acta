import subprocess


def git(*args: str, capture: bool = False) -> str:
    try:
        completed_process = subprocess.run(
            ["git", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
        return completed_process.stdout.strip() if completed_process.stdout else ""
    except FileNotFoundError:
        raise RuntimeError("'git' not found in PATH — install git: https://git-scm.com/install/")
    except subprocess.CalledProcessError:
        raise


def get_remote_url(remote_name: str) -> str:
    return git("remote", "get-url", remote_name, capture=True)
