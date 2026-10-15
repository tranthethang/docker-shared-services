# Quality gate

`make check` is the single quality gate. CI (`.github/workflows/ci.yml`) runs it on every push and pull request, after `uv lock --check` and a disposable Compose env. The git hooks call the same targets except `make validate`.

## `make check`

Runs these targets in order and stops at the first failure:

| Target              | What it runs                                                                         |
| ------------------- | ------------------------------------------------------------------------------------ |
| `make format-check` | `tools/format_repo.py --check`: ruff format, yamlfix, mdformat, JSON, `.env.example` |
| `make lint`         | ruff, import-linter, `tools/check_file_size.py`, shellcheck, shfmt                   |
| `make typecheck`    | mypy strict on `dss/` and `tools/` (installs the `tui` group)                        |
| `make test`         | pytest with a `dss/` coverage report, then the `dss/core` coverage floor             |
| `make validate`     | `docker compose config` per service, plus service catalog drift                      |

`make format` rewrites files in place. Run it before `make check` when `format-check` fails.

Rules:

- Run `make check` after any change to Compose files, shell scripts, `dss/`, `tools/`, or `tests/`. **Enforced by** CI. Git hooks run `format-check`, `lint`, `typecheck`, and `test`; `make validate` is CI-only (see below).
- Do not lower a limit (line length, complexity, coverage floor, file size) to make a check pass. **Review only.**

## Limits

- File size: each `*.py` under `dss/`, `tools/`, `tests/` and each `*.sh` is ≤ 300 lines. `tools/file_size_baseline.json` stays `{}`. **Enforced by** `tools/check_file_size.py` (`make lint`) and `tests/test_file_size.py` (`make test`).
- Coverage: `dss/core` ≥ 80% (`COVERAGE_FLOOR_CORE` in the Makefile). `dss/cli`, `dss/package`, and `dss/tui` are reported but not counted toward the floor. **Enforced by** `coverage report --include='dss/core/*' --fail-under` (`make test`).
- Lint, complexity, and typing limits are in [python-layout.md](python-layout.md).

## Golden snapshots

`tests/test_export_golden.py` exports a stack with `export_stack` and compares the result with `tests/golden/<stack>/`. `tests/golden/info.txt` pins `make info` output.

- A golden diff means `export_stack` or `make info` output changed. If the change is intended, regenerate with `make test-update` (`GOLDEN_UPDATE=1`) and review the diff under `tests/golden/` before committing. **Enforced by** pytest (`make test`). Whether a change is intended is **review only**.
- `dss/core/config.py` is copied into exports, so any edit to it, comments included, changes the `config.py` goldens.

## Git hooks

`make hooks` installs [prek](https://github.com/j178/prek) hooks from `.pre-commit-config.yaml`:

- pre-commit: `make format-check`, `make lint`, `make typecheck`
- pre-push: `make test`

Hooks only call make targets and define no rule config of their own. **Enforced by** review of `.pre-commit-config.yaml`. To run every hook without committing, use `uv run prek run --all-files --hook-stage pre-commit` (or `--hook-stage pre-push`).

## Dependencies

- `uv.lock` must match `pyproject.toml`. **Enforced by** `uv lock --check` in CI.
- Ask before adding a dependency. **Review only.**
