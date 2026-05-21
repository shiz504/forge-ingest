# Troubleshooting

## Health Check Fails

```bash
docker compose ps
docker compose logs --tail=100 forge-ingest
curl -i http://127.0.0.1:8092/healthz
```

Check that `.env` exists and contains a 64-character hex `INGEST_TOKEN`.

## Repository Returns 404

`forge-ingest` intentionally returns empty `404` responses for bad tokens,
clone failures, and inaccessible repositories.

Check:

- the URL contains the correct token
- `owner` and `repo` match the forge path
- the deploy key is attached to the target repository as read-only
- `INGEST_FORGE_HOST` and `INGEST_FORGE_PORT` point at the reachable SSH endpoint
- `secrets/forge_known_hosts` contains the pinned SSH host key

## Bundle Too Large

Use the manifest endpoint first:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo/manifest" | jq .
```

Then retry with a narrow include:

```bash
curl -fsS "https://ingest.example.net/${INGEST_TOKEN}/org/repo?include=README.md,src/**"
```

## Cloud Client Cannot Fetch

Check the HTTPS edge first:

```bash
curl -sSI https://ingest.example.net/robots.txt
curl -sS https://ingest.example.net/robots.txt
```

Expected:

```text
User-agent: *
Allow: /
Disallow:
```

If fetchers preflight with `HEAD`, both bundle and manifest routes should return
`200` for a valid token without running a full clone.

## Token Exposure

If a live ingest URL is pasted into an untrusted system:

1. Generate a new token.
2. Update `.env`.
3. Restart the container.
4. Replace any saved URL palettes.
