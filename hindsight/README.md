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

2. Ensure **openai-quota-gateway** is running on `infra_shared` (sibling repo). Copy env and set the gateway API key:

```bash
cp hindsight/.env.example hindsight/.env
# Edit hindsight/.env — set HINDSIGHT_API_*_API_KEY to a GATEWAY_API_KEYS value
```

Default models (pool IDs from `openai-quota-gateway/config/pool.json`):

| Role       | Model                      | Gateway path                |
| ---------- | -------------------------- | --------------------------- |
| Text / LLM | `gemma-4-26b-a4b-it`       | `POST /v1/chat/completions` |
| Embedding  | `gemini-embedding-2`       | `POST /v1/embeddings`       |
| Rerank     | `semantic-ranker-fast-004` | `POST /v1/rerank`           |

```bash
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=http://openai-quota-gateway:8000/v1
HINDSIGHT_API_LLM_API_KEY=sk-oqg-xxxx
HINDSIGHT_API_LLM_MODEL=gemma-4-26b-a4b-it

HINDSIGHT_API_EMBEDDINGS_PROVIDER=litellm-sdk
HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_API_BASE=http://openai-quota-gateway:8000/v1
HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_API_KEY=sk-oqg-xxxx
HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_MODEL=openai/gemini-embedding-2
HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_ENCODING_FORMAT=float
HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_OUTPUT_DIMENSIONS=1536

HINDSIGHT_API_RERANKER_PROVIDER=litellm
HINDSIGHT_API_RERANKER_LITELLM_API_BASE=http://openai-quota-gateway:8000/v1
HINDSIGHT_API_RERANKER_LITELLM_API_KEY=sk-oqg-xxxx
HINDSIGHT_API_RERANKER_LITELLM_MODEL=semantic-ranker-fast-004
```

Switching embedding dimensions on a non-empty bank requires re-indexing.

3. Ensure Traefik is up (`make up service=traefik`) so the `*.dss.localhost` hosts resolve over HTTPS.

## Start

```bash
make up service=hindsight
```

## Smoke test

```bash
./hindsight/smoke-test.sh
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
