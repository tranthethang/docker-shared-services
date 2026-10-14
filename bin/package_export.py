"""Export a selected service stack into a runnable dist tree.

This module does not import Textual or the Docker SDK. The wizard calls
``export_stack`` only after the user confirms.
"""

from __future__ import annotations

import ast
import os
import re
import shutil
from pathlib import Path

from config import (
    AUTH_OPT_IN_UI_SERVICES,
    AUTO_GENERATED_SECRETS,
    PACKAGE_REQUIRES,
    SERVICE_INFO_VARS,
    SERVICES,
    SHARED_PASSWORD_KEYS,
    SHARED_PASSWORD_TEMPLATES,
    START_ORDER,
    STRONG_PASSWORD_REQUIRED,
    VALIDATION_RULES,
    direct_dependencies,
    startup_queue,
)
from service_catalog import CATEGORIES, load_catalog

_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_BANNER_SEP = re.compile(r"^# ={10,}\s*$")

# Banner title (text before " - ") -> service directory. Longest match wins.
_BANNER_TO_SERVICE = {
    "TRAEFIK": "traefik",
    "POSTGRES": "postgres",
    "PGVECTOR": "pgvector",
    "MySQL 8": "mysql8",
    "MARIADB": "mariadb",
    "MONGODB": "mongodb",
    "REDIS INSIGHT": "redisinsight",
    "REDIS": "redis",
    "RABBITMQ": "rabbitmq",
    "MEMCACHED": "memcached",
    "MAILPIT": "mailpit",
    "MINIO": "minio",
    "ADMINER": "adminer",
    "DOCKGE": "dockge",
    "PORTAINER": "portainer",
    "GITEA": "gitea",
    "SONARQUBE": "sonarqube",
    "JENKINS": "jenkins",
    "CONCOURSE": "concourse",
    "ACT RUNNER": "act_runner",
    "OTEL": "otel",
    "n8n": "n8n",
    "Node-RED": "node-red",
    "DOZZLE": "dozzle",
    "CHROMADB": "chromadb",
    "QDRANT": "qdrant",
    "APPSMITH": "appsmith",
    "TEMPORAL": "temporal",
    "POCKETBASE": "pocketbase",
    "SUPABASE": "supabase",
    "CENTRIFUGO": "centrifugo",
    "GOTENBERG": "gotenberg",
    "MERMAID": "mermaid-live-editor",
    "HASURA": "hasura",
}
_BANNER_KEYS = sorted(_BANNER_TO_SERVICE, key=len, reverse=True)

_SKIP_DIR_NAMES = {"data", "volumes", "__pycache__", ".venv"}
_MAKE_TARGETS = ("help", "setup", "passwords", "cert", "up", "down", "restart", "recreate")
_PACKAGE_PYPROJECT = """[project]
name = "docker-shared-services"
version = "0.1.0"
description = "Packaged Docker Shared Services stack"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false
"""
_PACKAGE_GITIGNORE = """# Environment & secrets
.env
.env.local
.env.production
.env.*.local
.env.test
!.env.example
!**/.env.example

# Runtime data
**/data/
**/*_data/
dozzle/data/
supabase/volumes/db/data/
supabase/volumes/storage/

# Certificates
traefik/certs/*.crt
traefik/certs/*.key
**/server.crt
**/server.key

# Logs, temp, OS
*.log
logs/
*.tmp
tmp/
temp/
.DS_Store
Thumbs.db

# Python
.venv/
**/__pycache__/
*.py[cod]
"""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_stack_name(name: str) -> str:
    """Return ``name`` when it matches ``^[a-z][a-z0-9]*(-[a-z0-9]+)*$`` and length 1–48."""
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name) or not 1 <= len(name) <= 48:
        raise ValueError(
            "Stack name must match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ and be 1-48 characters."
        )
    return name


def service_requires_traefik(service: str, root: Path | None = None) -> bool:
    compose = (root or repo_root()) / service / "docker-compose.yml"
    if not compose.is_file():
        return False
    return "traefik.enable=true" in compose.read_text(encoding="utf-8")


