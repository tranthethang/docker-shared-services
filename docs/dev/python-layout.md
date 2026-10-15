# Python layout

How the `dss` package is split into layers, and how to add a module. Each rule names the tool that enforces it. "Review only" means no tool checks it.

## Layers

| Package       | Purpose                                                                  | May import                   |
| ------------- | ------------------------------------------------------------------------ | ---------------------------- |
| `dss/core`    | Config tables, service catalog, `.env` handling, secrets, dependencies.  | Standard library, `dss.core` |
| `dss/cli`     | `make up/down/…`, `make setup`, `make info`, `make manage` entry points. | `dss.core`, `dss.cli`        |
| `dss/package` | `make package` exporter and wizard.                                      | `dss.core`, `dss.package`    |
| `dss/tui`     | Textual dashboard (`make tui`).                                          | Anything above, `textual`    |
| `tools/`      | Dev tooling (formatter, file-size check). Not part of `dss`.             | Anything in the dev group    |

Rules:

- `dss.core` imports nothing from `dss.cli`, `dss.package`, or `dss.tui`. **Enforced by** import-linter (`make lint`, contract "core imports no higher layer").
- `dss.core` imports only the standard library. **Enforced by** `tests/test_core_imports.py` (`make test`).
- `dss.cli` and `dss.package` do not import each other or `dss.tui`. **Enforced by** import-linter (`make lint`, contracts "cli and package are independent" and "cli and package do not import tui").
- Imports are absolute (`from dss.core.config import …`). Relative imports and `sys.path` hacks are not allowed. **Review only.**

## Running code

- Run modules from the repo root through `uv`, for example `uv run --frozen --no-dev python -m dss.cli.env check all`. The Makefile does this for you. **Enforced by** the Makefile (every Python target goes through `uv`).
- Runtime code depends only on the standard library. `textual` and `docker` live in the `tui` dependency group, and tools in the `dev` group. Ask before adding a dependency. **Review only.**

## Code rules

- Ruff lint rules `E F W I UP B N SIM PTH S C90 PLR` apply to `dss/`, `tools/`, and `tests/`. **Enforced by** ruff (`make lint`). Config: `[tool.ruff.lint]` in `pyproject.toml`.
- Complexity limits: McCabe ≤ 10, branches ≤ 12, arguments ≤ 6, statements ≤ 50, returns ≤ 6. **Enforced by** ruff `C901` and `PLR09xx` (`make lint`). Split the function instead of raising a limit.
- Use `pathlib.Path`, not `os.path`. **Enforced by** ruff `PTH` (`make lint`).
- Fix a violation instead of ignoring it. When a fix would risk behavior, use an inline `# noqa: <code>  # <reason>`. Per-file ignores exist only for `S101` in tests, `S603`/`S607` in the `dss/cli`, `dss/tui`, and `tools` modules that run subprocesses with fixed argv lists, and `E501` in two modules that keep long remediation and generated-Makefile lines. **Review only** (ruff can't judge the reason).
- Every function is fully typed, and mypy runs in strict mode with no `ignore_errors` overrides. The only exception is `ignore_missing_imports` for `textual.*` and `docker.*`. **Enforced by** mypy (`make typecheck`, which installs the `tui` group so Textual classes are typed).
- Formatting: ruff format, line length 100. **Enforced by** `make format-check`.
- Each Python file is ≤ 300 lines. **Enforced by** `tools/check_file_size.py` (`make lint`).

## Adding a module

1. Pick the lowest layer that has everything the module needs. Shared logic with no I/O beyond files goes in `dss/core`.
1. Create `dss/<layer>/<name>.py` with a one-line module docstring.
1. Import it absolutely from callers. If it is a new entry point, add a Makefile target that runs `$(PY) -m dss.<layer>.<name>`.
1. Add tests under `tests/`. New `dss/core` code must keep `dss/core` coverage at or above 80%. **Enforced by** `coverage report --fail-under` (`make test`).
1. Run `make check`.

When a new subpackage is added, add it to the import-linter contracts in `pyproject.toml`.
