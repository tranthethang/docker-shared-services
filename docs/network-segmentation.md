# Network Segmentation Architecture

## Overview

Docker Shared Services uses a three-tier network segmentation model that isolates external ingress traffic from internal application logic and database persistence:

1. **`traefik_proxy`** (`10.0.0.0/16`): The public-facing edge network. Connects Traefik reverse proxy to services that expose Web UIs or HTTP APIs routed by Traefik (`https://*.dss.localhost`).
1. **`backend_net`** (`10.1.0.0/16`): The internal application and orchestration network. Interconnects application logic containers, background workers, and CI/CD agents. Data stores are not attached to it.
1. **`data_net`** (`10.2.0.0/16`): The data storage and persistence network. Data stores (relational and document databases, caches, message brokers, vector stores, Loki) attach only here, plus `traefik_proxy` when they have a UI. Only declared clients join it (see [Data tier rules](#data-tier-rules)). Traefik does NOT connect to `data_net`.

## Network Topology & Addressing

| Network Name    | Subnet        | Gateway    | Purpose                                           | Direct Traefik Ingress |
| --------------- | ------------- | ---------- | ------------------------------------------------- | ---------------------- |
| `traefik_proxy` | `10.0.0.0/16` | `10.0.0.1` | Traefik edge routing and HTTP(S) entrypoint       | Yes                    |
| `backend_net`   | `10.1.0.0/16` | `10.1.0.1` | Inter-service application communication & workers | No                     |
| `data_net`      | `10.2.0.0/16` | `10.2.0.1` | Database, cache, and storage persistence tier     | No                     |

## Service-to-Network Mapping Matrix

Below is the mapping for all container services in the repository:

| Service / Container         | Primary Role              | `traefik_proxy` | `backend_net` | `data_net` | Notes                                                |
| --------------------------- | ------------------------- | :-------------: | :-----------: | :--------: | ---------------------------------------------------- |
| **traefik**                 | Reverse Proxy             |       ✅        |      ❌       |     ❌     | Docker API via traefik-socket-proxy                  |
| **dockge**                  | Docker Stack UI           |       ✅        |      ❌       |     ❌     | Traefik Web UI                                       |
| **dozzle**                  | Container Log UI          |       ✅        |      ❌       |     ❌     | Traefik Web UI; Docker API via dozzle-socket-proxy   |
| **mermaid-live-editor**     | Diagram Editor UI         |       ✅        |      ❌       |     ❌     | Traefik Web UI                                       |
| **portainer**               | Container Management UI   |       ✅        |      ❌       |     ❌     | Traefik Web UI                                       |
| **act_runner**              | Gitea Actions Runner      |       ❌        |      ✅       |     ❌     | Interacts with Gitea on `backend_net`                |
| **adminer**                 | Database Web UI           |       ✅        |      ✅       |     ✅     | Traefik Web UI + connects to DBs                     |
| **appsmith**                | Low-Code App Platform     |       ✅        |      ✅       |     ✅     | Traefik Web UI + queries data & APIs                 |
| **bugsink**                 | Error Tracking            |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL on data_net              |
| **centrifugo**              | Realtime Messaging Server |       ❌        |      ✅       |     ❌     | Internal messaging API / localhost:8010              |
| **chromadb**                | Vector DB                 |       ✅        |      ❌       |     ✅     | Traefik HTTP API + data_net                          |
| **chromadb-admin**          | ChromaDB Admin UI         |       ✅        |      ✅       |     ✅     | Traefik Web UI + ChromaDB on data_net                |
| **concourse**               | CI/CD Platform            |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL on data_net              |
| **crawl4ai**                | Web Crawler API/UI        |       ✅        |      ✅       |     ❌     | Traefik Web UI/API + internal workers                |
| **garage**                  | Distributed S3 Storage    |       ✅        |      ✅       |     ❌     | Traefik S3 / Admin + backend S3 clients              |
| **garage-ui**               | Garage Admin Web UI       |       ✅        |      ✅       |     ❌     | Traefik Web UI + Garage APIs on backend_net          |
| **gitea**                   | Git Service               |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL on data_net              |
| **gotenberg**               | PDF Conversion Service    |       ❌        |      ✅       |     ❌     | Internal HTTP API / localhost:3030                   |
| **hasura**                  | GraphQL Engine            |       ✅        |      ✅       |     ✅     | Traefik GraphQL API/Console + PostgreSQL on data_net |
| **hindsight**               | MCP Memory Service        |       ✅        |      ✅       |     ✅     | Traefik Web UI/API + PgVector on data_net            |
| **inngest**                 | Background Job Platform   |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL/Redis on data_net        |
| **jenkins**                 | Automation Server         |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL on data_net              |
| **kafka** (broker)          | Event Streaming Broker    |       ❌        |      ❌       |     ✅     | data_net only; kafka-ui joins data_net               |
| **kafka-ui**                | Kafka Management UI       |       ✅        |      ✅       |     ✅     | Traefik Web UI + Kafka on data_net                   |
| **litellm**                 | OpenAI-compatible proxy   |       ✅        |      ✅       |     ✅     | Traefik UI/API + Postgres 16 on data_net             |
| **mailpit**                 | SMTP Testing & Web UI     |       ✅        |      ✅       |     ❌     | Traefik Web UI + backend SMTP clients                |
| **mariadb**                 | Relational Database       |       ❌        |      ❌       |     ✅     | data_net only; host port on 127.0.0.1                |
| **memcached**               | In-Memory Cache           |       ❌        |      ❌       |     ✅     | data_net only; host port on 127.0.0.1                |
| **minio**                   | S3 Object Storage         |       ✅        |      ✅       |     ❌     | Traefik Console/API + backend S3 clients             |
| **mongodb**                 | Document Database         |       ❌        |      ❌       |     ✅     | data_net only; host port on 127.0.0.1                |
| **mysql8**                  | Relational Database       |       ❌        |      ❌       |     ✅     | data_net only; host port on 127.0.0.1                |
| **n8n**                     | Workflow Automation       |       ✅        |      ✅       |     ✅     | Traefik Web UI + DB connectors & APIs                |
| **node-red**                | Flow-Based Automation     |       ✅        |      ✅       |     ✅     | Traefik Web UI + DB connectors & APIs                |
| **oauth2-proxy**            | Auth Gateway              |       ✅        |      ✅       |     ❌     | Traefik Auth Gateway + configured OIDC issuer        |
| **otel-collector**          | OpenTelemetry Collector   |       ❌        |      ✅       |     ✅     | OTLP on backend_net; exports to Loki                 |
| **grafana**                 | Observability Dashboard   |       ✅        |      ✅       |     ✅     | Traefik Web UI + Loki on data_net                    |
| **loki**                    | Log Aggregator            |       ❌        |      ❌       |     ✅     | data_net only; otel clients join data_net            |
| **alloy**                   | Docker Log Shipper        |       ❌        |      ✅       |     ✅     | Docker API via alloy-socket-proxy; Loki on data_net  |
| **pgvector**                | PostgreSQL 17 + Vector    |       ❌        |      ❌       |     ✅     | data_net only; Hindsight joins data_net              |
| **pocketbase**              | PocketBase Backend & UI   |       ✅        |      ✅       |     ❌     | Traefik Web UI + backend API                         |
| **postgres**                | PostgreSQL 16 Shared DB   |       ❌        |      ❌       |     ✅     | data_net only; consumers join data_net               |
| **qdrant**                  | Vector Search Engine      |       ✅        |      ❌       |     ✅     | Traefik Web UI/API + data_net                        |
| **rabbitmq**                | Message Broker & Mgmt UI  |       ✅        |      ❌       |     ✅     | Traefik Mgmt UI + AMQP on data_net                   |
| **redis**                   | In-Memory Key-Value Store |       ❌        |      ❌       |     ✅     | data_net only; consumers join data_net               |
| **redisinsight**            | Redis Web UI              |       ✅        |      ✅       |     ✅     | Traefik Web UI + Redis connection                    |
| **sonarqube**               | Code Quality Platform     |       ✅        |      ✅       |     ✅     | Traefik Web UI + PostgreSQL on data_net              |
| **supabase-kong**           | Supabase API Gateway      |       ✅        |      ✅       |     ❌     | Traefik Web Gateway                                  |
| **supabase-studio**         | Supabase Dashboard        |       ❌        |      ✅       |     ✅     | Routed via Kong; DB on data_net                      |
| **supabase-auth**           | GoTrue Auth Service       |       ❌        |      ✅       |     ✅     | Auth service; DB on data_net                         |
| **supabase-storage**        | Supabase Storage API      |       ❌        |      ✅       |     ✅     | Storage API; DB on data_net                          |
| **realtime**                | Realtime Sync Server      |       ❌        |      ✅       |     ✅     | Realtime engine; DB on data_net                      |
| **supabase-meta**           | Postgres Metadata API     |       ❌        |      ✅       |     ✅     | Metadata API; DB on data_net                         |
| **supabase-db**             | Supabase Database         |       ❌        |      ❌       |     ✅     | data_net only; Supabase services join it             |
| **temporal**                | Temporal Core Engine      |       ❌        |      ✅       |     ✅     | Internal gRPC server + PostgreSQL on data_net        |
| **temporal-ui**             | Temporal Web UI           |       ✅        |      ✅       |     ❌     | Traefik Web UI + Temporal server                     |
| **woodpecker-server**       | CI Server & UI            |       ✅        |      ✅       |     ❌     | Traefik Web UI + agent communication                 |
| **woodpecker-socket-proxy** | Docker Socket Proxy       |       ❌        |      ❌       |     ❌     | Agent-only Docker API on internal woodpecker_docker  |
| **woodpecker-agent**        | CI Worker Agent           |       ❌        |      ✅       |     ❌     | Internal agent communicating with server             |
| **zitadel**                 | Identity Provider Core    |       ✅        |      ✅       |     ✅     | Traefik Ingress + PostgreSQL on data_net             |
| **zitadel-login**           | Zitadel Login UI          |       ✅        |      ✅       |     ❌     | Traefik Ingress + Zitadel core                       |
| **traefik-socket-proxy**    | Docker Socket Proxy       |       ❌        |      ❌       |     ❌     | Traefik-only Docker API on internal traefik_docker   |
| **dozzle-socket-proxy**     | Docker Socket Proxy       |       ❌        |      ❌       |     ❌     | Dozzle-only Docker API on internal dozzle_docker     |
| **alloy-socket-proxy**      | Docker Socket Proxy       |       ❌        |      ❌       |     ❌     | Alloy-only Docker API on internal otel_docker        |

## Data tier rules

`tests/test_network_tiers.py` (`make test`) enforces these rules:

- Every data store is on `data_net` and not on `backend_net`. Data stores: `postgres`, `pgvector`, `mysql8`, `mariadb`, `mongodb`, `redis`, `memcached`, `kafka`, `loki`, `supabase-db`, `chromadb`, `qdrant`, `rabbitmq`.
- A non-data container joins `data_net` only when one of these holds:
  - its project is a consumer of a data store in `PACKAGE_REQUIRES` (`dss/core/config.py`);
  - it is in the same Compose project as a data store (for example `kafka-ui`, `grafana`, the Supabase services);
  - its project is a data-store UI listed in `DATA_CLIENT_UI_SERVICES`.
- Every `PACKAGE_REQUIRES` consumer of a data store has a container on `data_net`.

`data_net` is not `internal: true`. An internal network blocks the `127.0.0.1` host ports that local database clients use.

Consumers reach a data store at its container port (`postgres:5432`, `redis:6379`). The `*_PORT` variables in the data-store projects only set the host port.

## Docker API access

A `:ro` bind mount of `/var/run/docker.sock` does not limit the Docker API. A client with the socket can still create and stop containers. Services that only read Docker state go through a `tecnativa/docker-socket-proxy` sidecar on an internal network that only that client joins:

| Client           | Proxy                     | Internal network    | Allowed API sections              |
| ---------------- | ------------------------- | ------------------- | --------------------------------- |
| traefik          | `traefik-socket-proxy`    | `traefik_docker`    | `CONTAINERS`                      |
| dozzle           | `dozzle-socket-proxy`     | `dozzle_docker`     | `CONTAINERS`, `INFO`              |
| alloy            | `alloy-socket-proxy`      | `otel_docker`       | `CONTAINERS`, `NETWORKS`          |
| woodpecker-agent | `woodpecker-socket-proxy` | `woodpecker_docker` | runs CI containers (`POST`, etc.) |

`portainer`, `dockge`, and `act_runner` mount the socket read-write because they manage containers. Treat each of them as root-equivalent on the host.

## Auth gateway scope

The auth middlewares (`auth-default`, `auth-admin`) apply only to requests that pass through Traefik. Containers on `traefik_proxy` can reach each other's ports directly and bypass them. This is accepted for a local development stack.
