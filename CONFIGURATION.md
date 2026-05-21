# Configuration

`forge-ingest` is configured through environment variables and Docker secrets.

## Required Runtime Files

```text
.env
secrets/forge_deploy_key
secrets/forge_known_hosts
```

These files are intentionally not committed. Use `.env.example` and
`deploy/generate-deploy-key.sh` to recreate them.

## Environment

```env
INGEST_TOKEN=
INGEST_MAX_BYTES=5242880
INGEST_TIMEOUT_SECONDS=60
INGEST_FORGE_HOST=forge
INGEST_FORGE_PORT=22
REPOMIX_VERSION=1.14.0
```

`INGEST_TOKEN` is a capability token. Possession of the token grants read access
to any repository that trusts the mounted deploy key.

## Forge Access

The service clones with SSH:

```text
ssh://git@{INGEST_FORGE_HOST}:{INGEST_FORGE_PORT}/{owner}/{repo}.git
```

The deploy key must be added to every allowed repository as read-only.

## Public Edge

Put this service behind HTTPS before using it from cloud clients. Keep access
logs disabled or redacted for token-bearing paths.

For multi-client use, pair it with `forge-mcp` so AI clients authenticate with
OAuth and never see the internal ingest token.
