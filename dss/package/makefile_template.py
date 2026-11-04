"""Generate the Makefile of a packaged stack."""

from __future__ import annotations

from dss.core.dependencies import direct_dependencies, startup_queue

_MAKE_TARGETS = (
    "help",
    "setup",
    "passwords",
    "validate",
    "up",
    "down",
    "restart",
    "recreate",
)


def _make_lines(text: str) -> str:
    """Turn leading '>' markers into Makefile recipe tabs."""
    lines = []
    for line in text.splitlines():
        if line.startswith(">"):
            lines.append("\t" + line[1:])
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def _startup_order(services: list[str]) -> list[str]:
    """Same ordering as ``dss.cli.compose.sort_for_startup``."""
    return startup_queue(services)


def _traefik_publish_make_shell(service_var: str) -> str:
    """Shell words appended to compose when ``service_var`` is traefik and port is set."""
    return (
        f'$$(if [ "$${service_var}" = traefik ] && [ -f traefik/.env ]; then '
        "port=$$(grep -E '^TRAEFIK_HTTP_PORT=' traefik/.env | head -1 | cut -d= -f2- "
        "| tr -d '\"\\047 \\r'); "
        'if [ -n "$$port" ]; then echo -f traefik/docker-compose.publish.yml; fi; fi)'
    )


def _env_file_make_shell(service_var: str) -> str:
    """Shell words for ``--env-file``: root ``.env`` first, then ``<service>/.env``.

    Same order as ``dss.cli.compose.get_compose_cmd``, so a service value overrides a root value.
    """
    return (
        "$$(if [ -f .env ]; then echo --env-file .env; fi) "
        f'$$(if [ -f "$${service_var}/.env" ]; then echo --env-file "$${service_var}/.env"; fi)'
    )


_QUEUE_SHELL = r"""
>@set -e; \
>wait_ready() { \
>dep="$$1"; \
>deadline=$$((SECONDS + $(READY_TIMEOUT))); \
>echo "  Waiting until $$dep is ready..."; \
>while [ "$$SECONDS" -lt "$$deadline" ]; do \
>ids=$$(docker compose --project-directory "$$dep" __DEP_ENV_FILES__ -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" __TRAEFIK_DEP_PUBLISH__ ps -aq); \
>if [ -z "$$ids" ]; then \
>echo "  ERROR: $$dep has no containers" >&2; \
>return 1; \
>fi; \
>ready=1; \
>for id in $$ids; do \
>set -- $$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.State.ExitCode}} {{or .HostConfig.RestartPolicy.Name "no"}}' "$$id"); \
>if [ "$${1:-}" = exited ] && [ "$${3:-}" = 0 ] && [ "$${4:-}" = no ]; then \
>continue; \
>fi; \
>if [ "$${1:-}" != running ] || { [ "$${2:-}" != none ] && [ "$${2:-}" != healthy ]; }; then \
>ready=0; \
>fi; \
>done; \
>if [ "$$ready" -eq 1 ]; then \
>echo "  $$dep is ready"; \
>return 0; \
>fi; \
>sleep 2; \
>done; \
>echo "  ERROR: $$dep was not ready within $(READY_TIMEOUT)s" >&2; \
>return 1; \
>}; \
>for s in $(STARTUP_SERVICES); do \
>for item in $(SERVICE_DEPS) .:. ; do \
>if [ "$${item%%:*}" = "$$s" ]; then \
>wait_ready "$${item#*:}"; \
>fi; \
>done; \
>echo "Starting $$s..."; \
>$(COMPOSE) up -d__FLAGS__; \
>done
"""


def _queue_recipe(flags: str) -> str:
    suffix = f" {flags}" if flags else ""
    dep_publish = _traefik_publish_make_shell("dep")
    text = (
        _QUEUE_SHELL.lstrip("\n")
        .replace("__FLAGS__", suffix)
        .replace("__TRAEFIK_DEP_PUBLISH__", dep_publish)
        .replace("__DEP_ENV_FILES__", _env_file_make_shell("dep"))
    )
    return _make_lines(text)


def _dependency_tokens(services: list[str]) -> str:
    """``consumer:backend`` pairs, in startup order, for the packaged Makefile."""
    selected = set(services)
    tokens: list[str] = []
    for service in _startup_order(services):
        for backend in direct_dependencies(service, selected):
            tokens.append(f"{service}:{backend}")
    return " ".join(tokens)


