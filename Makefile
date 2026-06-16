.PHONY: help setup ps remove-all prune remove-config info up down stop restart logs cert validate manage

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Python managers
PYTHON_ENV_MGR := python3 bin/env_manager.py
PYTHON_SVC_MGR := python3 bin/service_manager.py

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

setup: ## Setup environment files, networks and certificates
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
	@echo "Checking Dozzle users file (dozzle/data/users.yml)..."
	@mkdir -p dozzle/data
	@if [[ -d "dozzle/data/users.yml" ]]; then \
		echo "  dozzle/data/users.yml is a directory -> removing and regenerating..."; \
		rm -rf dozzle/data/users.yml; \
	fi; \
	if [[ ! -f "dozzle/data/users.yml" ]]; then \
		echo "  dozzle/data/users.yml not found -> generating default admin credentials..."; \
		docker run --rm -i amir20/dozzle generate admin \
		  --password password102 \
		  --email admin@example.com \
		  --name "Admin" > dozzle/data/users.yml; \
	else \
		echo "  dozzle/data/users.yml already exists"; \
	fi
	@echo ""
	@read -p "Do you want to create missing .env files from .env.example? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PYTHON_ENV_MGR) create all; \
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

cert: ## Generate SSL certificates for Traefik
	@echo "Detecting local IP..."
	@CURRENT_IP=$$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $$2}' | sed 's/addr://' | head -n 1); \
	echo "Local IP detected: $$CURRENT_IP"; \
	mkdir -p traefik/certs; \
	if command -v mkcert >/dev/null 2>&1; then \
		mkcert -cert-file traefik/certs/server.crt \
		       -key-file traefik/certs/server.key \
		       "$$CURRENT_IP" \
		       "*.localhost" \
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

logs: ## Show logs (usage: make logs [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@,$@)

ps: ## Show status of all running services
	@echo ""
	@echo "Service Status:"
	@echo ""
	@$(DOCKER_COMPOSE) ps
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
	@echo "  • Adminer - http://localhost:8081"
	@echo "  • Appsmith - http://localhost:8091 (Host: appsmith.localhost)"
	@echo "  • ChromaDB - http://localhost:8000 (Host: chromadb.localhost)"
	@echo "  • ChromaDB Admin - http://localhost:8001 (Host: chromadb-admin.localhost)"
	@echo "  • Centrifugo - http://localhost:8010 (container: centrifugo:8000)"
	@echo "  • Concourse - http://localhost:8070"
	@echo "  • Dockge - http://localhost:5001"
	@echo "  • Dozzle - http://localhost:8888 (Host: dozzle.localhost)"
	@echo "  • Gitea - http://localhost:3000"
	@echo "  • Gotenberg - http://localhost:3030 (container: gotenberg:3000)"
	@echo "  • Grafana - http://localhost:3001 (Host: grafana.localhost)"
	@echo "  • Inngest - http://localhost:8288 (Host: inngest.localhost)"
	@echo "  • Jaeger - http://localhost:16686 (Host: jaeger.localhost)"
	@echo "  • Jenkins - http://localhost:8090"
	@echo "  • Kafka - localhost:9092"
	@echo "  • Kafka UI - http://localhost:8082 (Host: kafka-ui.localhost)"
	@echo "  • Mailpit - localhost:8025 (SMTP: 1025)"
	@echo "  • MariaDB 11 - localhost:3307"
	@echo "  • Memcached - localhost:11211"
	@echo "  • MinIO - http://localhost:9002"
	@echo "  • MongoDB - localhost:27017"
	@echo "  • MySQL 8 - localhost:3306"
	@echo "  • n8n - http://localhost:5678 (Host: n8n.localhost)"
	@echo "  • OTel Collector - localhost:4317 (gRPC), localhost:4318 (HTTP)"
	@echo "  • PocketBase - http://localhost:8140 (Host: pocketbase.localhost)"
	@echo "  • PgVector (PostgreSQL 17) - localhost:5432"
	@echo "  • Portainer - http://localhost:9007 (HTTPS: 9443)"
	@echo "  • Postgres (PostgreSQL 16) - localhost:5433"
	@echo "  • Prometheus - http://localhost:9090 (Host: prometheus.localhost)"
	@echo "  • RabbitMQ - localhost:5672 (management: 15672)"
	@echo "  • Redis - localhost:6379"
	@echo "  • Redis Insight - http://localhost:5540"
	@echo "  • SonarQube - http://localhost:9000"
	@echo "  • Temporal - localhost:7233 (UI: http://localhost:8083 or temporal.localhost)"
	@echo "  • Traefik (Reverse Proxy) - http://localhost:8080"
	@echo "  • Woodpecker CI - http://localhost:8012 (Host: woodpecker.localhost)"
	@echo ""

validate: ## Validate all Docker Compose files
	@echo "Validating Docker Compose configuration..."
	@$(DOCKER_COMPOSE) config >/dev/null
	@echo "✅ Compose configuration is valid"
