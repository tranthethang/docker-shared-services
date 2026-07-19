# Crawl4AI Service Configuration

This directory contains the Docker Compose configuration and environment templates for deploying **Crawl4AI** as a shared containerized utility within the infrastructure.

Crawl4AI is an open-source, LLM-friendly web crawler and scraper designed to crawl pages, handle dynamic client-side rendering (using Playwright/Chromium), and extract clean, structured Markdown or HTML results suitable for LLMs.

---

## 🚀 Setup & Installation

### 1. Environment Setup
The service environment variables are managed via the central workspace. You can initialize the configuration file by running:

```bash
# From the repository root
make setup
```

Alternatively, manually copy the template:
```bash
cp crawl4ai/.env.example crawl4ai/.env
```

### 2. Configuration Parameters
Customize the variables in `crawl4ai/.env`:

*   `CRAWL4AI_PORT`: Host port to expose the service (default: `11235`).
*   `CRAWL4AI_API_TOKEN`: API Token for security (default: `crawl4ai102`).
    > [!IMPORTANT]
    > If `CRAWL4AI_API_TOKEN` is left empty, the server will bind to loopback (`127.0.0.1`) only for security and cannot be accessed externally. Setting this token allows the container to bind to `0.0.0.0`, making it accessible via Traefik or external networks.
*   `LLM_PROVIDER`: Default LLM model provider format (e.g. `openai/gpt-4o-mini`).
*   `OPENAI_API_KEY` / `OPENAI_BASE_URL`: Configure these if you route LLM calls through a custom OpenAI-compatible proxy (e.g., LiteLLM, Ollama, Portkey).
*   Resource limits: Memory and CPU limitations (`CRAWL4AI_MEMORY_LIMIT` defaults to `2G` to support Playwright/Chromium requirements).

---

## 🛠️ Operations

To manage the Crawl4AI service, run commands from the repository root:

```bash
# Start Crawl4AI service
make up service=crawl4ai

# View logs
make logs service=crawl4ai

# Stop Crawl4AI service
make down service=crawl4ai
```

---

## 🔌 API Integration

### Service Endpoints
*   **Host URL**: `http://localhost:11235` (mapped port) or `http://crawl4ai.localhost` (if Traefik reverse proxy is active).
*   **Authentication**: Include the token in your HTTP headers using the Bearer scheme:
    ```http
    Authorization: Bearer <CRAWL4AI_API_TOKEN>
    ```

### 1. Health Check (Unauthenticated)
Verify if the container is healthy:
```bash
curl http://localhost:11235/health
```
**Response:**
```json
{
  "status": "ok",
  "timestamp": 1784173605.033,
  "version": "0.9.2"
}
```

### 2. Crawl Endpoint `/crawl` (Authenticated)
Request the crawler to fetch page contents and return Markdown.

#### cURL Example
```bash
curl -X POST http://localhost:11235/crawl \
  -H "Authorization: Bearer crawl4ai102" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://trends.google.com/trending?geo=VN"],
    "crawler_config": {
      "word_count_threshold": 10
    }
  }'
```

#### Python Example
```python
import requests

url = "http://localhost:11235/crawl"
headers = {
    "Authorization": "Bearer crawl4ai102",
    "Content-Type": "application/json"
}
payload = {
    "urls": ["https://example.com"],
    "crawler_config": {
        "word_count_threshold": 5
    }
}

response = requests.post(url, headers=headers, json=payload)
if response.status_code == 200:
    results = response.json().get("results", [])
    if results and results[0].get("success"):
        markdown_data = results[0].get("markdown")
        print("Crawl successful! Content length:", len(markdown_data))
        print(markdown_data[:500])
else:
    print("Error:", response.status_code, response.text)
```
