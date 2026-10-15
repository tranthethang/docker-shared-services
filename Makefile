.PHONY: help setup passwords ps health remove-all prune remove-config info up down stop restart logs cert validate manage tui package sync format format-check lint typecheck test test-update check hooks

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Python runs through uv on the locked Python 3.12 environment (without dev tools).
UV ?= uv
UV_MISSING := $(if $(shell command -v $(UV) 2>/dev/null),,1)
UV_RUN = $(if $(UV_MISSING),$(error uv is required. Install: https://docs.astral.sh/uv/),$(UV) run --frozen --no-dev)
PY = $(UV_RUN) python
PY_TUI = $(UV_RUN) --group tui python

# Python managers
PYTHON_ENV_MGR = $(PY) -m dss.cli.env
PYTHON_SVC_MGR = $(PY) -m dss.cli.service

# Optional shared password for setup/passwords targets:
#   make setup password='your-secure-password'
#   DSS_SHARED_PASSWORD='your-secure-password' make setup
#   make passwords password='your-secure-password'
# When omitted, setup generates a shared password on first use.
password ?=

# -f arguments for every service compose file, shared networks first.
COMPOSE_FILES = -f docker-compose.shared.yml \
	$(shell find . -maxdepth 2 -name "docker-compose.yml" -not -path "./docker-compose.shared.yml" | LC_ALL=C sort | sed 's|^./|-f |')
# Dynamic DOCKER_COMPOSE command that includes all services
DOCKER_COMPOSE = docker compose $(COMPOSE_FILES)

# Shared bridge networks (name:subnet). Bridges cannot share one CIDR; adjacent /16s in 10/8.
SHARED_NETWORKS = traefik_proxy:10.0.0.0/16 backend_net:10.1.0.0/16 data_net:10.2.0.0/16

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

setup: ## Setup env files, networks, certs (optional: password='your-secure-password')
	@echo "Checking shared Docker networks (traefik_proxy, backend_net, data_net)..."
	@scripts/ensure-networks.sh $(SHARED_NETWORKS)
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
	@# ONE shared password for every placeholder password (DB/Redis/MinIO/…).
	@# Override: make setup password='your-secure-password'  OR  DSS_SHARED_PASSWORD='…' make setup
	@# Unique secrets (Garage, Woodpecker agent) are filled next and stay distinct.
	@$(PYTHON_ENV_MGR) fill-shared-password $(if $(password),--password "$(password)",)
	@$(PYTHON_ENV_MGR) fill-secrets all
	@echo "Checking Dozzle users file (dozzle/data/users.yml)..."
	@scripts/ensure-dozzle-users.sh dozzle/data/users.yml .env
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
	@scripts/gen-certs.sh traefik/certs

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
	@if [ ! -t 0 ] || [ ! -t 1 ]; then \
		echo "❌ make tui needs an interactive terminal (TTY)."; \
		echo "   Use make manage / make up / make ps / make logs instead."; \
		exit 1; \
	fi
	@$(PY_TUI) -m dss.tui

package: ## Package a selected stack into dist/ (requires uv + interactive terminal)
	@if [ ! -t 0 ] || [ ! -t 1 ]; then \
		echo "❌ make package needs an interactive terminal (TTY)."; \
		exit 1; \
	fi
	@$(PY_TUI) -m dss.package.wizard

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
	@scripts/remove-all.sh $(COMPOSE_FILES)

prune: ## Remove unused Docker resources
	@echo "Pruning Docker resources..."
	@docker system prune -f --volumes
	@echo "✅ Pruned"

remove-config: ## Remove all .env files that have a matching .env.example
	@scripts/remove-config.sh .

info: ## Show service information and access URLs
	@$(PY) -m dss.cli.info

validate: ## Validate all Docker Compose files
	@echo "==> validate"
	@$(PYTHON_SVC_MGR) --validate-compose

sync: ## Install Python tooling deps with uv (ruff, yamlfix, mdformat, …)
	@$(UV) sync --group dev
	@echo "✅ uv sync complete"

format: ## Format YAML, JSON, Markdown, Python, and .env.example files
	@$(UV) sync --group dev --quiet
	@PYTHONUNBUFFERED=1 $(UV) run python tools/format_repo.py

format-check: ## Check formatting without writing changes
	@echo "==> format-check"
	@$(UV) sync --group dev --quiet
	@PYTHONUNBUFFERED=1 $(UV) run python tools/format_repo.py --check

SHELL_SCRIPTS = $(shell find . -name '*.sh' -not -path './.venv/*' -not -path './dist/*' -not -path './.git/*' -not -path '*/data/*')

lint: ## Run ruff, import-linter, the file-size check, shellcheck, and shfmt
	@$(UV) sync --group dev --quiet
	@echo "==> lint: ruff"
	@$(UV) run ruff check dss tools tests
	@echo "==> lint: import-linter"
	@$(UV) run lint-imports
	@echo "==> lint: file size"
	@$(UV) run python tools/check_file_size.py
	@echo "==> lint: shellcheck"
	@$(UV) run shellcheck -x $(SHELL_SCRIPTS)
	@echo "==> lint: shfmt"
	@$(UV) run shfmt -d -i 2 -ci $(SHELL_SCRIPTS)

typecheck: ## Run mypy (strict) on dss/ and tools/
	@# The tui group installs textual so its widgets type-check as real classes, not Any.
	@echo "==> typecheck: mypy (strict)"
	@$(UV) sync --group dev --group tui --quiet
	@$(UV) run --group tui mypy dss tools

COVERAGE_FLOOR_CORE = 80

test: ## Run pytest with a dss/ coverage report; dss/core must reach the coverage floor
	@echo "==> test: pytest"
	@$(UV) sync --group dev --quiet
	@$(UV) run pytest --cov=dss --cov-report=term-missing
	@echo "==> test: coverage floor dss/core >= $(COVERAGE_FLOOR_CORE)%"
	@$(UV) run coverage report --include='dss/core/*' --fail-under=$(COVERAGE_FLOOR_CORE)

test-update: ## Regenerate tests/golden snapshots
	@$(UV) sync --group dev --quiet
	@GOLDEN_UPDATE=1 $(UV) run pytest

hooks: ## Install git hooks (pre-commit: format-check, lint, typecheck; pre-push: test)
	@$(UV) sync --group dev --quiet
	@$(UV) run prek install
	@echo "✅ Git hooks installed (.pre-commit-config.yaml)"

check: format-check lint typecheck test validate ## Run format-check, lint, typecheck, test, and validate
