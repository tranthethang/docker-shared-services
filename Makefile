.PHONY: help build setup passwords ps health remove-all prune remove-config info up down stop restart logs validate manage tui package format format-check lint test check hooks

SHELL := /bin/bash
.DEFAULT_GOAL := help

# The Rust binary in cli/ does the work. It builds with cargo on first use.
CARGO ?= cargo
CARGO_MISSING := $(if $(shell command -v $(CARGO) 2>/dev/null),,1)
MANIFEST := --manifest-path cli/Cargo.toml
DSS := cli/target/release/dss

# Optional shared password for setup/passwords targets:
#   make setup password='your-secure-password'
#   DSS_SHARED_PASSWORD='your-secure-password' make setup
#   make passwords password='your-secure-password'
# When omitted, setup generates a shared password on first use.
password ?=

$(DSS): $(wildcard cli/src/*.rs cli/src/*/*.rs) cli/Cargo.toml cli/Cargo.lock cli/service_catalog.json
	$(if $(CARGO_MISSING),$(error cargo is required. Install: https://rustup.rs/))
	@$(CARGO) build --release --quiet $(MANIFEST)

build: $(DSS) ## Build the dss binary (cli/target/release/dss)

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

setup: $(DSS) ## Setup env files and networks (optional: password='your-secure-password')
	@$(DSS) setup $(if $(password),--password "$(password)",)

passwords: $(DSS) ## Apply ONE shared password to all services (optional: password='…' force=1)
	@$(DSS) env passwords \
		$(if $(password),--password "$(password)",) \
		$(if $(filter 1 true yes,$(force)),--force,)

up: $(DSS) ## Start services (usage: make up [service=pgvector]; no service opens the dashboard)
	@$(DSS) $(if $(service),up --service $(service),)

down: $(DSS) ## Stop and remove services (usage: make down [service=pgvector])
	@$(DSS) $(if $(service),down --service $(service),)

stop: $(DSS) ## Stop services (usage: make stop [service=pgvector])
	@$(DSS) $(if $(service),stop --service $(service),)

restart: $(DSS) ## Restart services (usage: make restart [service=pgvector])
	@$(DSS) $(if $(service),restart --service $(service),)

manage: $(DSS) ## Interactive multi-select manager (space to select, m to apply)
	@$(DSS)

tui: $(DSS) ## Open the ratatui dashboard (needs an interactive terminal)
	@$(DSS)

package: $(DSS) ## Package a selected stack into dist/ (interactive wizard)
	@$(DSS) package

logs: $(DSS) ## Show logs (usage: make logs service=pgvector)
	@$(DSS) logs --service "$(service)"

ps: $(DSS) ## Show status of all running services
	@$(DSS) ps

health: $(DSS) ## Check health status of services (usage: make health [service=pgvector])
	@$(DSS) health $(if $(service),--service $(service),)

remove-all: $(DSS) ## Remove all containers and volumes (⚠️ DANGER: Removes all data)
	@$(DSS) teardown

prune: $(DSS) ## Remove unused Docker resources
	@$(DSS) prune

remove-config: $(DSS) ## Remove all .env files that have a matching .env.example
	@$(DSS) remove-config

info: $(DSS) ## Show service information and access URLs
	@$(DSS) info

validate: $(DSS) ## Validate all Docker Compose files and the service catalog
	@echo "==> validate"
	@$(DSS) validate

format: ## Format the Rust sources
	@$(CARGO) fmt $(MANIFEST)

format-check: ## Check Rust formatting without writing changes
	@echo "==> format-check"
	@$(CARGO) fmt --check $(MANIFEST)

lint: ## Run clippy with warnings as errors
	@echo "==> lint: clippy"
	@$(CARGO) clippy $(MANIFEST) --all-targets -- -D warnings

test: ## Run cargo test (unit tests plus repo rules and the 300-line limit)
	@echo "==> test: cargo test"
	@$(CARGO) test --quiet $(MANIFEST)

hooks: ## Install git hooks (pre-commit: format-check, lint; pre-push: test). Needs prek.
	@command -v prek >/dev/null 2>&1 || { echo "prek is required. Install: https://github.com/j178/prek"; exit 1; }
	@prek install
	@echo "✅ Git hooks installed (.pre-commit-config.yaml)"

check: format-check lint test validate ## Run format-check, lint, test, and validate
