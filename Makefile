.PHONY: help setup passwords ps health remove-all prune remove-config info up down stop restart logs cert validate manage tui sync format format-check

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Python managers
PYTHON_ENV_MGR := python3 bin/env_manager.py
PYTHON_SVC_MGR := python3 bin/service_manager.py
UV ?= uv

# Optional shared password for setup/passwords targets:
#   make setup password='Password102!'
#   DSS_SHARED_PASSWORD='Password102!' make setup
#   make passwords password='Password102!'
# When omitted, setup uses the shared development password below.
password ?= Password102!

# Dynamic DOCKER_COMPOSE command that includes all services
DOCKER_COMPOSE = docker compose -f docker-compose.shared.yml \
	$(shell find . -maxdepth 2 -name "docker-compose.yml" -not -path "./docker-compose.shared.yml" | LC_ALL=C sort | sed 's|^./|-f |')

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           Docker Shared Services - Management Console          ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage:"
	@echo "  make <command> [service=<service_name>]"
	@echo ""
	@echo "Commands:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {print $$1 "\t" $$2}' | \
		LC_ALL=C sort -f -k1,1 -u | \
		awk -F'\t' '{printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

setup: ## Setup env files, networks, certs (optional: password='Password102!')
	@echo "Checking shared Docker networks (infra_shared, dev_tools)..."
	@# Two bridges cannot share one CIDR; prefer adjacent /16s in 10/8. Fall back if pool overlaps (OrbStack/Docker Desktop).
	@for pair in "infra_shared:10.0.0.0/16" "dev_tools:10.1.0.0/16"; do \
		name=$${pair%%:*}; subnet=$${pair#*:}; \
		if docker network inspect $$name >/dev/null 2>&1; then \
			echo "  $$name: already exists"; \
		elif docker network create $$name --subnet $$subnet --driver bridge >/dev/null 2>&1; then \
			echo "  $$name: created ($$subnet)"; \
		elif docker network create $$name --driver bridge >/dev/null 2>&1; then \
			echo "  $$name: created (auto subnet; $$subnet overlapped another Docker pool)"; \
		else \
			echo "  ERROR: could not create $$name" >&2; exit 1; \
		fi; \
	done
	@echo "Checking environment files..."
	@$(PYTHON_ENV_MGR) check all
	@echo ""
	@read -p "Do you want to create missing .env files from .env.example? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PYTHON_ENV_MGR) create all; \
	fi
	@# Append keys newly added to .env.example without overwriting existing values.
	@$(PYTHON_ENV_MGR) merge-missing all
	@# ONE shared password for all Password102! placeholders (DB/Redis/MinIO/…).
	@# Override: make setup password='Password102!'  OR  DSS_SHARED_PASSWORD='…' make setup
	@# Unique secrets (Garage, Woodpecker agent) are filled next and stay distinct.
	@$(PYTHON_ENV_MGR) fill-shared-password $(if $(password),--password "$(password)",)
	@$(PYTHON_ENV_MGR) fill-secrets all
	@echo "Checking Dozzle users file (dozzle/data/users.yml)..."
	@mkdir -p dozzle/data
	@if [[ -d "dozzle/data/users.yml" ]]; then \
		echo "  dozzle/data/users.yml is a directory -> removing and regenerating..."; \
		rm -rf dozzle/data/users.yml; \
	fi; \
	if [[ ! -f "dozzle/data/users.yml" ]]; then \
		DOZZLE_PW="$${DSS_SHARED_PASSWORD:-}"; \
		if [[ -z "$$DOZZLE_PW" && -f .env ]]; then \
			DOZZLE_PW=$$(grep -E '^DSS_SHARED_PASSWORD=' .env | head -1 | cut -d= -f2-); \
		fi; \
		DOZZLE_PW="$${DOZZLE_PW:-Password102!}"; \
		echo "  dozzle/data/users.yml not found -> generating admin (shared password)..."; \
		docker run --rm -i amir20/dozzle generate admin \
		  --password "$$DOZZLE_PW" \
		  --email admin@example.com \
		  --name "Admin" > dozzle/data/users.yml; \
	else \
		echo "  dozzle/data/users.yml already exists"; \
	fi
	@$(PYTHON_ENV_MGR) validate all || true
	@$(PYTHON_ENV_MGR) summary all
	@echo ""
	@read -p "Do you want to generate SSL certificates? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) cert; \
	fi
	@echo ""

passwords: ## Apply ONE shared password to all services (optional: password='…' force=1)
	@$(PYTHON_ENV_MGR) fill-shared-password \
		$(if $(password),--password "$(password)",) \
		$(if $(filter 1 true yes,$(force)),--force,)

cert: ## Generate SSL certificates for Traefik
	@echo "Detecting local IP..."
	@CURRENT_IP=$$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $$2}' | sed 's/addr://' | head -n 1); \
	echo "Local IP detected: $$CURRENT_IP"; \
	mkdir -p traefik/certs; \
	if command -v mkcert >/dev/null 2>&1; then \
		mkcert -cert-file traefik/certs/server.crt \
		       -key-file traefik/certs/server.key \
		       "$$CURRENT_IP" \
		       "*.dss.localhost" \
		       "*.minio.dss.localhost" \
		       "*.garage.dss.localhost" \
		       "*.tts.dss.localhost" \
		       "dss.localhost" \
		       localhost \
		       127.0.0.1 \
		       ::1; \
		echo "✅ Success: Certificates are generated in traefik/certs/"; \
	else \
		echo "❌ Error: mkcert is not installed. Please install it first."; \
		exit 1; \
	fi

