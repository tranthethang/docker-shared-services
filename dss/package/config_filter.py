"""Render ``dss/core/config.py`` with its service maps limited to a selection."""

from __future__ import annotations

import ast

from dss.core.config import (
    AUTH_OPT_IN_UI_SERVICES,
    AUTO_GENERATED_SECRETS,
    SERVICE_INFO_VARS,
    SERVICES,
    SHARED_PASSWORD_KEYS,
    SHARED_PASSWORD_TEMPLATES,
    START_ORDER,
    STRONG_PASSWORD_REQUIRED,
    VALIDATION_RULES,
)


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
