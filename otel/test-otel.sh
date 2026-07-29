#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Testing OpenTelemetry Setup..."

# Helper: get current time in nanoseconds (compatible with both Linux and macOS)
get_unix_nano() {
  if date +%s%N | grep -qv 'N'; then
    # Linux: date supports %N natively
    date +%s%N
  else
    # macOS fallback: use python3
    python3 -c "import time; print(int(time.time() * 1e9))"
  fi
}

# 1. Check if services are up
echo -n "Checking OTel Collector (4318)... "
if curl -s http://localhost:4318 > /dev/null; then
    echo -e "${GREEN}UP${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

echo -n "Checking Jaeger UI (16686)... "
if curl -s http://localhost:16686 > /dev/null; then
    echo -e "${GREEN}UP${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

echo -n "Checking Prometheus (9090)... "
if curl -s http://localhost:9090 > /dev/null; then
    echo -e "${GREEN}UP${NC}"
else
    echo -e "${RED}DOWN${NC}"
fi

echo "------------------------------------"

# 2. Send a test trace
echo "Sending test trace to OTLP HTTP (4318)..."
curl -s -X POST http://localhost:4318/v1/traces \
-H "Content-Type: application/json" \
-d '{
 "resourceSpans": [
   {
     "resource": {
       "attributes": [
         {
           "key": "service.name",
           "value": {
             "stringValue": "test-script"
           }
         }
       ]
     },
     "scopeSpans": [
       {
         "spans": [
           {
             "traceId": "5B8EFFF798038103D269B633813FC60C",
             "spanId": "EEE19B7EC3C1B174",
             "name": "test-span",
             "kind": 1,
             "startTimeUnixNano": "'$(get_unix_nano)'",
             "endTimeUnixNano": "'$(($(get_unix_nano) + 1000000))'",
             "attributes": [
               {
                 "key": "test.key",
                 "value": {
                   "stringValue": "test-value"
                 }
               }
             ]
           }
         ]
       }
     ]
   }
 ]
}'

echo -e "\n${GREEN}Trace sent! Check Jaeger UI: http://jaeger.localhost${NC}"

# 3. Send a test metric
echo "Sending test metric to OTLP HTTP (4318)..."
curl -s -X POST http://localhost:4318/v1/metrics \
-H "Content-Type: application/json" \
-d '{
 "resourceMetrics": [
   {
     "resource": {
       "attributes": [
         {
           "key": "service.name",
           "value": {
             "stringValue": "test-script"
           }
         }
       ]
     },
     "scopeMetrics": [
       {
         "metrics": [
           {
             "name": "test_counter",
             "description": "A test counter",
             "sum": {
               "dataPoints": [
                 {
                   "asInt": "1",
                   "startTimeUnixNano": "'$(get_unix_nano)'",
                   "timeUnixNano": "'$(get_unix_nano)'"
                 }
               ],
               "aggregationTemporality": 1,
               "isMonotonic": true
             }
           }
         ]
       }
     ]
   }
 ]
}'

echo -e "\n${GREEN}Metric sent! Check Prometheus: http://prometheus.localhost${NC}"
