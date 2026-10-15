"""Services shown as labels until manual configuration exists.

``oauth2-proxy`` stays in the catalog, but ``make manage`` and ``make tui`` do not
offer it as a start target while the Zitadel client id and secret are empty.
"""

from pathlib import Path

from dss.core.utils import read_env_value

_OAUTH2_CLIENT_KEYS = ("OAUTH2_PROXY_CLIENT_ID", "OAUTH2_PROXY_CLIENT_SECRET")
_OAUTH2_REASON = (
    "OIDC client not set — fill OAUTH2_PROXY_CLIENT_ID and "
    "OAUTH2_PROXY_CLIENT_SECRET in oauth2-proxy/.env"
)


def label_only_reason(service: str) -> str | None:
    """Why ``service`` is display-only, or None when it can be started."""
    if service != "oauth2-proxy":
        return None
    env_path = Path("oauth2-proxy") / ".env"
    if not env_path.is_file():
        return "oauth2-proxy/.env is missing — run make setup"
    if any(not read_env_value(env_path, key) for key in _OAUTH2_CLIENT_KEYS):
        return _OAUTH2_REASON
    return None


def label_only_services() -> frozenset[str]:
    """Service names that menus may show but must not start or stop."""
    if label_only_reason("oauth2-proxy") is None:
        return frozenset()
    return frozenset({"oauth2-proxy"})
