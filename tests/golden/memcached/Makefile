.PHONY: help setup passwords validate up down restart recreate

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON_ENV_MGR := uv run --frozen --no-dev python -m dss.cli.env
PYTHON_STACK := uv run --frozen --no-dev python -m dss.core.stack
# SANDBOX_NAME in the root .env prefixes every Compose project and network.
SANDBOX_NAME = $(shell $(PYTHON_STACK) name 2>/dev/null)
password ?=

# One compose project per service, like dss/cli/service.py: --project-directory
# resolves ./ paths inside <service>/. The root .env, then <service>/.env, feed
# interpolation, so DOMAIN in the root .env sets every hostname.
STARTUP_SERVICES := memcached
SHUTDOWN_SERVICES := memcached
# consumer:backend. up/recreate wait until each backend is running and healthy.
SERVICE_DEPS := 
READY_TIMEOUT ?= 300
COMPOSE = docker compose $(if $(SANDBOX_NAME),-p $(SANDBOX_NAME)-$$s) --project-directory $$s $$(if [ -f .env ]; then echo --env-file .env; fi) $$(if [ -f "$$s/.env" ]; then echo --env-file "$$s/.env"; fi) -f docker-compose.shared.yml -f $$s/docker-compose.yml $$(if [ "$$s" = traefik ] && [ -f traefik/.env ]; then port=$$(grep -E '^TRAEFIK_HTTP_PORT=' traefik/.env | head -1 | cut -d= -f2- | tr -d '"\047 \r'); if [ -n "$$port" ]; then echo -f traefik/docker-compose.publish.yml; fi; fi)

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

setup: ## Create env files and fill secrets
	@echo "Checking shared Docker networks (names and subnets from SANDBOX_NAME and SANDBOX_SUBNET_BASE)..."
	@pairs=$$($(PYTHON_STACK)) || exit 1; \
	for pair in $$pairs; do \
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

passwords: ## Fill the shared password only (optional: password='…' force=1)
	@$(PYTHON_ENV_MGR) fill-shared-password \
	$(if $(password),--password "$(password)",) \
	$(if $(filter 1 true yes,$(force)),--force,)

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
	ids=$$(docker compose --project-directory "$$dep" $$(if [ -f .env ]; then echo --env-file .env; fi) $$(if [ -f "$$dep/.env" ]; then echo --env-file "$$dep/.env"; fi) -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" $$(if [ "$$dep" = traefik ] && [ -f traefik/.env ]; then port=$$(grep -E '^TRAEFIK_HTTP_PORT=' traefik/.env | head -1 | cut -d= -f2- | tr -d '"\047 \r'); if [ -n "$$port" ]; then echo -f traefik/docker-compose.publish.yml; fi; fi) ps -aq); \
	if [ -z "$$ids" ]; then \
	echo "  ERROR: $$dep has no containers" >&2; \
	return 1; \
	fi; \
	ready=1; \
	for id in $$ids; do \
	set -- $$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.State.ExitCode}} {{or .HostConfig.RestartPolicy.Name "no"}}' "$$id"); \
	if [ "$${1:-}" = exited ] && [ "$${3:-}" = 0 ] && [ "$${4:-}" = no ]; then \
	continue; \
	fi; \
	if [ "$${1:-}" != running ] || { [ "$${2:-}" != none ] && [ "$${2:-}" != healthy ]; }; then \
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
	ids=$$(docker compose --project-directory "$$dep" $$(if [ -f .env ]; then echo --env-file .env; fi) $$(if [ -f "$$dep/.env" ]; then echo --env-file "$$dep/.env"; fi) -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" $$(if [ "$$dep" = traefik ] && [ -f traefik/.env ]; then port=$$(grep -E '^TRAEFIK_HTTP_PORT=' traefik/.env | head -1 | cut -d= -f2- | tr -d '"\047 \r'); if [ -n "$$port" ]; then echo -f traefik/docker-compose.publish.yml; fi; fi) ps -aq); \
	if [ -z "$$ids" ]; then \
	echo "  ERROR: $$dep has no containers" >&2; \
	return 1; \
	fi; \
	ready=1; \
	for id in $$ids; do \
	set -- $$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.State.ExitCode}} {{or .HostConfig.RestartPolicy.Name "no"}}' "$$id"); \
	if [ "$${1:-}" = exited ] && [ "$${3:-}" = 0 ] && [ "$${4:-}" = no ]; then \
	continue; \
	fi; \
	if [ "$${1:-}" != running ] || { [ "$${2:-}" != none ] && [ "$${2:-}" != healthy ]; }; then \
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
