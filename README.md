# forge-ingest

Read-only Git forge repository packer for AI context.

`forge-ingest` turns private Git repositories into model-ready Markdown bundles
and lightweight manifests. It is designed for workflows where an AI assistant
needs fresh source context without direct Git credentials, write access, or a
manual copy-paste workflow.

Built by INTRAC.NET as part of the local-forge-to-universal-AI-context stack:

https://intrac.net/articles/local-git-universal-ai-context

## What It Does

- Clones a requested repository over SSH.
- Packs the repository into Markdown with Repomix.
- Returns a manifest with file sizes, token estimates, and commit SHA.
- Supports include/exclude glob filters.
- Uses a capability token in the URL path.
- Redacts token-like paths from application logs.
- Deletes temporary clones after each request.

## Architecture

```text
AI client or MCP wrapper
  |
  v
HTTPS edge / reverse proxy
  |
  v
forge-ingest container
  |
  v
Git forge over SSH
```

`forge-ingest` has no write endpoints, no sessions, and no database. Each
request clones fresh, packs the requested ref, returns the result, and removes
the temporary clone.

## API

Health:

```bash
curl -fsS http://127.0.0.1:8092/healthz
```

Packed repository context:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo"
```

Manifest:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo/manifest" | jq .
```

Scoped context:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo?include=README.md,src/**"
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo?exclude=.github/**,tests/**"
```

Ref selection:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo?ref=main"
```

## Configuration

Copy `.env.example` to `.env`:

```env
INGEST_TOKEN=
INGEST_MAX_BYTES=5242880
INGEST_TIMEOUT_SECONDS=60
INGEST_FORGE_HOST=forge
INGEST_FORGE_PORT=22
REPOMIX_VERSION=1.14.0
```

Generate a token:

```bash
openssl rand -hex 32
```

Generate an SSH deploy key and host pinning data:

```bash
./deploy/generate-deploy-key.sh
```

Add the generated public key to each repository that `forge-ingest` may read.
Use read-only deploy keys.

## Run

```bash
docker compose up -d --build
curl -fsS http://127.0.0.1:8092/healthz
```

## Security Model

The URL path token is a capability secret. Anyone with the token can request
any repository reachable by the configured deploy key.

Recommended boundaries:

- Use a dedicated read-only deploy key.
- Scope that key only to repositories intended for AI context.
- Keep access logs disabled or redacted at the reverse proxy.
- Rotate `INGEST_TOKEN` if a live URL is pasted into an untrusted system.
- Put OAuth or another authenticated gateway in front for multi-client use.

For cloud AI clients, pair this service with `forge-mcp` so clients authenticate
with OAuth and never see the internal ingest token.

## License

MIT
