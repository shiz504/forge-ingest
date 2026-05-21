import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Settings


class PackError(RuntimeError):
    pass


@dataclass
class BundleResult:
    content: bytes
    tokens: int


@dataclass
class ManifestResult:
    payload: dict


def _split_globs(values: list[str] | None) -> str | None:
    if not values:
        return None
    globs: list[str] = []
    for value in values:
        globs.extend(part.strip() for part in value.split(",") if part.strip())
    return ",".join(globs) if globs else None


def build_repomix_command(settings: Settings, repo_path: Path, style: str, includes: list[str] | None, excludes: list[str] | None) -> list[str]:
    cmd = [
        "npx",
        "-y",
        f"repomix@{settings.repomix_version}",
        str(repo_path),
        "--stdout",
        "--style",
        style,
        "--token-count-encoding",
        "o200k_base",
    ]
    include_arg = _split_globs(includes)
    exclude_arg = _split_globs(excludes)
    if include_arg:
        cmd += ["--include", include_arg]
    if exclude_arg:
        cmd += ["--ignore", exclude_arg]
    return cmd


def _run_repomix(cmd: list[str], settings: Settings) -> bytes:
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True, timeout=settings.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("repomix timed out") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace")
        raise PackError(stderr.strip() or "repomix failed") from exc
    return proc.stdout


def estimate_tokens(text: str) -> int:
    return max(1, len(text.encode("utf-8")) // 4) if text else 0


def pack_bundle(repo_path: Path, includes: list[str] | None, excludes: list[str] | None, settings: Settings) -> BundleResult:
    output = _run_repomix(build_repomix_command(settings, repo_path, "markdown", includes, excludes), settings)
    if len(output) > settings.max_bytes:
        raise ValueError("bundle exceeds size limit")
    return BundleResult(content=output, tokens=estimate_tokens(output.decode("utf-8", errors="ignore")))


def build_manifest(repo_path: Path, commit: str, includes: list[str] | None, excludes: list[str] | None, settings: Settings) -> ManifestResult:
    cmd = build_repomix_command(settings, repo_path, "json", includes, excludes)
    raw = _run_repomix(cmd, settings)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PackError("repomix did not return valid JSON") from exc

    files_obj = data.get("files", {})
    if isinstance(files_obj, list):
        iterator = ((item.get("path", ""), item.get("content", ""), item) for item in files_obj if isinstance(item, dict))
    elif isinstance(files_obj, dict):
        iterator = ((path, content, {}) for path, content in files_obj.items())
    else:
        iterator = iter(())

    files = []
    total_bytes = 0
    total_tokens = 0
    for path, content, meta in iterator:
        if not path:
            continue
        content_text = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
        byte_count = len(content_text.encode("utf-8"))
        token_count = int(meta.get("tokens") or meta.get("tokenCount") or estimate_tokens(content_text))
        files.append({"path": path, "bytes": byte_count, "tokens": token_count})
        total_bytes += byte_count
        total_tokens += token_count

    files.sort(key=lambda item: item["path"])
    return ManifestResult({"files": files, "total_bytes": total_bytes, "total_tokens": total_tokens, "commit": commit})
