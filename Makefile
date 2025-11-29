.PHONY: help setup up down restart logs ps clean pull validate health

SHELL := /bin/bash
.DEFAULT_GOAL := help

DOCKER_COMPOSE := docker compose -f docker-compose.shared.yml \
	-f traefik/docker-compose.yml \
	-f postgres/docker-compose.yml \
	-f mysql8/docker-compose.yml \
	-f mongodb/docker-compose.yml \
	-f redis/docker-compose.yml \
	-f rabbitmq/docker-compose.yml \
	-f memcached/docker-compose.yml \
	-f mailpit/docker-compose.yml \
	-f redisinsight/docker-compose.yml \
	-f minio/docker-compose.yml \
	-f gitea/docker-compose.yml \
	-f sonarqube/docker-compose.yml \
	-f jenkins/docker-compose.yml \
	-f concourse/docker-compose.yml \
	-f act_runner/docker-compose.yml \
	-f adminer/docker-compose.yml

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           Docker Shared Services - Makefile Help               ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

setup: ## Setup environment files from .env.example
	@echo "Creating network if it doesn't exist..."
	@docker network create dev_tools --subnet 10.0.0.0/16 --driver bridge 2>/dev/null || true
	@echo "Setting up environment files..."
	@bash setup-env.sh all
	@echo ""

validate: ## Validate environment configuration
	@echo "Validating configuration..."
	@bash setup-env.sh validate
	@echo ""

network: ## Create the dev_tools network
	@echo "Creating network dev_tools..."
	@docker network create dev_tools --subnet 10.0.0.0/16 --driver bridge 2>/dev/null && echo "✅ Network created" || echo "ℹ️  Network already exists"
	@echo ""

up: ## Start all services
	@echo "Creating network if it doesn't exist..."
	@docker network create dev_tools --subnet 10.0.0.0/16 --driver bridge 2>/dev/null || true
	@echo "Starting all services..."
	@$(DOCKER_COMPOSE) up -d
	@echo ""
	@make ps

down: ## Stop all services
	@echo "Stopping all services..."
	@$(DOCKER_COMPOSE) down
	@echo "✅ All services stopped"
	@echo ""

restart: ## Restart all services
	@echo "Restarting all services..."
	@$(DOCKER_COMPOSE) restart
	@echo "✅ All services restarted"
	@echo ""

ps: ## Show status of all services
	@echo ""
	@echo "Service Status:"
	@echo ""
	@$(DOCKER_COMPOSE) ps

logs: ## Show logs from all services (tail -f)
	@$(DOCKER_COMPOSE) logs -f

logs-tail: ## Show last 100 lines of logs
	@$(DOCKER_COMPOSE) logs --tail=100

pull: ## Pull latest images for all services
	@echo "Pulling latest images..."
	@$(DOCKER_COMPOSE) pull
	@echo "✅ Images pulled"

health: ## Check health status of services
	@echo ""
	@echo "Checking service health..."
	@echo ""
	@$(DOCKER_COMPOSE) ps | grep -E "healthy|unhealthy|starting" || echo "All services running"

clean: ## Remove all containers and volumes
	@echo "⚠️  WARNING: This will remove all data!"
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "✅ Cleaned up"; \
	else \
		echo "Cancelled"; \
	fi

prune: ## Remove unused Docker resources
	@echo "Pruning Docker resources..."
	@docker system prune -f --volumes
	@echo "✅ Pruned"

exec: ## Execute command in a service (usage: make exec SERVICE=postgres CMD="psql -U postgres")
	@$(DOCKER_COMPOSE) exec $(SERVICE) $(CMD)

logs-service: ## Show logs from specific service (usage: make logs-service SERVICE=postgres)
	@$(DOCKER_COMPOSE) logs -f $(SERVICE)

ps-service: ## Show status of specific service (usage: make ps-service SERVICE=postgres)
	@$(DOCKER_COMPOSE) ps $(SERVICE)

stop-service: ## Stop specific service (usage: make stop-service SERVICE=postgres)
	@echo "Stopping $(SERVICE)..."
	@$(DOCKER_COMPOSE) stop $(SERVICE)
	@echo "✅ $(SERVICE) stopped"

start-service: ## Start specific service (usage: make start-service SERVICE=postgres)
	@echo "Starting $(SERVICE)..."
	@$(DOCKER_COMPOSE) start $(SERVICE)
	@echo "✅ $(SERVICE) started"

restart-service: ## Restart specific service (usage: make restart-service SERVICE=postgres)
	@echo "Restarting $(SERVICE)..."
	@$(DOCKER_COMPOSE) restart $(SERVICE)
	@echo "✅ $(SERVICE) restarted"

build: ## Build all services
	@echo "Building all services..."
	@$(DOCKER_COMPOSE) build --no-cache

inspect: ## Inspect network configuration
	@echo ""
	@echo "Network Configuration:"
	@docker network inspect dev_tools || echo "Network not found"
	@echo ""

version: ## Show Docker Compose version
	@$(DOCKER_COMPOSE) --version

info: ## Show service information
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                     Service Information                        ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Network: dev_tools"
	@echo "Subnet: 172.20.0.0/16"
	@echo ""
	@echo "Services:"
	@echo "  • Traefik (Reverse Proxy) - http://localhost:8080"
	@echo "  • PostgreSQL - localhost:5432"
	@echo "  • MySQL 8 - localhost:3306"
	@echo "  • MongoDB - localhost:27017"
	@echo "  • Redis - localhost:6379"
	@echo "  • RabbitMQ - localhost:5672 (management: 15672)"
	@echo "  • Memcached - localhost:11211"
	@echo "  • Mailpit - localhost:8025 (SMTP: 1025)"
	@echo "  • Redis Insight - http://localhost:5540"
	@echo "  • MinIO - http://localhost:9002"
	@echo "  • Gitea - http://localhost:3000"
	@echo "  • SonarQube - http://localhost:9000"
	@echo "  • Jenkins - http://localhost:8090"
	@echo "  • Concourse - http://localhost:8070"
	@echo "  • Adminer - http://localhost:8081"
	@echo ""

debug: ## Debug mode - keep services running and show logs
	@echo "Starting services in debug mode..."
	@$(DOCKER_COMPOSE) up

.PHONY: all-status
all-status: ps health ## Show detailed status of all services
	@echo ""
	@echo "Detailed Status:"
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U postgres 2>/dev/null && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL not ready"
	@$(DOCKER_COMPOSE) exec mysql8 mysqladmin ping -h localhost -u root -p$$(grep MYSQL_ROOT_PASSWORD mysql8/.env | cut -d '=' -f 2) 2>/dev/null && echo "✅ MySQL ready" || echo "❌ MySQL not ready"
	@$(DOCKER_COMPOSE) exec redis redis-cli ping 2>/dev/null && echo "✅ Redis ready" || echo "❌ Redis not ready"
	@echo ""
