"""Filter the root ``.env.example`` down to the banners of selected services."""

from __future__ import annotations

import re

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
