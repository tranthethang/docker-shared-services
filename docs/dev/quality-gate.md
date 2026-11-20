# Quality gate

`make check` is the single quality gate. CI (`.github/workflows/ci.yml`) runs it on every push and pull request, after it builds the binary and creates a disposable Compose env. The git hooks call the same targets except `make validate`.

## `make check`

Runs these targets in order and stops at the first failure:

| Target              | What it runs                                                                           |
| ------------------- | -------------------------------------------------------------------------------------- |
| `make format-check` | `cargo fmt --check`                                                                    |
| `make lint`         | `cargo clippy --all-targets -- -D warnings`                                            |
| `make shell-lint`   | `shellcheck -S warning` on every tracked `*.sh` file (needs `shellcheck`)              |
| `make test`         | `cargo test`: unit tests, Compose repo rules, and the 300-line limit                   |
| `make validate`     | `docker compose config` per service, plus service catalog drift                        |

`make format` rewrites the Rust sources in place. Run it before `make check` when `format-check` fails.

Rules:

- Run `make check` after any change to Compose files, `cli/`, or the Makefile. **Enforced by** CI. Git hooks run `format-check`, `lint`, and `shell-lint` on commit and `test` on push. `make validate` is CI-only (see below).
- Do not lower a limit (line length, clippy level, file size) to make a check pass. **Review only.**

## Limits

- File size: each `*.rs` and `*.sh` file in the repo is at most 300 lines. **Enforced by** `cli/src/size_rules.rs` (`make test`).
- Lint limits are in [rust-layout.md](rust-layout.md).

## Compose rules

`cli/src/repo_rules.rs` reads every `docker-compose.yml` with a line reader and runs under `make test`:

- Every directory with a compose file is in `SERVICES` and the catalog, and catalog `containers` match the compose service names.
- Every service sets `restart`. A service with `restart: "no"` is awaited with `condition: service_completed_successfully`.
- `container_name`, and explicit volume and network `name:` values, carry the `SANDBOX_NAME` prefix. Every `traefik.enable=true` service carries the `sandbox.stack` label.
- Data stores sit on `data_net` and not `backend_net`. Only declared clients join `data_net`.

A failure names the compose file and the service. Fix the compose file, or the table at the top of `repo_rules.rs` when a new data store is added.

## Git hooks

`make hooks` installs [prek](https://github.com/j178/prek) hooks from `.pre-commit-config.yaml`:

- pre-commit: `make format-check`, `make lint`, `make shell-lint`
- pre-push: `make test`

Hooks only call make targets and define no rule config of their own. **Enforced by** review of `.pre-commit-config.yaml`. To run every hook without committing, use `prek run --all-files --hook-stage pre-commit` (or `--hook-stage pre-push`).

## Dependencies

- `cli/Cargo.lock` is committed and matches `cli/Cargo.toml`. **Enforced by** `cargo build` in CI.
- Ask before adding a crate. **Review only.**
