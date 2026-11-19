# Rust layout

How the `dss` binary in `cli/` is split into modules, and how to add one. Each rule names the tool that enforces it. "Review only" means no tool checks it.

## Modules

| Path                     | Purpose                                                                           |
| ------------------------ | --------------------------------------------------------------------------------- |
| `cli/src/main.rs`        | `clap` command tree. No subcommand opens the dashboard.                           |
| `cli/src/config.rs`      | `SERVICES`, `START_ORDER`, `PACKAGE_REQUIRES`, password rules, `active_services`. |
| `cli/src/stack.rs`       | `SANDBOX_NAME`, `SANDBOX_SUBNET_BASE`, project and network names.                 |
| `cli/src/catalog.rs`     | Loads the embedded `cli/service_catalog.json` and fills `{domain}`.               |
| `cli/src/env/`           | `.env` files, secrets, the shared password, validation, Dozzle users.             |
| `cli/src/docker/`        | `Runner` trait, compose commands, readiness gates, container state, log follower. |
| `cli/src/commands.rs`    | Subcommand bodies. `cleanup.rs` holds the destructive ones.                       |
| `cli/src/tui/`           | ratatui dashboard: state (`app.rs`), keys, drawing (`ui.rs`), worker operations.  |
| `cli/src/package/`       | `make package` exporter and wizard.                                               |
| `cli/src/repo_rules.rs`  | Test-only checks that read the Compose files. See [quality-gate.md](quality-gate.md). |

Rules:

- Docker calls go through the `Runner` trait in `cli/src/docker/mod.rs`, so tests use a fake runner. **Review only.**
- `app.rs` and `keys.rs` in `tui/`, and `package/wizard.rs`, hold no terminal or Docker calls, so unit tests need no terminal. **Review only.**
- Code that runs while the dashboard owns the screen never prints to stdout. Send lines to a callback. **Review only.**
- Do not add `tokio` or `bollard`. Docker runs through `std::process::Command`, `std::thread`, and `mpsc`. **Review only.**
- Crates: `clap`, `ratatui`, `crossterm`, `serde`, `serde_json`, `rand`, `base64`, `hmac`, `sha2`, `bcrypt`. Ask before adding another. **Review only.**
- Do not change a service `docker-compose.yml` or `.env.example` to fit the binary. **Review only.**

## Code rules

- Formatting is `cargo fmt`. **Enforced by** `make format-check`.
- Clippy warnings are errors, tests included. **Enforced by** `make lint` (`cargo clippy --all-targets -- -D warnings`).
- Fix a warning instead of allowing it. When a fix would risk behavior, use an `#[allow(...)]` with a comment that gives the reason. **Review only.**
- Each `*.rs` and `*.sh` file is at most 300 lines, tests included. Move tests to a `*_tests.rs` file with `#[path = "…"]` when a file grows. **Enforced by** `cli/src/size_rules.rs` (`make test`).
- Functions return `Result<_, String>` for expected failures. Do not `unwrap` on user input or Docker output. **Review only.**

## Running code

- Run the binary through the Makefile (`make up service=redis`), or `cli/target/release/dss <subcommand>` after `make build`. Run from the repo root, because Compose paths are relative. **Review only.**
- `cargo` is the only build requirement. The Makefile stops with an install hint when it is missing. **Enforced by** the Makefile.

## Adding a module

1. Pick the directory that fits the purpose in the table above. Shared logic with no Docker calls belongs in `config`, `stack`, `catalog`, or `env`.
1. Create `cli/src/<name>.rs` (or a directory with `mod.rs`) with a one-line `//!` comment, and declare it in `main.rs`.
1. For a new subcommand, add it to the `clap` tree in `main.rs` and a body in `commands.rs`, then add a Makefile target that runs `$(DSS) <subcommand>`.
1. Add unit tests in the file, or in a `*_tests.rs` file next to it.
1. Run `make check`.

## Scripts

Makefile helpers are subcommands of `dss`, not shell scripts. Service-specific scripts live in their service directory, for example `supabase/run.sh`. **Review only.** Scripts that delete data must prompt first. **Review only.**
