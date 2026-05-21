import asyncio
import json
import logging
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from .auth import empty_404, require_token
from .config import Settings, get_settings
from .git_ops import GitError, cleanup_clone, clone_repo
from .logging_filter import TokenRedactionFilter, redact_path
from .pack import PackError, build_manifest, pack_bundle

logger = logging.getLogger("forge_ingest")
handler = logging.StreamHandler()
handler.addFilter(TokenRedactionFilter())
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers[:] = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False

app = FastAPI(title="forge-ingest", docs_url=None, redoc_url=None, openapi_url=None)


def _json_log(**fields: object) -> None:
    logger.info(json.dumps(fields, separators=(",", ":"), sort_keys=True))


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        _json_log(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            method=request.method,
            path=redact_path(str(request.url.path)),
            status=status,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            owner=getattr(request.state, "owner", None),
            repo=getattr(request.state, "repo", None),
            ref=getattr(request.state, "ref", None),
            bundle_bytes=getattr(request.state, "bundle_bytes", None),
            bundle_tokens=getattr(request.state, "bundle_tokens", None),
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return empty_404()
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.api_route("/healthz", methods=["GET", "HEAD"])
async def healthz() -> Response:
    return Response(status_code=200, content=b"ok\n", media_type="text/plain")


@app.api_route("/robots.txt", methods=["GET", "HEAD"], include_in_schema=False)
async def robots():
    """
    Fully permissive robots.txt. The security model on this subdomain is
    capability-URL secrecy (32-byte tokens), not user-agent filtering.
    Crawlers cannot enumerate token paths, so allow/deny by UA is theatre.

    Explicit bot blocks were removed because some third-party fetchers
    (e.g. ChatGPT web tool, Claude web fetch) refuse to retrieve any URL
    on a host whose robots.txt mentions their bot family in a Disallow
    block, even when the wildcard rule would allow the user-initiated UA.
    """
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow:\n"
    )
    return PlainTextResponse(
        body,
        headers={"Cache-Control": "public, max-age=300"},
    )


def _clone_and_pack(owner: str, repo: str, ref: str | None, include: list[str] | None, exclude: list[str] | None, settings: Settings):
    clone = clone_repo(owner, repo, ref, settings)
    try:
        return pack_bundle(clone.path, include, exclude, settings)
    finally:
        cleanup_clone(clone.path)


def _clone_and_manifest(owner: str, repo: str, ref: str | None, include: list[str] | None, exclude: list[str] | None, settings: Settings):
    clone = clone_repo(owner, repo, ref, settings)
    try:
        return build_manifest(clone.path, clone.commit, include, exclude, settings)
    finally:
        cleanup_clone(clone.path)


@app.api_route("/{token}/{owner}/{repo}", methods=["GET", "HEAD"])
async def ingest_repo(
    request: Request,
    token: str,
    owner: str,
    repo: str,
    ref: str | None = None,
    include: Annotated[list[str] | None, Query()] = None,
    exclude: Annotated[list[str] | None, Query()] = None,
    settings: Settings = Depends(get_settings),
):
    require_token(token, settings.ingest_token)
    # HEAD short-circuit: validate the token, then return a cheap synthetic
    # response without running the clone+pack. Polite fetchers (ChatGPT,
    # Claude) preflight with HEAD before GET; without this, the preflight
    # either 405s (route not bound) or triggers a full git clone.
    if request.method == "HEAD":
        return Response(status_code=200, media_type="text/markdown; charset=utf-8")
    request.state.owner = owner
    request.state.repo = repo
    request.state.ref = ref
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_clone_and_pack, owner, repo, ref, include, exclude, settings),
            timeout=settings.timeout_seconds + 5,
        )
    except TimeoutError:
        return JSONResponse(status_code=504, content={"detail": "request timed out"})
    except ValueError:
        return JSONResponse(
            status_code=413,
            content={"detail": "bundle exceeds size limit", "suggestion": "Use the manifest endpoint and retry with a tighter include glob."},
        )
    except (GitError, PackError):
        raise HTTPException(status_code=404, detail=None)

    request.state.bundle_bytes = len(result.content)
    request.state.bundle_tokens = result.tokens
    headers = {"Content-Disposition": f'inline; filename="{owner}-{repo}.md"'}
    return Response(content=result.content, media_type="text/markdown; charset=utf-8", headers=headers)


@app.api_route("/{token}/{owner}/{repo}/manifest", methods=["GET", "HEAD"])
async def ingest_manifest(
    request: Request,
    token: str,
    owner: str,
    repo: str,
    ref: str | None = None,
    include: Annotated[list[str] | None, Query()] = None,
    exclude: Annotated[list[str] | None, Query()] = None,
    settings: Settings = Depends(get_settings),
):
    require_token(token, settings.ingest_token)
    if request.method == "HEAD":
        return Response(status_code=200, media_type="application/json")
    request.state.owner = owner
    request.state.repo = repo
    request.state.ref = ref
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_clone_and_manifest, owner, repo, ref, include, exclude, settings),
            timeout=settings.timeout_seconds + 5,
        )
    except TimeoutError:
        return JSONResponse(status_code=504, content={"detail": "request timed out"})
    except (GitError, PackError):
        raise HTTPException(status_code=404, detail=None)

    request.state.bundle_bytes = result.payload.get("total_bytes")
    request.state.bundle_tokens = result.payload.get("total_tokens")
    return JSONResponse(content=result.payload)