def resolve_services(selected: list[str], root: Path | None = None) -> list[str]:
    """Transitive ``PACKAGE_REQUIRES`` plus traefik, ordered as ``SERVICES``."""
    unknown = [name for name in selected if name not in SERVICES]
    if unknown:
        raise ValueError(f"Unknown services: {', '.join(unknown)}")
    if not selected:
        raise ValueError("No services selected.")

    root = root or repo_root()
    chosen = set(selected)
    changed = True
    while changed:
        changed = False
        for backend, consumers in PACKAGE_REQUIRES.items():
            if backend not in chosen and chosen.intersection(consumers):
                chosen.add(backend)
                changed = True
        if "traefik" not in chosen:
            for service in list(chosen):
                if service_requires_traefik(service, root):
                    chosen.add("traefik")
                    changed = True
                    break
    return [name for name in SERVICES if name in chosen]


def partition_selection(
    selected: list[str], root: Path | None = None
) -> tuple[list[str], list[str]]:
    """Return (checked services, dependency services added), both in ``SERVICES`` order."""
    resolved = resolve_services(selected, root)
    selected_set = set(selected)
    checked = [name for name in resolved if name in selected_set]
    added = [name for name in resolved if name not in selected_set]
    return checked, added


def _banner_service(title: str) -> str | None:
    for key in _BANNER_KEYS:
        if title == key or title.startswith(key + " "):
            return _BANNER_TO_SERVICE[key]
    return None


def _is_sep(line: str) -> bool:
    return _BANNER_SEP.match(line.rstrip("\n")) is not None


def _header_close(lines: list[str], start: int) -> int | None:
    """Index of the closing separator when ``start`` opens a banner header."""
    if start >= len(lines) or not _is_sep(lines[start]):
        return None
    saw_comment = False
    index = start + 1
    while index < len(lines) and not _is_sep(lines[index]):
        stripped = lines[index].strip()
        if stripped == "":
            index += 1
            continue
        if stripped.startswith("#"):
            saw_comment = True
            index += 1
            continue
        return None
    if saw_comment and index < len(lines):
        return index
    return None


def _banner_title(lines: list[str], start: int, close: int) -> str:
    for line in lines[start + 1 : close]:
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped[1:].strip()
            return text.split(" - ", 1)[0].strip()
    return ""


def _banner_spans(lines: list[str]) -> list[tuple[int, int, str]]:
    """Each span is (start, next_start, title) covering a banner and its body."""
    headers: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        close = _header_close(lines, index)
        if close is not None:
            headers.append((index, _banner_title(lines, index, close)))
            index = close + 1
            continue
        index += 1
    spans: list[tuple[int, int, str]] = []
    for position, (start, title) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        spans.append((start, end, title))
    return spans


def unmapped_env_banners(text: str) -> list[str]:
    """Banner titles the service map does not name. These are dropped from the package."""
    lines = text.splitlines(keepends=True)
    dropped: list[str] = []
    for _start, _end, title in _banner_spans(lines):
        if title.startswith("SHARED PASSWORD") or title == "Security Notes":
            continue
        if _banner_service(title) is None:
            dropped.append(title)
    return dropped


def filter_env_example(text: str, services: list[str]) -> str:
    """Keep the preamble, shared-password block, selected service blocks, and Security Notes."""
    lines = text.splitlines(keepends=True)
    spans = _banner_spans(lines)
    selected = set(services)
    if not spans:
        return text

    shared_end = 0
    for start, end, title in spans:
        if title.startswith("SHARED PASSWORD"):
            shared_end = end
            break
    parts = ["".join(lines[:shared_end])]
    for start, end, title in spans:
        if title.startswith("SHARED PASSWORD"):
            continue
        if title == "Security Notes":
            parts.append("".join(lines[start:]))
            break
        service = _banner_service(title)
        if service is not None and service in selected:
            parts.append("".join(lines[start:end]))
    rendered = "".join(parts)
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def _render_str_list(items: list[str]) -> str:
    if not items:
        return "[]"
    body = ",\n".join(f"    {item!r}" for item in items)
    return "[\n" + body + ",\n]"


def _render_dict_of_str_lists(mapping: dict[str, list[str]]) -> str:
    if not mapping:
        return "{}"
    lines = ["{"]
    for key, values in mapping.items():
        inner = ", ".join(repr(value) for value in values)
        lines.append(f"    {key!r}: [{inner}],")
    lines.append("}")
    return "\n".join(lines)


