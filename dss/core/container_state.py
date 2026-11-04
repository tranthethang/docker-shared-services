"""Decide whether one container counts as up for readiness checks and status views."""

# Compose `restart: "no"` marks a one-shot init container (see docs/dev/adding-a-service.md).
ONESHOT_RESTART_POLICIES = frozenset({"", "no"})
READY_HEALTH = frozenset({"none", "healthy"})


def is_completed_oneshot(status: str, exit_code: int, restart_policy: str) -> bool:
    """Return True for a one-shot init container that finished with exit code 0."""
    return status == "exited" and exit_code == 0 and restart_policy in ONESHOT_RESTART_POLICIES


def is_container_ready(status: str, health: str, exit_code: int, restart_policy: str) -> bool:
    """Return True when a container is running and healthy, or is a finished one-shot."""
    if status == "running":
        return health in READY_HEALTH
    return is_completed_oneshot(status, exit_code, restart_policy)
