# Network Segmentation Architecture

## Overview

Docker Shared Services uses a three-tier network segmentation model that isolates external ingress traffic from internal application logic and database persistence:

1. **`traefik_proxy`** (`10.0.0.0/16`): The public-facing edge network. Connects Traefik reverse proxy to services that expose Web UIs or HTTP APIs routed by Traefik (`https://*.dss.localhost`).
1. **`backend_net`** (`10.1.0.0/16`): The internal application and orchestration network. Interconnects application logic containers, background workers, CI/CD agents, and data service clients.
1. **`data_net`** (`10.2.0.0/16`): The isolated data storage and persistence network. Hosts relational databases, document databases, in-memory caches, message brokers, and vector stores. Traefik does NOT connect to `data_net`.

## Network Topology & Addressing

| Network Name    | Subnet        | Gateway    | Purpose                                           | Direct Traefik Ingress |
| --------------- | ------------- | ---------- | ------------------------------------------------- | ---------------------- |
| `traefik_proxy` | `10.0.0.0/16` | `10.0.0.1` | Traefik edge routing and HTTP(S) entrypoint       | Yes                    |
| `backend_net`   | `10.1.0.0/16` | `10.1.0.1` | Inter-service application communication & workers | No                     |
| `data_net`      | `10.2.0.0/16` | `10.2.0.1` | Database, cache, and storage persistence tier     | No                     |

## Service-to-Network Mapping Matrix

Below is the mapping for all container services in the repository:

