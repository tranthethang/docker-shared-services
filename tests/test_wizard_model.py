"""Selection logic of the package wizard, without Textual."""

from __future__ import annotations

from pathlib import Path

from dss.core.config import SERVICES
from dss.core.service_catalog import CATEGORIES
from dss.package.wizard_model import (
    CATALOG,
    TRAEFIK_USERS,
    added_dependencies,
    confirm_rows,
    grouped_matches,
    matches,
    ordered_selection,
    required_by,
    requires,
    selection_state,
    stack_name_error,
    toggle,
)


def test_requires_lists_backends_and_traefik_in_service_order() -> None:
    needs = requires("zitadel")
    assert "postgres" in needs
    assert "traefik" in needs
    assert needs == [name for name in SERVICES if name in needs]
    assert "traefik" not in requires("traefik")


def test_required_by_is_the_inverse_of_requires() -> None:
    assert "zitadel" in required_by("postgres")
    assert required_by("traefik") == TRAEFIK_USERS


def test_matches_name_category_and_description_case_insensitively() -> None:
    entry = CATALOG["zitadel"]
    assert matches("zitadel", "")
    assert matches("zitadel", "ZITA")
    assert matches("zitadel", entry["category"].upper())
    assert matches("zitadel", entry["description"][:8].lower())
    assert not matches("zitadel", "no-such-text-anywhere")


def test_grouped_matches_follows_category_order_and_drops_empty_groups() -> None:
    groups = grouped_matches("")
    categories = [category for category, _members in groups]
    assert categories == [category for category in CATEGORIES if category in categories]
    assert sorted(name for _category, members in groups for name in members) == sorted(SERVICES)
    filtered = dict(grouped_matches("zitadel"))
    assert "zitadel" in filtered[CATALOG["zitadel"]["category"]]
    assert all(matches(name, "zitadel") for members in filtered.values() for name in members)
    assert grouped_matches("no-such-text-anywhere") == []


def test_added_dependencies() -> None:
    assert added_dependencies(set()) == set()
    assert added_dependencies({"zitadel"}) == {"postgres", "traefik"}
    assert added_dependencies({"zitadel", "postgres"}) == {"traefik"}


def test_toggle_returns_a_new_set() -> None:
    checked = {"redis"}
    assert toggle(checked, "postgres") == {"redis", "postgres"}
    assert toggle(checked, "redis") == set()
    assert checked == {"redis"}


def test_selection_state() -> None:
    assert selection_state("zitadel", {"zitadel"}, {"postgres"}) == "checked"
    assert selection_state("postgres", {"zitadel"}, {"postgres"}) == "added"
    assert selection_state("redis", {"zitadel"}, {"postgres"}) == "none"


def test_ordered_selection_uses_service_order() -> None:
    picked = {SERVICES[-1], SERVICES[0]}
    assert ordered_selection(picked) == [SERVICES[0], SERVICES[-1]]


def test_stack_name_error(tmp_path: Path) -> None:
    assert stack_name_error("ok-stack", tmp_path) is None
    assert stack_name_error("Bad Name", tmp_path) is not None
    assert stack_name_error("", tmp_path) is not None
    (tmp_path / "dist" / "taken").mkdir(parents=True)
    assert stack_name_error("taken", tmp_path) == "dist/taken/ already exists"


def test_confirm_rows_lists_checked_and_added_in_service_order() -> None:
    rows = confirm_rows(["zitadel"], ["postgres", "traefik"])
    assert [row[0] for row in rows] == [
        s for s in SERVICES if s in {"zitadel", "postgres", "traefik"}
    ]
    reasons = {row[0]: row[3] for row in rows}
    assert reasons == {"zitadel": "checked", "postgres": "dependency", "traefik": "dependency"}
    for service, category, web_ui, _reason in rows:
        assert category == CATALOG[service]["category"]
        assert web_ui == (CATALOG[service]["web_ui"] or ["—"])[0]