up: ## Start services (usage: make up [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

down: ## Stop and remove services (usage: make down [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

stop: ## Stop services (usage: make stop [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

restart: ## Restart services (usage: make restart [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

manage: ## Interactive multi-select service manager (up selected, down unselected)
	@$(PYTHON_SVC_MGR) manage

tui: ## Optional Textual dashboard (requires uv + interactive terminal)
	@if ! command -v $(UV) >/dev/null 2>&1; then \
		echo "❌ uv is required for make tui."; \
		echo "   Install: https://docs.astral.sh/uv/"; \
		echo "   Non-TUI workflows still work: make manage, make up, make ps, make logs, …"; \
		exit 1; \
	fi
	@if [ ! -t 0 ] || [ ! -t 1 ]; then \
		echo "❌ make tui needs an interactive terminal (TTY)."; \
		echo "   Use make manage / make up / make ps / make logs instead."; \
		exit 1; \
	fi
	@PYTHONPATH=bin $(UV) run --group tui python -m tui

logs: ## Show logs (usage: make logs [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

ps: ## Show status of all running services
	@echo ""
	@echo "Service Status:"
	@echo ""
	@$(DOCKER_COMPOSE) ps
	@echo ""

health: ## Check health status of all services (usage: make health [service=pgvector])
	@echo ""
	@echo "Service Health:"
	@echo ""
	@if [ -n "$(service)" ]; then \
		docker compose --project-directory $(service) -f docker-compose.shared.yml -f $(service)/docker-compose.yml ps; \
	else \
		$(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}"; \
	fi
	@echo ""

remove-all: ## Remove all containers and volumes (⚠️ DANGER: Removes all data)
	@echo "⚠️  WARNING: This will remove all data from all services!"
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "✅ All containers and volumes removed"; \
	else \
		echo "Operation cancelled"; \
	fi

prune: ## Remove unused Docker resources
	@echo "Pruning Docker resources..."
	@docker system prune -f --volumes
	@echo "✅ Pruned"

