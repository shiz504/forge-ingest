# Operations

## Health Check

```bash
curl -fsS http://127.0.0.1:8092/healthz
```

Expected response:

```text
ok
```

## Restart

```bash
docker compose up -d --build
docker compose logs -f --tail=100
```

The container uses `restart: unless-stopped`.

## Token Rotation

```bash
openssl rand -hex 32
$EDITOR .env
docker compose up -d
```

Old capability URLs stop working as soon as the container restarts with the new
token.

## Add Repository Access

1. Copy `secrets/forge_deploy_key.pub`.
2. Add it as a read-only deploy key on the target forge repository.
3. No service restart is required.

## Troubleshooting

- A bad or missing token returns an empty `404`.
- If clone fails, verify the deploy key is present on the target repository.
- If host verification fails, refresh `secrets/forge_known_hosts` only after
  confirming the forge host key change is legitimate.
- If cloud clients cannot fetch, verify the HTTPS edge and reverse proxy before
  changing application code.
