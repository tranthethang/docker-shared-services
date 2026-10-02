#!/usr/bin/env bash
# Smoke-test Hindsight + openai-quota-gateway wiring (chat / embed / rerank).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1091
  source "${ENV_FILE}"
  set +a
fi

GW_BASE="${GW_BASE:-https://openai.dss.localhost}"
HS_BASE="${HS_BASE:-${HINDSIGHT_PUBLIC_URL:-https://hindsight.dss.localhost}}"
GW_KEY="${GW_KEY:-${HINDSIGHT_API_LLM_API_KEY:-}}"
CHAT_MODEL="${CHAT_MODEL:-${HINDSIGHT_API_LLM_MODEL:-gemma-4-26b-a4b-it}}"
EMBED_MODEL_RAW="${EMBED_MODEL:-${HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_MODEL:-openai/gemini-embedding-2}}"
case "${EMBED_MODEL_RAW}" in
  */*) EMBED_MODEL="${EMBED_MODEL_RAW#*/}" ;;
  *) EMBED_MODEL="${EMBED_MODEL_RAW}" ;;
esac
RERANK_MODEL="${RERANK_MODEL:-${HINDSIGHT_API_RERANKER_LITELLM_MODEL:-semantic-ranker-fast-004}}"
BANK_ID="${BANK_ID:-smoke-oqg}"
CURL_OPTS=(-skS --connect-timeout 5 --max-time 120)

pass=0
fail=0

ok() {
  echo "  PASS  $1"
  pass=$((pass + 1))
}

bad() {
  echo "  FAIL  $1"
  echo "        $2"
  fail=$((fail + 1))
}

need_key() {
  if [[ -z "${GW_KEY}" ]]; then
    echo "ERROR: set HINDSIGHT_API_LLM_API_KEY in ${ENV_FILE} or GW_KEY=..."
    exit 1
  fi
}

json_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print($1)" 2>/dev/null || true
}

echo "== Hindsight / openai-quota-gateway smoke =="
echo "  GW_BASE=${GW_BASE}"
echo "  HS_BASE=${HS_BASE}"
echo "  chat=${CHAT_MODEL}  embed=${EMBED_MODEL}  rerank=${RERANK_MODEL}"
echo

need_key

echo "-- 1) Gateway health"
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/oqg-health.json -w "%{http_code}" "${GW_BASE}/health"); then
  if [[ "${code}" == "200" ]]; then
    ok "GET ${GW_BASE}/health → ${code}"
  else
    bad "GET ${GW_BASE}/health → ${code}" "$(head -c 200 /tmp/oqg-health.json)"
  fi
else
  bad "GET ${GW_BASE}/health" "curl failed"
fi

echo "-- 2) Gateway models include configured pools"
if curl "${CURL_OPTS[@]}" -o /tmp/oqg-models.json \
  -H "Authorization: Bearer ${GW_KEY}" \
  "${GW_BASE}/v1/models"; then
  missing=""
  for m in "${CHAT_MODEL}" "${EMBED_MODEL}" "${RERANK_MODEL}"; do
    if ! python3 -c "import json,sys; ids={x.get('id') for x in json.load(open('/tmp/oqg-models.json')).get('data',[])}; sys.exit(0 if '${m}' in ids else 1)"; then
      missing="${missing} ${m}"
    fi
  done
  if [[ -z "${missing}" ]]; then
    ok "catalog contains ${CHAT_MODEL}, ${EMBED_MODEL}, ${RERANK_MODEL}"
  else
    bad "catalog missing models:${missing}" "see /tmp/oqg-models.json"
  fi
else
  bad "GET /v1/models" "curl failed"
fi

echo "-- 3) Gateway chat (${CHAT_MODEL})"
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/oqg-chat.json -w "%{http_code}" \
  -X POST "${GW_BASE}/v1/chat/completions" \
  -H "Authorization: Bearer ${GW_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${CHAT_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: ok\"}],\"max_tokens\":16}"); then
  if [[ "${code}" == "200" ]]; then
    content=$(python3 -c "import json; d=json.load(open('/tmp/oqg-chat.json')); print(d['choices'][0]['message']['content'][:80])" 2>/dev/null || echo "")
    ok "POST /v1/chat/completions → ${code} (${content})"
  else
    bad "POST /v1/chat/completions → ${code}" "$(head -c 300 /tmp/oqg-chat.json)"
  fi
