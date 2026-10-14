"""Unit tests for the file-size gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load(repo_root: Path):
    path = repo_root / "tools" / "check_file_size.py"
    spec = importlib.util.spec_from_file_location("check_file_size", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, lines: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"line {index}" for index in range(lines)) + "\n", encoding="utf-8")


def test_file_under_limit_passes(repo_root: Path, tmp_path: Path) -> None:
    checker = _load(repo_root)
    _write(tmp_path / "dss" / "small.py", 10)
    assert checker.check_files(tmp_path, {}) == []


def test_file_over_limit_fails(repo_root: Path, tmp_path: Path) -> None:
    checker = _load(repo_root)
    _write(tmp_path / "dss" / "big.py", checker.LIMIT + 1)
    problems = checker.check_files(tmp_path, {})
    assert len(problems) == 1
    assert "big.py" in problems[0]
    assert "exceeds limit" in problems[0]


def test_baselined_file_may_not_grow(repo_root: Path, tmp_path: Path) -> None:
    checker = _load(repo_root)
    relative = "dss/legacy.py"
    _write(tmp_path / relative, 12)
    assert checker.check_files(tmp_path, {relative: 12}) == []
    _write(tmp_path / relative, 13)
    problems = checker.check_files(tmp_path, {relative: 12})
    assert len(problems) == 1
    assert "grew" in problems[0]


def test_repo_baseline_matches_current_tree(repo_root: Path) -> None:
    checker = _load(repo_root)
    baseline = checker.load_baseline(repo_root / "tools" / "file_size_baseline.json")
    assert baseline
    assert checker.check_files(repo_root, baseline) == []


def test_main_exits_nonzero_on_violation(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checker = _load(repo_root)
    _write(tmp_path / "dss" / "big.py", checker.LIMIT + 1)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "file_size_baseline.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(checker, "__file__", str(tmp_path / "tools" / "check_file_size.py"))
    assert checker.main([str(tmp_path)]) == 1
