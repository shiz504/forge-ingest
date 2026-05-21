import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Settings

SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class GitError(RuntimeError):
    pass


@dataclass
class CloneResult:
    path: Path
    commit: str


def validate_slug(value: str, label: str) -> str:
    if not SLUG_RE.fullmatch(value) or value in {".", ".."}:
        raise GitError(f"invalid {label}")
    return value


def git_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = (
        f"ssh -i {settings.deploy_key_path} "
        "-o StrictHostKeyChecking=accept-new "
        f"-o UserKnownHostsFile={settings.known_hosts_path} "
        f"-p {settings.forge_port}"
    )
    return env


def clone_repo(owner: str, repo: str, ref: str | None, settings: Settings) -> CloneResult:
    owner = validate_slug(owner, "owner")
    repo = validate_slug(repo, "repo")
    if ref is not None and not re.fullmatch(r"[A-Za-z0-9_./-]{1,160}", ref):
        raise GitError("invalid ref")

    tmp = Path(tempfile.mkdtemp(prefix="forge-ingest-", dir="/tmp"))
    dest = tmp / "repo"
    url = f"ssh://git@{settings.forge_host}:{settings.forge_port}/{owner}/{repo}.git"
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [url, str(dest)]

    try:
        subprocess.run(cmd, env=git_env(settings), text=True, capture_output=True, check=True, timeout=settings.timeout_seconds)
        commit = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        return CloneResult(path=dest, commit=commit)
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise TimeoutError("git clone timed out") from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise GitError(exc.stderr.strip() or "git clone failed") from exc


def cleanup_clone(path: Path) -> None:
    shutil.rmtree(path.parent, ignore_errors=True)
