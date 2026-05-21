# Secrets

This repository intentionally omits live secrets.

Never commit:

- `.env`
- `INGEST_TOKEN`
- `secrets/forge_deploy_key`
- live ingest URLs containing the token
- reverse-proxy credentials
- tunnel credentials
- cloud provider API keys

Safe to commit:

- `.env.example`
- `secrets/README.md`
- documentation using `{INGEST_TOKEN}` placeholders

If a live token is committed, rotate it immediately and remove the credential
from Git history before publishing the repository more broadly.