def _render_validation(mapping: dict[str, list[str]]) -> str:
    if not mapping:
        return "{}"
    lines = ["{"]
    for key, values in mapping.items():
        inner = ", ".join(repr(value) for value in values)
        lines.append(f"    {key!r}: [{inner}],")
    lines.append("}")
    return "\n".join(lines)


def _render_auto_secrets(mapping: dict[str, dict[str, tuple[str, int]]]) -> str:
    if not mapping:
        return "{}"
    lines = ["{"]
    for service, secrets in mapping.items():
        lines.append(f"    {service!r}: {{")
        for key, (method, nbytes) in secrets.items():
            lines.append(f"        {key!r}: ({method!r}, {nbytes}),")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _render_templates(mapping: dict[tuple[str, str], str]) -> str:
    if not mapping:
        return "{}"
    lines = ["{"]
    for (service, variable), value in mapping.items():
        lines.append(f"    ({service!r}, {variable!r}): {value!r},")
    lines.append("}")
    return "\n".join(lines)


def _filter_shared_password_keys(services: set[str]) -> dict[str, list[str]]:
    packaged_vars: set[str] = set()
    for service, keys in SHARED_PASSWORD_KEYS.items():
        if service in services:
            packaged_vars.update(keys)
    filtered: dict[str, list[str]] = {}
    dot_keys = [
        key
        for key in SHARED_PASSWORD_KEYS.get(".", [])
        if key == "DSS_SHARED_PASSWORD" or key in packaged_vars
    ]
    if "." in SHARED_PASSWORD_KEYS:
        filtered["."] = dot_keys
    for service, keys in SHARED_PASSWORD_KEYS.items():
        if service in services:
            filtered[service] = list(keys)
    return filtered


def _filter_auto_secrets(services: set[str]) -> dict[str, dict[str, tuple[str, int]]]:
    packaged_keys: set[str] = set()
    for service, secrets in AUTO_GENERATED_SECRETS.items():
        if service in services:
            packaged_keys.update(secrets)
    filtered: dict[str, dict[str, tuple[str, int]]] = {}
    dot = AUTO_GENERATED_SECRETS.get(".")
    if dot is not None:
        kept = {key: value for key, value in dot.items() if key in packaged_keys}
        if kept:
            filtered["."] = kept
    for service, secrets in AUTO_GENERATED_SECRETS.items():
        if service in services:
            filtered[service] = dict(secrets)
    return filtered


def _filter_templates(services: set[str]) -> dict[tuple[str, str], str]:
    packaged_vars = {
        variable for (service, variable) in SHARED_PASSWORD_TEMPLATES if service in services
    }
    return {
        key: value
        for key, value in SHARED_PASSWORD_TEMPLATES.items()
        if key[0] in services or (key[0] == "." and key[1] in packaged_vars)
    }


def _replace_statements(source: str, replacements: dict[str, str]) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        if target not in replacements or node.end_lineno is None:
            continue
        text = replacements[target]
        if not text.endswith("\n"):
            text += "\n"
        spans.append((node.lineno, node.end_lineno, text))
    for start, end, text in sorted(spans, reverse=True):
        lines[start - 1 : end] = [text]
    return "".join(lines)


def filter_config_source(source: str, services: list[str]) -> str:
    """Source ``config.py`` with ``SERVICES`` and related maps limited to ``services``."""
    selected = set(services)
    ordered = [name for name in SERVICES if name in selected]
    validation = {name: VALIDATION_RULES[name] for name in VALIDATION_RULES if name in selected}
    info = {name: SERVICE_INFO_VARS[name] for name in SERVICE_INFO_VARS if name in selected}
    strong = {
        name: STRONG_PASSWORD_REQUIRED[name]
        for name in STRONG_PASSWORD_REQUIRED
        if name in selected
    }
    replacements = {
        "SERVICES": "SERVICES = " + _render_str_list(ordered),
        "START_ORDER": "START_ORDER = "
        + _render_str_list([name for name in START_ORDER if name in selected]),
        "VALIDATION_RULES": "VALIDATION_RULES = " + _render_validation(validation),
        "AUTO_GENERATED_SECRETS": "AUTO_GENERATED_SECRETS = "
        + _render_auto_secrets(_filter_auto_secrets(selected)),
        "AUTH_OPT_IN_UI_SERVICES": "AUTH_OPT_IN_UI_SERVICES = "
        + _render_str_list([name for name in AUTH_OPT_IN_UI_SERVICES if name in selected]),
        "SHARED_PASSWORD_KEYS": "SHARED_PASSWORD_KEYS: dict[str, list[str]] = "
        + _render_dict_of_str_lists(_filter_shared_password_keys(selected)),
        "SHARED_PASSWORD_TEMPLATES": "SHARED_PASSWORD_TEMPLATES: dict[tuple[str, str], str] = "
        + _render_templates(_filter_templates(selected)),
        "SERVICE_INFO_VARS": "SERVICE_INFO_VARS = " + _render_dict_of_str_lists(info),
        "STRONG_PASSWORD_REQUIRED": "STRONG_PASSWORD_REQUIRED = "
        + _render_dict_of_str_lists(strong),
    }
    return _replace_statements(source, replacements)