else
  bad "POST /v1/chat/completions" "curl failed"
fi

echo "-- 4) Gateway embeddings (${EMBED_MODEL})"
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/oqg-embed.json -w "%{http_code}" \
  -X POST "${GW_BASE}/v1/embeddings" \
  -H "Authorization: Bearer ${GW_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${EMBED_MODEL}\",\"input\":\"hindsight smoke embedding\"}"); then
  dim=$(python3 -c "import json; d=json.load(open('/tmp/oqg-embed.json')); print(len(d['data'][0]['embedding']))" 2>/dev/null || echo "0")
  if [[ "${code}" == "200" && "${dim}" != "0" ]]; then
    ok "POST /v1/embeddings → ${code} (dim=${dim})"
  else
    bad "POST /v1/embeddings → ${code}" "$(head -c 300 /tmp/oqg-embed.json)"
  fi
else
  bad "POST /v1/embeddings" "curl failed"
fi

echo "-- 5) Gateway rerank (${RERANK_MODEL})"
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/oqg-rerank.json -w "%{http_code}" \
  -X POST "${GW_BASE}/v1/rerank" \
  -H "Authorization: Bearer ${GW_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${RERANK_MODEL}\",\"query\":\"memory bank\",\"documents\":[\"unrelated text\",\"agent memory service\"],\"top_n\":2}"); then
  n=$(python3 -c "import json; d=json.load(open('/tmp/oqg-rerank.json')); print(len(d.get('results') or d.get('data') or []))" 2>/dev/null || echo "0")
  if [[ "${code}" == "200" && "${n}" != "0" ]]; then
    ok "POST /v1/rerank → ${code} (results=${n})"
  else
    bad "POST /v1/rerank → ${code}" "$(head -c 300 /tmp/oqg-rerank.json)"
  fi
else
  bad "POST /v1/rerank" "curl failed"
fi

echo "-- 6) Hindsight health"
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/hs-health.json -w "%{http_code}" "${HS_BASE}/health/ready"); then
  if [[ "${code}" == "200" ]]; then
    ok "GET ${HS_BASE}/health/ready → ${code}"
  else
    bad "GET ${HS_BASE}/health/ready → ${code}" "$(head -c 200 /tmp/hs-health.json)"
  fi
else
  bad "GET ${HS_BASE}/health/ready" "curl failed"
fi

echo "-- 7) Hindsight retain + recall (${BANK_ID})"
retain_body=$(cat <<EOF
{"items":[{"content":"Smoke test fact: openai-quota-gateway powers Hindsight LLM, embeddings, and rerank. Timestamp $(date -u +%Y-%m-%dT%H:%M:%SZ)."}],"async":false}
EOF
)
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/hs-retain.json -w "%{http_code}" \
  -X POST "${HS_BASE}/v1/default/banks/${BANK_ID}/memories" \
  -H "Content-Type: application/json" \
  -d "${retain_body}"); then
  if [[ "${code}" =~ ^(200|201|202)$ ]]; then
    ok "POST retain → ${code}"
  else
    bad "POST retain → ${code}" "$(head -c 300 /tmp/hs-retain.json)"
  fi
else
  bad "POST retain" "curl failed"
fi

# Brief wait for indexing when retain was accepted.
sleep 3

recall_body='{"query":"What powers Hindsight embeddings?","budget":"low"}'
if code=$(curl "${CURL_OPTS[@]}" -o /tmp/hs-recall.json -w "%{http_code}" \
  -X POST "${HS_BASE}/v1/default/banks/${BANK_ID}/memories/recall" \
  -H "Content-Type: application/json" \
  -d "${recall_body}"); then
  if [[ "${code}" =~ ^(200|201)$ ]]; then
    ok "POST recall → ${code}"
  else
    bad "POST recall → ${code}" "$(head -c 300 /tmp/hs-recall.json)"
  fi
else
  bad "POST recall" "curl failed"
fi

echo
echo "== Summary: ${pass} passed, ${fail} failed =="
if [[ "${fail}" -gt 0 ]]; then
  exit 1
fi
exit 0
