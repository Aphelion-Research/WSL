# Tmux Workflow

Dominion uses stable tmux sessions for shared work:

- `matin`
- `dan`
- `dominion`
- `ragd`
- `codex-matin`

Use `warp` for navigation:

```bash
warp list
warp matin
warp dan
warp dominion
warp codex
warp ragd
```

Copy and paste:

- Windows Terminal paste: `Ctrl+Shift+V`.
- Windows Terminal selection: hold `Shift` and drag when mouse mode captures selection.
- tmux prefix: `Ctrl+b`.
- tmux copy mode: `Ctrl+b [` then move/select/copy according to tmux bindings.
- Mouse scrolling works when tmux mouse mode is enabled; use terminal scrollback with `Shift` if needed.

No shell startup file should auto-attach tmux or run blocking commands.