def render_makefile(services: list[str]) -> str:
    startup = _startup_order(services)
    traefik_publish = _traefik_publish_make_shell("s")
    env_files = _env_file_make_shell("s")
    dozzle = ""
    if "dozzle" in services:
        dozzle = _make_lines(
            r"""
>@echo "Checking Dozzle users file (dozzle/data/users.yml)..."
>@mkdir -p dozzle/data
>@if [[ -d "dozzle/data/users.yml" ]]; then \
>echo "  dozzle/data/users.yml is a directory -> removing and regenerating..."; \
>rm -rf dozzle/data/users.yml; \
>fi; \
>if [[ ! -f "dozzle/data/users.yml" ]]; then \
>DOZZLE_PW="$${DSS_SHARED_PASSWORD:-}"; \
>if [[ -z "$$DOZZLE_PW" && -f .env ]]; then \
>DOZZLE_PW=$$(grep -E '^DSS_SHARED_PASSWORD=' .env | head -1 | cut -d= -f2-); \
>fi; \
>if [[ -z "$$DOZZLE_PW" || "$$DOZZLE_PW" == "Password102!" ]]; then \
>echo "  ERROR: DSS_SHARED_PASSWORD is missing or still Password102!." >&2; \
>echo "  Run make setup before generating Dozzle users." >&2; \
>exit 1; \
>fi; \
>echo "  dozzle/data/users.yml not found -> generating admin (shared password)..."; \
>docker run --rm -i amir20/dozzle generate admin \
>  --password "$$DOZZLE_PW" \
>  --email admin@example.com \
>  --name "Admin" > dozzle/data/users.yml; \
>else \
>echo "  dozzle/data/users.yml already exists"; \
>fi
"""
        )
    body = f"""\
.PHONY: {" ".join(_MAKE_TARGETS)}

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON_ENV_MGR := uv run --frozen --no-dev python -m dss.cli.env
PYTHON_STACK := uv run --frozen --no-dev python -m dss.core.stack
# DSS_NAME in the root .env prefixes every Compose project and network.
DSS_NAME = $(shell $(PYTHON_STACK) name 2>/dev/null)
password ?=

# One compose project per service, like dss/cli/service.py: --project-directory
# resolves ./ paths inside <service>/. The root .env, then <service>/.env, feed
# interpolation, so DOMAIN in the root .env sets every hostname.
STARTUP_SERVICES := {" ".join(startup)}
SHUTDOWN_SERVICES := {" ".join(reversed(startup))}
# consumer:backend. up/recreate wait until each backend is running and healthy.
SERVICE_DEPS := {_dependency_tokens(services)}
READY_TIMEOUT ?= 300
COMPOSE = docker compose $(if $(DSS_NAME),-p $(DSS_NAME)-$$s) --project-directory $$s {env_files} -f docker-compose.shared.yml -f $$s/docker-compose.yml {traefik_publish}
"""
    body += _make_lines(
        r"""
help: ## Show this help message
>@echo "Packaged Docker Shared Services stack"
>@echo ""
>@echo "Usage:"
>@echo "  make <command>"
>@echo ""
>@echo "Commands:"
>@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
>awk 'BEGIN {FS = ":.*?## "} {print $$1 "\t" $$2}' | \
>LC_ALL=C sort -f -k1,1 -u | \
>awk -F'\t' '{printf "  %-20s %s\n", $$1, $$2}'
>@echo ""

setup: ## Create env files and fill secrets
>@echo "Checking shared Docker networks (names and subnets from DSS_NAME and DSS_SUBNET_BASE)..."
>@pairs=$$($(PYTHON_STACK)) || exit 1; \
>for pair in $$pairs; do \
>name=$${pair%%:*}; subnet=$${pair#*:}; \
>if docker network inspect $$name >/dev/null 2>&1; then \
>echo "  $$name: already exists"; \
>elif docker network create $$name --subnet $$subnet --driver bridge >/dev/null 2>&1; then \
>echo "  $$name: created ($$subnet)"; \
>elif docker network create $$name --driver bridge >/dev/null 2>&1; then \
>echo "  $$name: created (auto subnet; $$subnet overlapped another Docker pool)"; \
>else \
>echo "  ERROR: could not create $$name" >&2; exit 1; \
>fi; \
>done
>@$(PYTHON_ENV_MGR) create all
>@$(PYTHON_ENV_MGR) merge-missing all
>@$(PYTHON_ENV_MGR) fill-shared-password $(if $(password),--password "$(password)",)
>@$(PYTHON_ENV_MGR) fill-secrets all
"""
    )
    body += dozzle
    body += _make_lines(
        r"""
>@$(PYTHON_ENV_MGR) validate all || true
>@$(PYTHON_ENV_MGR) summary all
>@echo ""

passwords: ## Fill the shared password only (optional: password='…' force=1)
>@$(PYTHON_ENV_MGR) fill-shared-password \
>$(if $(password),--password "$(password)",) \
>$(if $(filter 1 true yes,$(force)),--force,)

validate: ## Validate every packaged Compose project
>@set -e; for s in $(STARTUP_SERVICES); do \
>echo "Validating $$s..."; $(COMPOSE) config -q; \
>done

up: ## Validate compose, then start the packaged stack in dependency order
>@set -e; for s in $(STARTUP_SERVICES); do \
>echo "Validating $$s..."; $(COMPOSE) config -q; \
>done
"""
    )
    body += _queue_recipe("")
    body += _make_lines(
        r"""
down: ## Stop and remove containers (keeps volumes)
>@set -e; for s in $(SHUTDOWN_SERVICES); do \
>echo "Stopping $$s..."; $(COMPOSE) down; \
>done

restart: ## Restart the packaged stack
>@set -e; for s in $(STARTUP_SERVICES); do \
>echo "Restarting $$s..."; $(COMPOSE) restart; \
>done

recreate: ## Recreate the packaged stack in dependency order
"""
    )
    body += _queue_recipe("--force-recreate")
    return body
