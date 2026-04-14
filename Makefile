.PHONY: help setup ps clean prune info up down stop restart logs cert

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Python managers
PYTHON_ENV_MGR := python3 bin/env_manager.py
PYTHON_SVC_MGR := python3 bin/service_manager.py

# Dynamic DOCKER_COMPOSE command that includes all services
DOCKER_COMPOSE = docker compose -f docker-compose.shared.yml \
	$(shell find . -maxdepth 2 -name "docker-compose.yml" -not -path "./docker-compose.shared.yml" | sed 's|^./|-f |')

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           Docker Shared Services - Management Console          ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage:"
	@echo "  make <command> [service=<service_name>]"
	@echo ""
	@echo "Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

setup: ## Setup environment files, network and certificates
	@echo "Creating network if it doesn't exist..."
	@docker network create infra_shared --subnet 10.0.0.0/16 --driver bridge 2>/dev/null || true
	@echo "Checking environment files..."
	@$(PYTHON_ENV_MGR) check all
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
		       localhost \
		       127.0.0.1 \
		       ::1; \
		echo "✅ Success: Certificates are generated in traefik/certs/"; \
	else \
		echo "❌ Error: mkcert is not installed. Please install it first."; \
		exit 1; \
	fi

up: ## Start services (usage: make up [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@)

down: ## Stop and remove services (usage: make down [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@)

stop: ## Stop services (usage: make stop [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@)

restart: ## Restart services (usage: make restart [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@)

logs: ## Show logs (usage: make logs [service=pgvector])
	@$(PYTHON_SVC_MGR) $(if $(service),$(service) $@)

ps: ## Show status of all running services
	@echo ""
	@echo "Service Status:"
	@echo ""
	@$(DOCKER_COMPOSE) ps
	@echo ""

clean: ## Remove all containers and volumes (⚠️ DANGER: Removes all data)
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

info: ## Show service information and access URLs
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                     Service Information                        ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Network: infra_shared"
	@echo "Subnet: 10.0.0.0/16"
	@echo ""
	@echo "Services:"
	@echo "  • Adminer - http://localhost:8081"
	@echo "  • Appsmith - http://localhost:8091 (Host: appsmith.localhost)"
	@echo "  • ChromaDB - http://localhost:8000 (Host: chromadb.localhost)"
	@echo "  • ChromaDB Admin - http://localhost:8001 (Host: chromadb-admin.localhost)"
	@echo "  • Concourse - http://localhost:8070"
	@echo "  • Dockge - http://localhost:5001"
	@echo "  • Dozzle - http://localhost:8888 (Host: dozzle.localhost)"
	@echo "  • Gitea - http://localhost:3000"
	@echo "  • Grafana - http://localhost:3001 (Host: grafana.localhost)"
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
