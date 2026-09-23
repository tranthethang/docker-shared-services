#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

get_unix_nano() {
  if date +%s%N 2>/dev/null | grep -qv 'N'; then
    date +%s%N
  else
    python3 -c "import time; print(int(time.time() * 1e9))"
  fi
}

echo "Testing OTel logs-first stack..."

echo -n "Checking OTel Collector OTLP HTTP (4318)... "
if curl -sf -o /dev/null -w "%{http_code}" http://localhost:4318 | grep -qE '^[0-9]+$'; then
  echo -e "${GREEN}UP${NC}"
else
  # Endpoint may return 404/405 on GET; connection success is enough.
  if curl -s -o /dev/null --connect-timeout 2 http://localhost:4318; then
    echo -e "${GREEN}UP${NC}"
  else
    echo -e "${RED}DOWN${NC}"
  fi
fi

echo -n "Checking Loki ready (3100)... "
if curl -sf http://localhost:3100/ready >/dev/null; then
  echo -e "${GREEN}UP${NC}"
else
  echo -e "${RED}DOWN${NC}"
fi

echo -n "Checking Grafana health (3001)... "
if curl -sf http://localhost:3001/api/health >/dev/null; then
  echo -e "${GREEN}UP${NC}"
else
  echo -e "${RED}DOWN${NC}"
fi

echo "------------------------------------"

TS="$(get_unix_nano)"
echo "Sending test OTLP log to Collector (4318)..."
curl -s -X POST "http://localhost:4318/v1/logs" \
  -H "Content-Type: application/json" \
  -d "{
  \"resourceLogs\": [{
    \"resource\": {
      \"attributes\": [{
        \"key\": \"service.name\",
        \"value\": { \"stringValue\": \"test-script\" }
      }]
    },
    \"scopeLogs\": [{
      \"logRecords\": [{
        \"timeUnixNano\": \"${TS}\",
        \"severity\": { \"stringValue\": \"hello from otel test-script\" },
        \"attributes\": [{
          \"key\": \"test.key\",
          \"value\": { \"stringValue\": \"test-value\" }
        }]
      }]
    }]
  }]
}"

echo ""
echo -e "${GREEN}Log sent.${NC} Explore in Grafana: https://grafana.dss.localhost"
echo "  LogQL hint: {service_name=\"test-script\"} or {container=~\".+\"}"
echo ""
echo "Trace/metric OTLP is accepted by the collector but dropped (nop) until Tempo/Prometheus are added."
