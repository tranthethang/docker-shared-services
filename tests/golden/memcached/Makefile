.PHONY: help setup passwords cert validate up down restart recreate

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON_ENV_MGR := uv run --frozen --no-dev python -m dss.cli.env
password ?=

# One compose project per service, like dss/cli/service.py: --project-directory
# loads <service>/.env for interpolation and resolves ./ paths inside <service>/.
STARTUP_SERVICES := memcached
SHUTDOWN_SERVICES := memcached
# consumer:backend. up/recreate wait until each backend is running and healthy.
SERVICE_DEPS := 
READY_TIMEOUT ?= 300
COMPOSE = docker compose --project-directory $$s -f docker-compose.shared.yml -f $$s/docker-compose.yml

help: ## Show this help message
	@echo "Packaged Docker Shared Services stack"
	@echo ""
	@echo "Usage:"
	@echo "  make <command>"
	@echo ""
	@echo "Commands:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "} {print $$1 "\t" $$2}' | \
	LC_ALL=C sort -f -k1,1 -u | \
	awk -F'\t' '{printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

setup: ## Create env files, fill secrets, and optionally generate certificates
	@echo "Checking shared Docker networks (traefik_proxy, backend_net, data_net)..."
	@for pair in "traefik_proxy:10.0.0.0/16" "backend_net:10.1.0.0/16" "data_net:10.2.0.0/16"; do \
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
	@$(PYTHON_ENV_MGR) create all
	@$(PYTHON_ENV_MGR) merge-missing all
	@$(PYTHON_ENV_MGR) fill-shared-password $(if $(password),--password "$(password)",)
	@$(PYTHON_ENV_MGR) fill-secrets all

	@$(PYTHON_ENV_MGR) validate all || true
	@$(PYTHON_ENV_MGR) summary all
	@echo ""
	@read -p "Do you want to generate SSL certificates? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
	$(MAKE) cert; \
	fi
	@echo ""

passwords: ## Fill the shared password only (optional: password='…' force=1)
	@$(PYTHON_ENV_MGR) fill-shared-password \
	$(if $(password),--password "$(password)",) \
	$(if $(filter 1 true yes,$(force)),--force,)

cert: ## Generate SSL certificates for Traefik
	@echo "Detecting local IP..."
	@CURRENT_IP=$$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' \
	  | grep -v '127.0.0.1' | awk '{print $$2}' | sed 's/addr://' | head -n 1); \
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
	echo "Success: Certificates are generated in traefik/certs/"; \
	else \
	echo "Error: mkcert is not installed. Please install it first."; \
	exit 1; \
	fi

validate: ## Validate every packaged Compose project
	@set -e; for s in $(STARTUP_SERVICES); do \
	echo "Validating $$s..."; $(COMPOSE) config -q; \
	done

up: ## Validate compose, then start the packaged stack in dependency order
	@set -e; for s in $(STARTUP_SERVICES); do \
	echo "Validating $$s..."; $(COMPOSE) config -q; \
	done
	@set -e; \
	wait_ready() { \
	dep="$$1"; \
	deadline=$$((SECONDS + $(READY_TIMEOUT))); \
	echo "  Waiting until $$dep is ready..."; \
	while [ "$$SECONDS" -lt "$$deadline" ]; do \
	ids=$$(docker compose --project-directory "$$dep" -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" ps -aq); \
	if [ -z "$$ids" ]; then \
	echo "  ERROR: $$dep has no containers" >&2; \
	return 1; \
	fi; \
	ready=1; \
	for id in $$ids; do \
	state=$$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$$id"); \
	status="$${state%% *}"; \
	health="$${state#* }"; \
	if [ "$$status" != "running" ] || { [ "$$health" != "none" ] && [ "$$health" != "healthy" ]; }; then \
	ready=0; \
	fi; \
	done; \
	if [ "$$ready" -eq 1 ]; then \
	echo "  $$dep is ready"; \
	return 0; \
	fi; \
	sleep 2; \
	done; \
	echo "  ERROR: $$dep was not ready within $(READY_TIMEOUT)s" >&2; \
	return 1; \
	}; \
	for s in $(STARTUP_SERVICES); do \
	for item in $(SERVICE_DEPS) .:. ; do \
	if [ "$${item%%:*}" = "$$s" ]; then \
	wait_ready "$${item#*:}"; \
	fi; \
	done; \
	echo "Starting $$s..."; \
	$(COMPOSE) up -d; \
	done

down: ## Stop and remove containers (keeps volumes)
	@set -e; for s in $(SHUTDOWN_SERVICES); do \
	echo "Stopping $$s..."; $(COMPOSE) down; \
	done

restart: ## Restart the packaged stack
	@set -e; for s in $(STARTUP_SERVICES); do \
	echo "Restarting $$s..."; $(COMPOSE) restart; \
	done

recreate: ## Recreate the packaged stack in dependency order
	@set -e; \
	wait_ready() { \
	dep="$$1"; \
	deadline=$$((SECONDS + $(READY_TIMEOUT))); \
	echo "  Waiting until $$dep is ready..."; \
	while [ "$$SECONDS" -lt "$$deadline" ]; do \
	ids=$$(docker compose --project-directory "$$dep" -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" ps -aq); \
	if [ -z "$$ids" ]; then \
	echo "  ERROR: $$dep has no containers" >&2; \
	return 1; \
	fi; \
	ready=1; \
	for id in $$ids; do \
	state=$$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$$id"); \
	status="$${state%% *}"; \
	health="$${state#* }"; \
	if [ "$$status" != "running" ] || { [ "$$health" != "none" ] && [ "$$health" != "healthy" ]; }; then \
	ready=0; \
	fi; \
	done; \
	if [ "$$ready" -eq 1 ]; then \
	echo "  $$dep is ready"; \
	return 0; \
	fi; \
	sleep 2; \
	done; \
	echo "  ERROR: $$dep was not ready within $(READY_TIMEOUT)s" >&2; \
	return 1; \
	}; \
	for s in $(STARTUP_SERVICES); do \
	for item in $(SERVICE_DEPS) .:. ; do \
	if [ "$${item%%:*}" = "$$s" ]; then \
	wait_ready "$${item#*:}"; \
	fi; \
	done; \
	echo "Starting $$s..."; \
	$(COMPOSE) up -d --force-recreate; \
	done
