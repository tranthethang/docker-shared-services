# Capturing TUI & CLI screenshots as SVG

Screenshots in `assets/` are generated as vector SVGs using [freeze](https://github.com/charmbracelet/freeze) (`brew install charmbracelet/tap/freeze`).

## Why `freeze --execute "make console"` fails

`make console` launches the `ratatui` dashboard (`cli/target/release/dss`), which requires an interactive TTY (`stdout().is_terminal() && stdin().is_terminal()` in `cli/src/tui/mod.rs`) and runs an event loop until `q` is pressed. `freeze --execute` runs commands over a non-interactive pipe and expects them to print to stdout and exit.

## Capturing `make console` (`assets/console.svg`)

Run `make console` inside a detached `tmux` session with a fixed terminal size, wait for the TUI to render, capture the pane with ANSI escape codes (`-e`), and pipe it to `freeze -l ansi`:

```bash
brew install tmux charmbracelet/tap/freeze

make build && \
tmux new-session -d -s dss-shot -x 120 -y 36 "make console" && \
sleep 2 && \
tmux capture-pane -t dss-shot -e -p | freeze -l ansi --window -b "#f2e5bc" -o assets/console.svg && \
tmux kill-session -t dss-shot
```

Notes:

- **Background color (`-b`):** `freeze` defaults to a dark `#171717` canvas and only emits background `<rect>` elements on certain color transitions. Passing `-b "#f2e5bc"` (the default `gruvbox-light-soft` `surface_base` in `cli/src/tui/theme.rs`) prevents dark blotches on empty cells and trailing spaces.
- **Other themes (`DSS_THEME`):** Match `-b` to the theme's `surface_base` in `cli/src/tui/theme.rs`:
  - `gruvbox-light-soft` (default): `#f2e5bc`
  - `ocean`: `#0f1419`
  - `amber`: `#14110e`
  - `nord`: `#2e3440`
- **Build first:** Run `make build` beforehand because `make console` requires the prebuilt `dss` binary.
- **Duplicate session error:** If a previous run failed mid-way, clean up with `tmux kill-session -t dss-shot`.

## Capturing static CLI commands

Non-interactive commands that print to stdout and exit can use `freeze --execute` directly:

```bash
freeze --execute "make help" --window -o assets/help.svg
freeze --execute "cli/target/release/dss ps" --window -o assets/ps.svg
```