| Service / Container     | Primary Role              | `traefik_proxy` | `backend_net` | `data_net` | Notes                                         |
| ----------------------- | ------------------------- | :-------------: | :-----------: | :--------: | --------------------------------------------- |
| **traefik**             | Reverse Proxy             |       ✅        |      ❌       |     ❌     | Traefik ingress only                          |
| **dockge**              | Docker Stack UI           |       ✅        |      ❌       |     ❌     | Traefik Web UI                                |
| **dozzle**              | Container Log UI          |       ✅        |      ❌       |     ❌     | Traefik Web UI                                |
| **mermaid-live-editor** | Diagram Editor UI         |       ✅        |      ❌       |     ❌     | Traefik Web UI                                |
| **portainer**           | Container Management UI   |       ✅        |      ❌       |     ❌     | Traefik Web UI                                |
| **act_runner**          | Gitea Actions Runner      |       ❌        |      ✅       |     ❌     | Interacts with Gitea on `backend_net`         |
| **adminer**             | Database Web UI           |       ✅        |      ✅       |     ✅     | Traefik Web UI + connects to DBs              |
| **appsmith**            | Low-Code App Platform     |       ✅        |      ✅       |     ✅     | Traefik Web UI + queries data & APIs          |
| **bugsink**             | Error Tracking            |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL backend           |
| **centrifugo**          | Realtime Messaging Server |       ❌        |      ✅       |     ❌     | Internal messaging API / localhost:8010       |
| **chromadb**            | Vector DB                 |       ✅        |      ✅       |     ✅     | Traefik HTTP API + backend access + storage   |
| **chromadb-admin**      | ChromaDB Admin UI         |       ✅        |      ✅       |     ❌     | Traefik Web UI + ChromaDB backend             |
| **concourse**           | CI/CD Platform            |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL backend           |
| **crawl4ai**            | Web Crawler API/UI        |       ✅        |      ✅       |     ❌     | Traefik Web UI/API + internal workers         |
| **garage**              | Distributed S3 Storage    |       ✅        |      ✅       |     ❌     | Traefik S3 / Admin + backend S3 clients       |
| **gitea**               | Git Service               |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL backend           |
| **gotenberg**           | PDF Conversion Service    |       ❌        |      ✅       |     ❌     | Internal HTTP API / localhost:3030            |
| **hasura**              | GraphQL Engine            |       ✅        |      ✅       |     ❌     | Traefik GraphQL API/Console + PostgreSQL      |
| **hindsight**           | MCP Memory Service        |       ✅        |      ✅       |     ❌     | Traefik Web UI/API + PgVector backend         |
| **inngest**             | Background Job Platform   |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL/Redis             |
| **jenkins**             | Automation Server         |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL backend           |
| **kafka** (broker)      | Event Streaming Broker    |       ❌        |      ✅       |     ✅     | Broker persistence + backend consumers        |
| **kafka-ui**            | Kafka Management UI       |       ✅        |      ✅       |     ❌     | Traefik Web UI + Kafka broker                 |
| **litellm**             | OpenAI-compatible proxy   |       ✅        |      ✅       |     ❌     | Traefik UI/API + Postgres 16 backend          |
| **mailpit**             | SMTP Testing & Web UI     |       ✅        |      ✅       |     ❌     | Traefik Web UI + backend SMTP clients         |
| **mariadb**             | Relational Database       |       ❌        |      ✅       |     ✅     | Isolated DB tier + backend consumers          |
| **memcached**           | In-Memory Cache           |       ❌        |      ✅       |     ✅     | Isolated cache tier + backend consumers       |
| **minio**               | S3 Object Storage         |       ✅        |      ✅       |     ❌     | Traefik Console/API + backend S3 clients      |
| **mongodb**             | Document Database         |       ❌        |      ✅       |     ✅     | Isolated DB tier + backend consumers          |
| **mysql8**              | Relational Database       |       ❌        |      ✅       |     ✅     | Isolated DB tier + backend consumers          |
| **n8n**                 | Workflow Automation       |       ✅        |      ✅       |     ✅     | Traefik Web UI + DB connectors & APIs         |
| **node-red**            | Flow-Based Automation     |       ✅        |      ✅       |     ✅     | Traefik Web UI + DB connectors & APIs         |
| **oauth2-proxy**        | Auth Gateway              |       ✅        |      ✅       |     ❌     | Traefik Auth Gateway + configured OIDC issuer |
| **otel-collector**      | OpenTelemetry Collector   |       ❌        |      ✅       |     ❌     | Receives OTLP from backend services           |
| **grafana**             | Observability Dashboard   |       ✅        |      ✅       |     ❌     | Traefik Web UI + Loki/OTel backend            |
| **loki**                | Log Aggregator            |       ❌        |      ✅       |     ✅     | Internal log ingestion and query API          |
| **alloy**               | Docker Log Shipper        |       ❌        |      ✅       |     ❌     | Ships Docker API logs to Loki (backend_net)   |
| **pgvector**            | PostgreSQL 17 + Vector    |       ❌        |      ✅       |     ✅     | Isolated DB tier + Hindsight/consumers        |
| **pocketbase**          | PocketBase Backend & UI   |       ✅        |      ✅       |     ❌     | Traefik Web UI + backend API                  |
| **postgres**            | PostgreSQL 16 Shared DB   |       ❌        |      ✅       |     ✅     | Isolated DB tier + backend consumers          |
| **qdrant**              | Vector Search Engine      |       ✅        |      ✅       |     ✅     | Traefik Web UI/API + vector consumers         |
| **rabbitmq**            | Message Broker & Mgmt UI  |       ✅        |      ✅       |     ✅     | Traefik Mgmt UI + AMQP data broker            |
| **redis**               | In-Memory Key-Value Store |       ❌        |      ✅       |     ✅     | Isolated cache tier + backend consumers       |
| **redisinsight**        | Redis Web UI              |       ✅        |      ✅       |     ✅     | Traefik Web UI + Redis connection             |
| **sonarqube**           | Code Quality Platform     |       ✅        |      ✅       |     ❌     | Traefik Web UI + PostgreSQL backend           |
| **supabase-kong**       | Supabase API Gateway      |       ✅        |      ✅       |     ❌     | Traefik Web Gateway                           |
| **supabase-studio**     | Supabase Dashboard        |       ❌        |      ✅       |     ❌     | Routed via Kong on backend_net                |
| **supabase-auth**       | GoTrue Auth Service       |       ❌        |      ✅       |     ❌     | Internal auth service on backend_net          |
| **supabase-storage**    | Supabase Storage API      |       ❌        |      ✅       |     ❌     | Internal storage service on backend_net       |
| **realtime**            | Realtime Sync Server      |       ❌        |      ✅       |     ❌     | Internal realtime engine on backend_net       |
| **supabase-meta**       | Postgres Metadata API     |       ❌        |      ✅       |     ❌     | Internal metadata service on backend_net      |
| **supabase-db**         | Supabase Database         |       ❌        |      ✅       |     ✅     | Internal PostgreSQL data container            |
| **temporal**            | Temporal Core Engine      |       ❌        |      ✅       |     ❌     | Internal gRPC server + PostgreSQL             |
| **temporal-ui**         | Temporal Web UI           |       ✅        |      ✅       |     ❌     | Traefik Web UI + Temporal server              |
| **woodpecker-server**   | CI Server & UI            |       ✅        |      ✅       |     ❌     | Traefik Web UI + agent communication          |
| **socket-proxy**        | Docker Socket Proxy       |       ❌        |      ✅       |     ❌     | Internal Docker socket access                 |
| **woodpecker-agent**    | CI Worker Agent           |       ❌        |      ✅       |     ❌     | Internal agent communicating with server      |
| **zitadel**             | Identity Provider Core    |       ✅        |      ✅       |     ❌     | Traefik Ingress + PostgreSQL backend          |
| **zitadel-login**       | Zitadel Login UI          |       ✅        |      ✅       |     ❌     | Traefik Ingress + Zitadel core                |
