"""Golden snapshot of ``make info`` rendered from the service catalog.

Regenerate with GOLDEN_UPDATE=1 (make test-update). A normal test run only compares.
"""

from __future__ import annotations

import os
from pathlib import Path

from dss.cli.info import render_info, service_lines
from dss.core.service_catalog import catalog_problems, load_catalog


def test_info_matches_golden(repo_root: Path) -> None:
    actual = render_info()
    golden = repo_root / "tests" / "golden" / "info.txt"
    if os.environ.get("GOLDEN_UPDATE") == "1":
        golden.write_text(actual, encoding="utf-8")
        return
    assert golden.is_file(), f"missing golden {golden}; run make test-update"
    assert golden.read_text(encoding="utf-8") == actual


def test_service_lines_are_sorted_and_cover_multi_line_stacks() -> None:
    catalog = {
        "b": {"info": ["beta - one", "Alpha - two"]},
        "a": {"info": []},
        "c": {"info": ["gamma - three"]},
    }
    assert service_lines(catalog) == ["Alpha - two", "beta - one", "gamma - three"]


def test_catalog_rejects_a_non_list_info_field() -> None:
    catalog = load_catalog()
    catalog["redis"] = {**catalog["redis"], "info": "localhost:6379"}
    assert "redis: info must be a list of strings" in catalog_problems(catalog, {})
