# forge-ingest URL palette template

This is a safe template for constructing read-only ingest URLs.

Do not commit a live `INGEST_TOKEN` here. Store live URL palettes in a
credential vault.

## Pattern

```text
https://ingest.example.net/{INGEST_TOKEN}/{owner}/{repo}
https://ingest.example.net/{INGEST_TOKEN}/{owner}/{repo}/manifest
```

## Prompt

```text
Read this repository context and confirm you understand it. Treat it as
read-only reference material for this chat.

https://ingest.example.net/{INGEST_TOKEN}/{owner}/{repo}?include=README.md,app/**
```

## Safety

- Treat every URL containing `INGEST_TOKEN` as a credential.
- Prefer `forge-mcp` for cloud AI clients so the internal token is never exposed.
- Rotate `INGEST_TOKEN` if a live URL is pasted into an untrusted system.
