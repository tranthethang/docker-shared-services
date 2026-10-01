# Hindsight

MCP agent memory service ([vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)).
Traefik-only access — no host ports in the default compose file.

| Endpoint         | URL                                              |
| ---------------- | ------------------------------------------------ |
| API + MCP        | `https://hindsight.dss.localhost`                |
| Control-plane UI | `https://hindsight-ui.dss.localhost`             |
| MCP (per bank)   | `https://hindsight.dss.localhost/mcp/<bank_id>/` |

## Prerequisites

1. Start PgVector and create the database (once):

```bash
make up service=pgvector
docker exec pgvector psql -U postgres -c "CREATE DATABASE hindsight;"
docker exec pgvector psql -U postgres -d hindsight -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

2. Copy env and set LLM credentials:

```bash
cp hindsight/.env.example hindsight/.env
# Edit hindsight/.env — set HINDSIGHT_API_LLM_API_KEY
```

OpenAI-compatible proxies (e.g. 9router) — keep `provider=openai` and point `BASE_URL` at the `/v1` root that serves `/chat/completions`:

```bash
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=https://your-proxy.example.com/v1
HINDSIGHT_API_LLM_API_KEY=sk-xxxx
HINDSIGHT_API_LLM_MODEL=model-name-on-proxy
```

3. Ensure Traefik is up (`make up service=traefik`) so the `*.dss.localhost` hosts resolve over HTTPS.

## Start

```bash
make up service=hindsight
```

## Cursor / Antigravity MCP

Point an HTTP MCP client at a memory bank (trailing slash required):

```json
{
  "mcpServers": {
    "hindsight": {
      "url": "https://hindsight.dss.localhost/mcp/default/"
    }
  }
}
```

Replace `default` with your bank id. If you enable API-key tenant auth later, add an `Authorization: Bearer …` header per upstream MCP docs.
