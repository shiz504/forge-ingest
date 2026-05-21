from pathlib import Path

import pytest

from app.config import Settings
from app.pack import build_manifest, build_repomix_command, pack_bundle


def test_build_repomix_command_handles_include_exclude_globs():
    settings = Settings(ingest_token="a" * 64, repomix_version="1.14.0")
    cmd = build_repomix_command(settings, Path("/tmp/repo"), "markdown", ["**/*.py", "SKILL.md,README.md"], [".git/**"])

    assert "--include" in cmd
    assert cmd[cmd.index("--include") + 1] == "**/*.py,SKILL.md,README.md"
    assert "--ignore" in cmd
    assert cmd[cmd.index("--ignore") + 1] == ".git/**"
    assert "--token-count-encoding" in cmd
    assert "o200k_base" in cmd


def test_size_guard(monkeypatch):
    settings = Settings(ingest_token="a" * 64, max_bytes=5, repomix_version="1.14.0")
    monkeypatch.setattr("app.pack._run_repomix", lambda cmd, settings: b"too large")

    with pytest.raises(ValueError):
        pack_bundle(Path("/tmp/repo"), None, None, settings)


def test_manifest_shape(monkeypatch):
    settings = Settings(ingest_token="a" * 64, repomix_version="1.14.0")
    raw = b'{"files":{"README.md":"hello world","app/main.py":"print(1)"}}'
    monkeypatch.setattr("app.pack._run_repomix", lambda cmd, settings: raw)

    result = build_manifest(Path("/tmp/repo"), "abc123", None, None, settings).payload

    assert result["commit"] == "abc123"
    assert result["total_tokens"] > 0
    assert result["total_bytes"] == len("hello world".encode()) + len("print(1)".encode())
    assert result["files"] == [
        {"path": "README.md", "bytes": 11, "tokens": 2},
        {"path": "app/main.py", "bytes": 8, "tokens": 2},
    ]
