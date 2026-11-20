.PHONY: help build setup console package validate format format-check lint shell-lint test hooks check

SHELL := /bin/bash
.DEFAULT_GOAL := help

# The Rust binary in cli/ does the work. It builds with cargo on first use.
CARGO ?= cargo
CARGO_MISSING := $(if $(shell command -v $(CARGO) 2>/dev/null),,1)
MANIFEST := --manifest-path cli/Cargo.toml
DSS := cli/target/release/dss

# Optional shared password for setup:
#   make setup password='your-secure-password'
#   DSS_SHARED_PASSWORD='your-secure-password' make setup
# When omitted, setup generates a shared password on first use.
password ?=

define require-dss
	@test -x "$(DSS)" || { echo "❌ $(DSS) not built. Run 'make build' first."; exit 1; }
endef

build: ## Build the dss binary (cli/target/release/dss)
	$(if $(CARGO_MISSING),$(error cargo is required. Install: https://rustup.rs/))
	@$(CARGO) build --release $(MANIFEST)

help: ## Show this help message
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           Docker Shared Services - Management Console          ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage:"
	@echo "  make <command>"
	@echo "  $(DSS) --help"
	@echo ""
	@echo "Commands:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {print $$1 "\t" $$2}' | \
		LC_ALL=C sort -f -k1,1 -u | \
		awk -F'\t' '{printf "  %-20s %s\n", $$1, $$2}'
	@echo ""

setup: ## Setup env files and networks (optional: password='your-secure-password')
	$(require-dss)
	@$(DSS) setup $(if $(password),--password "$(password)",)

console: ## Open the management console (needs an interactive terminal)
	$(require-dss)
	@$(DSS)

package: ## Package a selected stack into dist/ (interactive wizard)
	$(require-dss)
	@$(DSS) package

validate: ## Validate all Docker Compose files and the service catalog
	$(require-dss)
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

shell-lint: ## Run shellcheck (warning level) on tracked shell scripts. Needs shellcheck.
	@echo "==> shell-lint: shellcheck"
	@command -v shellcheck >/dev/null 2>&1 || { echo "shellcheck is required. Install: https://www.shellcheck.net/"; exit 1; }
	@git ls-files -z '*.sh' | xargs -0 shellcheck -S warning

test: ## Run cargo test (unit tests plus repo rules and the 300-line limit)
	@echo "==> test: cargo test"
	@$(CARGO) test --quiet $(MANIFEST)

hooks: ## Install git hooks (pre-commit: format-check, lint, shell-lint; pre-push: test). Needs prek.
	@command -v prek >/dev/null 2>&1 || { echo "prek is required. Install: https://github.com/j178/prek"; exit 1; }
	@prek install
	@echo "✅ Git hooks installed (.pre-commit-config.yaml)"

check: format-check lint shell-lint test validate ## Run format-check, lint, shell-lint, test, and validate
