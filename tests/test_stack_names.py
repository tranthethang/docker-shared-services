"""Compose files keep names stack-scoped: DSS_NAME prefixes and the dss.stack router label."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILES = sorted(ROOT.glob("*/docker-compose.yml"))
CONTAINER_NAME = re.compile(r'^\s+container_name:\s*"?(.+?)"?\s*$')
PREFIX = "${DSS_NAME:+${DSS_NAME}-}"
STACK_LABEL = '"dss.stack=${DSS_NAME:-dss}"'


@pytest.mark.parametrize("compose", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_container_names_carry_the_stack_prefix(compose: Path) -> None:
    for line in compose.read_text(encoding="utf-8").splitlines():
        match = CONTAINER_NAME.match(line)
        if match:
            assert match.group(1).startswith(PREFIX), f"{compose.parent.name}: {line.strip()}"


@pytest.mark.parametrize("compose", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_routed_services_carry_the_stack_label(compose: Path) -> None:
    text = compose.read_text(encoding="utf-8")
    assert text.count('"traefik.enable=true"') == text.count(STACK_LABEL)
    assert "traefik.docker.network=traefik_proxy" not in text


TOP_LEVEL = re.compile(r"^([a-z_]+):")
RESOURCE_NAME = re.compile(r'^    name:\s*"?(.+?)"?\s*$')
RESOURCE_PREFIX = "${DSS_NAME:+${DSS_NAME}_}"


@pytest.mark.parametrize("compose", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_explicit_volume_and_network_names_carry_the_stack_prefix(compose: Path) -> None:
    section = ""
    for line in compose.read_text(encoding="utf-8").splitlines():
        top = TOP_LEVEL.match(line)
        if top:
            section = top.group(1)
            continue
        match = RESOURCE_NAME.match(line)
        if match and section in {"volumes", "networks"}:
            assert match.group(1).startswith(RESOURCE_PREFIX), (
                f"{compose.parent.name}: {line.strip()}"
            )
