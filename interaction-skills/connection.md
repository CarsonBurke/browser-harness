# Connection & Tab Visibility

## The omnibox popup problem

When Chrome opens fresh, the only CDP `type: "page"` targets are `chrome://inspect` and `chrome://omnibox-popup.top-chrome/` (a 1px invisible viewport). If the daemon attaches to the omnibox popup, all subsequent work — including `new_tab()` and `goto_url()` — happens on tabs that exist in CDP but may not be visible in the Chrome UI.

The daemon stays unattached when no real page exists; it does not manufacture a bootstrap window. Start work with `new_window()`, or attach to a deliberately selected existing target when the task requires its state.

## Startup sequence

1. Check if a daemon is already running with `daemon_alive()`
2. If stale sockets exist but daemon is dead, clean them up
3. List open tabs with `list_tabs()` to see what's available
4. `ensure_real_tab()` attaches to a real page
5. `attach_tab(target_id)` (or compatibility alias `switch_tab`) attaches without focusing or raising the browser

```python
if not daemon_alive():
    import os, ipc
    ipc.cleanup_endpoint("default")
    pid = ipc.pid_path("default")
    if pid.exists(): pid.unlink()
    ensure_daemon()

tabs = list_tabs()
for t in tabs:
    print(t["url"][:60])

tab = ensure_real_tab()
```

## Navigating

Use `new_window()` for isolated work, then navigate that target with `goto_url()`. Chrome may put `new_tab()` into an existing user window, so create another background window when a separate page must stay open.

```python
target = new_window("https://example.com")
print(current_tab())
```