def _skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.endswith("_data")


def _skip_file(service: str, relative: Path) -> bool:
    if relative.name == ".env":
        return True
    return (
        service == "traefik"
        and relative.parent.as_posix() == "certs"
        and relative.suffix in {".crt", ".key"}
    )


def _link_escapes(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return True
    return False


def _copy_tree(src: Path, dst: Path, service: str, root: Path, relative: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        rel = relative / entry.name
        if entry.is_symlink():
            if _link_escapes(entry, root):
                continue
            (dst / entry.name).symlink_to(os.readlink(entry))
            continue
        if entry.is_dir():
            if _skip_dir(entry.name):
                continue
            _copy_tree(entry, dst / entry.name, service, root, rel)
            continue
        if entry.is_file() and not _skip_file(service, rel):
            shutil.copy2(entry, dst / entry.name)


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
    """Same ordering as ``service_manager.sort_for_startup``."""
    return startup_queue(services)


_QUEUE_SHELL = r"""
>@set -e; \
>wait_ready() { \
>dep="$$1"; \
>deadline=$$((SECONDS + $(READY_TIMEOUT))); \
>echo "  Waiting until $$dep is ready..."; \
>while [ "$$SECONDS" -lt "$$deadline" ]; do \
>ids=$$(docker compose --project-directory "$$dep" -f docker-compose.shared.yml -f "$$dep/docker-compose.yml" ps -aq); \
>if [ -z "$$ids" ]; then \
>echo "  ERROR: $$dep has no containers" >&2; \
>return 1; \
>fi; \
>ready=1; \
>for id in $$ids; do \
>state=$$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$$id"); \
>status="$${state%% *}"; \
>health="$${state#* }"; \
>if [ "$$status" != "running" ] || { [ "$$health" != "none" ] && [ "$$health" != "healthy" ]; }; then \
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
    text = _QUEUE_SHELL.lstrip("\n").replace("__FLAGS__", suffix)
    return _make_lines(text)


def _dependency_tokens(services: list[str]) -> str:
    """``consumer:backend`` pairs, in startup order, for the packaged Makefile."""
    selected = set(services)
    tokens: list[str] = []
    for service in _startup_order(services):
        for backend in direct_dependencies(service, selected):
            tokens.append(f"{service}:{backend}")
    return " ".join(tokens)


def _makefile(services: list[str]) -> str:
    startup = _startup_order(services)
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

PYTHON_ENV_MGR := python3 bin/env_manager.py
password ?=

# One compose project per service, like bin/service_manager.py: --project-directory
# loads <service>/.env for interpolation and resolves ./ paths inside <service>/.
STARTUP_SERVICES := {" ".join(startup)}
SHUTDOWN_SERVICES := {" ".join(reversed(startup))}
# consumer:backend. up/recreate wait until each backend is running and healthy.
SERVICE_DEPS := {_dependency_tokens(services)}
READY_TIMEOUT ?= 300
COMPOSE = docker compose --project-directory $$s -f docker-compose.shared.yml -f $$s/docker-compose.yml
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

setup: ## Create env files, fill secrets, and optionally generate certificates
>@echo "Checking shared Docker networks (traefik_proxy, backend_net, data_net)..."
>@for pair in "traefik_proxy:10.0.0.0/16" "backend_net:10.1.0.0/16" "data_net:10.2.0.0/16"; do \
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
>@read -p "Do you want to generate SSL certificates? (y/n) " -n 1 -r; \
>echo; \
>if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
>$(MAKE) cert; \
>fi
>@echo ""

passwords: ## Fill the shared password only (optional: password='…' force=1)
>@$(PYTHON_ENV_MGR) fill-shared-password \
>$(if $(password),--password "$(password)",) \
>$(if $(filter 1 true yes,$(force)),--force,)

cert: ## Generate SSL certificates for Traefik
>@echo "Detecting local IP..."
>@CURRENT_IP=$$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' \
>  | grep -v '127.0.0.1' | awk '{print $$2}' | sed 's/addr://' | head -n 1); \
>echo "Local IP detected: $$CURRENT_IP"; \
>mkdir -p traefik/certs; \
>if command -v mkcert >/dev/null 2>&1; then \
>mkcert -cert-file traefik/certs/server.crt \
>       -key-file traefik/certs/server.key \
>       "$$CURRENT_IP" \
>       "*.dss.localhost" \
>       "*.minio.dss.localhost" \
>       "*.garage.dss.localhost" \
>       "*.tts.dss.localhost" \
>       "dss.localhost" \
>       localhost \
>       127.0.0.1 \
>       ::1; \
>echo "Success: Certificates are generated in traefik/certs/"; \
>else \
>echo "Error: mkcert is not installed. Please install it first."; \
>exit 1; \
>fi

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


def render_readme(name: str, services: list[str], catalog: dict | None = None) -> str:
    """README for the packaged tree: quick start plus services grouped by category."""
    catalog = load_catalog() if catalog is None else catalog
    lines = [
        f"# {name}",
        "",
        "Packaged Docker Shared Services stack generated by `make package`.",
        "",
        "## Quick start",
        "",
        "```bash",
        "make setup   # networks, .env files, shared password, secrets, optional certificates",
        "make up      # validate compose, then start every service in dependency order",
        "make down    # stop and remove containers (volumes are kept)",
        "```",
        "",
        "Run `make help` for every command.",
        "",
        "## Services",
    ]
    for category in CATEGORIES:
        members = [s for s in services if catalog.get(s, {}).get("category") == category]
        if not members:
            continue
        lines += ["", f"### {category}", ""]
        for service in members:
            entry = catalog[service]
            lines.append(f"- **{service}**: {entry['description']}")
            lines.append(f"  - Containers: {', '.join(entry['containers'])}")
            web_ui = entry["web_ui"]
            lines.append(f"  - Web UI: {', '.join(web_ui) if web_ui else 'none'}")
    return "\n".join(lines) + "\n"


def export_stack(
    selected: list[str],
    name: str,
    *,
    root: Path | None = None,
    destination: Path | None = None,
) -> Path:
    """Write a runnable tree for ``selected`` services. Refuse an existing destination."""
    validate_stack_name(name)
    root = (root or repo_root()).resolve()
    services = resolve_services(selected, root)
    dest = destination if destination is not None else root / "dist" / name
    dest = dest.resolve()
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")

    created = False
    try:
        dest.mkdir(parents=True)
        created = True
        for service in services:
            source = root / service
            if not source.is_dir():
                raise FileNotFoundError(f"Service directory not found: {source}")
            _copy_tree(source, dest / service, service, root, Path())
        shutil.copy2(root / "docker-compose.shared.yml", dest / "docker-compose.shared.yml")
        example = (root / ".env.example").read_text(encoding="utf-8")
        (dest / ".env.example").write_text(filter_env_example(example, services), encoding="utf-8")
        bin_dir = dest / "bin"
        bin_dir.mkdir()
        shutil.copy2(root / "bin" / "utils.py", bin_dir / "utils.py")
        shutil.copy2(root / "bin" / "env_manager.py", bin_dir / "env_manager.py")
        config_source = (root / "bin" / "config.py").read_text(encoding="utf-8")
        (bin_dir / "config.py").write_text(
            filter_config_source(config_source, services), encoding="utf-8"
        )
        (dest / "Makefile").write_text(_makefile(services), encoding="utf-8")
        (dest / "README.md").write_text(render_readme(name, services), encoding="utf-8")
        shutil.copy2(root / ".python-version", dest / ".python-version")
        (dest / "pyproject.toml").write_text(_PACKAGE_PYPROJECT, encoding="utf-8")
        (dest / ".gitignore").write_text(_PACKAGE_GITIGNORE, encoding="utf-8")
    except Exception:
        if created and dest.exists():
            shutil.rmtree(dest)
        raise
    return dest