remove-config: ## Remove all .env files that have a matching .env.example
	@echo "Searching for .env files with a matching .env.example..."
	@env_files=(); \
	while IFS= read -r -d '' ex; do \
		dir=$$(dirname "$$ex"); \
		env="$$dir/.env"; \
		[[ -f "$$env" ]] && env_files+=("$$env"); \
	done < <(find . -maxdepth 2 -name '.env.example' -print0); \
	if [[ $${#env_files[@]} -eq 0 ]]; then \
		echo "No .env files found."; \
		exit 0; \
	fi; \
	echo ""; \
	echo "Found $${#env_files[@]} .env file(s):"; \
	printf '  %s\n' "$${env_files[@]}"; \
	echo ""; \
	read -p "Remove these .env files? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		for f in "$${env_files[@]}"; do rm -f "$$f" && echo "  Removed $$f"; done; \
		echo ""; \
		echo "✅ Removed $${#env_files[@]} .env file(s). Run 'make setup' to recreate from .env.example."; \
	else \
		echo "Operation cancelled"; \
	fi

info: ## Show service information and access URLs
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                     Service Information                        ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Networks (10/8 plan, two non-overlapping /16s):"
	@echo "  • infra_shared — 10.0.0.0/16 (Traefik + main stack)"
	@echo "  • dev_tools — 10.1.0.0/16 (legacy / external compose)"
	@echo ""
	@echo "Services:"
	@echo "  • Adminer - https://adminer.dss.localhost"
	@echo "  • Appsmith - https://appsmith.dss.localhost"
	@echo "  • Bugsink - https://bugsink.dss.localhost"
	@echo "  • ChromaDB - https://chromadb.dss.localhost"
	@echo "  • ChromaDB Admin - https://chromadb-admin.dss.localhost"
	@echo "  • Centrifugo - http://localhost:8010 (container: centrifugo:8000)"
	@echo "  • Concourse - https://concourse.dss.localhost"
	@echo "  • Crawl4AI - https://crawl4ai.dss.localhost"
	@echo "  • Dockge - https://dockge.dss.localhost"
	@echo "  • Dozzle - https://dozzle.dss.localhost"
	@echo "  • Garage (S3) - https://s3.garage.dss.localhost (admin: https://admin.garage.dss.localhost)"
	@echo "  • Gitea - https://gitea.dss.localhost (SSH: localhost:2222)"
	@echo "  • Gotenberg - http://localhost:3030 (container: gotenberg:3000)"
	@echo "  • Grafana - https://grafana.dss.localhost [otel stack]"
	@echo "  • Hasura - https://hasura.dss.localhost"
	@echo "  • Inngest - https://inngest.dss.localhost"
	@echo "  • Jenkins - https://jenkins.dss.localhost (agent: localhost:50000)"
	@echo "  • Kafka - localhost:9092"
	@echo "  • Kafka UI - https://kafka-ui.dss.localhost"
	@echo "  • Loki - http://localhost:3100 [otel stack]"
	@echo "  • Mailpit - https://mailpit.dss.localhost (SMTP: localhost:1025)"
	@echo "  • MariaDB 11 - localhost:3307"
	@echo "  • Memcached - localhost:11211"
	@echo "  • Mermaid Live Editor - https://mermaid.dss.localhost"
	@echo "  • MinIO - https://minio.dss.localhost (S3: localhost:9002)"
	@echo "  • MongoDB - localhost:27017"
	@echo "  • MySQL 8 - localhost:3306"
	@echo "  • n8n - https://n8n.dss.localhost"
	@echo "  • Node-RED - https://node-red.dss.localhost"
	@echo "  • oauth2-proxy (auth gateway) - https://auth.dss.localhost (Traefik only; needs Zitadel app)"
	@echo "  • OTel Collector - localhost:4317 (gRPC), localhost:4318 (HTTP) [otel stack]"
	@echo "  • PocketBase - https://pocketbase.dss.localhost"
	@echo "  • PgVector (PostgreSQL 17, standalone) - localhost:5433"
	@echo "  • Portainer - https://portainer.dss.localhost"
	@echo "  • Postgres (PostgreSQL 16, default shared DB) - localhost:5432"
	@echo "  • RabbitMQ - https://rabbitmq.dss.localhost (AMQP: localhost:5672)"
	@echo "  • Redis - localhost:6379"
	@echo "  • Redis Insight - https://redisinsight.dss.localhost"
	@echo "  • SonarQube - https://sonarqube.dss.localhost"
	@echo "  • Supabase - https://studio.dss.localhost (API: https://supabase.dss.localhost, DB: localhost:5434)"
	@echo "  • Temporal - localhost:7233 (UI: https://temporal.dss.localhost)"
	@echo "  • Traefik (Reverse Proxy) - http://localhost:8080"
	@echo "  • Woodpecker CI - https://woodpecker.dss.localhost"
	@echo "  • Zitadel - https://zitadel.dss.localhost"
	@echo ""
	@echo "Opt-in UI auth (oauth2-proxy + Zitadel; OFF by default):"
	@echo "  • Candidates: mermaid-live-editor, temporal UI, chromadb, qdrant, kafka-ui"
	@echo "  • Enable: set AUTH_ENABLED=true and AUTH_MIDDLEWARE=auth-default in that service .env, then restart"
	@echo "  • Status: python bin/env_manager.py summary  (shows AUTH gateway on/off)"
	@echo "  • Setup: see oauth2-proxy/README.md and docs/configuration.md"
	@echo ""

validate: ## Validate all Docker Compose files
	@$(PYTHON_SVC_MGR) --validate-compose

sync: ## Install Python tooling deps with uv (ruff, yamlfix, mdformat, …)
	@$(UV) sync --group dev
	@echo "✅ uv sync complete"

format: ## Format YAML, JSON, Markdown, Python, and .env.example files
	@$(UV) sync --group dev --quiet
	@PYTHONUNBUFFERED=1 $(UV) run python scripts/format_repo.py

format-check: ## Check formatting without writing changes
	@$(UV) sync --group dev --quiet
	@PYTHONUNBUFFERED=1 $(UV) run python scripts/format_repo.py --check
