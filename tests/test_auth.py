import hmac

import httpx
import pytest

from app.auth import token_matches
from app.config import get_settings
from app.main import app

TOKEN = "a" * 64


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("INGEST_TOKEN", TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_token_matches_uses_compare_digest(monkeypatch):
    calls = []

    def fake_compare(left, right):
        calls.append((left, right))
        return left == right

    monkeypatch.setattr(hmac, "compare_digest", fake_compare)
    assert token_matches(TOKEN, TOKEN) is True
    assert calls == [(TOKEN, TOKEN)]


def test_bad_length_token_still_compares(monkeypatch):
    calls = []

    def fake_compare(left, right):
        calls.append((left, right))
        return False

    monkeypatch.setattr(hmac, "compare_digest", fake_compare)
    assert token_matches("bad", TOKEN) is False
    assert len(calls[0][0]) == 64


@pytest.mark.asyncio
async def test_bad_token_returns_empty_404_not_401():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/{'b' * 64}/infra/demo")

    assert response.status_code == 404
    assert response.content == b""


@pytest.mark.asyncio
async def test_robots_txt_is_public_and_fetcher_friendly():
    """robots.txt must be reachable without auth and easy for AI fetchers to parse."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/robots.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["cache-control"] == "public, max-age=300"
    assert response.text == "User-agent: *\nAllow: /\nDisallow:\n"


@pytest.mark.asyncio
async def test_head_preflights_are_cheap_after_token_validation():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        bundle = await client.head(f"/{TOKEN}/infra/demo")
        manifest = await client.head(f"/{TOKEN}/infra/demo/manifest")
        bad_token = await client.head(f"/{'b' * 64}/infra/demo")

    assert bundle.status_code == 200
    assert bundle.headers["content-type"].startswith("text/markdown")
    assert bundle.content == b""
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/json")
    assert manifest.content == b""
    assert bad_token.status_code == 404
    assert bad_token.content == b""


@pytest.mark.asyncio
async def test_robots_txt_supports_head():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.head("/robots.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.content == b""
