# Shell scripts

Rules for `*.sh` files. Each rule names the tool that enforces it. "Review only" means no tool checks it.

## Where scripts live

- Makefile helpers live in `scripts/`. Service-specific scripts live in their service directory (for example `supabase/run.sh`). **Review only.**
- A Makefile recipe calls a script or a `dss` module. It does not embed multi-line bash. **Review only.**

## Script rules

- Start with `#!/usr/bin/env bash`, a one-line comment saying what the script does, and `set -euo pipefail`. **Review only.** shellcheck catches many of the bugs that `set -u` and `pipefail` would surface.
- Provide `usage()` (a heredoc that shows arguments and an example), print it for `-h`/`--help`, and exit `2` on bad arguments. **Review only.**
- Take paths and names as arguments instead of hard-coding them, so the Makefile passes the values. **Review only.**
- Write errors to stderr (`>&2`). **Review only.**
- Pass shellcheck, following sourced files (`shellcheck -x`). **Enforced by** shellcheck (`make lint`).
- Format with shfmt: 2-space indent, indented `case` branches (`shfmt -i 2 -ci`). **Enforced by** shfmt (`make lint`, diff mode). Fix with `uv run shfmt -w -i 2 -ci <file>`.
- Each script is ≤ 300 lines. **Enforced by** `tools/check_file_size.py` (`make lint`).

## Scripts that delete data

`scripts/remove-all.sh` and `scripts/remove-config.sh` delete volumes or `.env` files. Run them, or their `make remove-all` / `make remove-config` targets, only when asked. They must prompt before deleting. **Review only.**

## Scope

`make lint` checks every `*.sh` outside `.venv/`, `dist/`, `.git/`, and `*/data/`.
