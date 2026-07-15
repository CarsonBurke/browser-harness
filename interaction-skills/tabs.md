# Tabs

Use **CDP for control**, **UI automation for user-visible order**.

## Pure CDP (portable: macOS / Linux / Windows)

```python
tabs = list_tabs()                         # includes chrome:// pages too
real_tabs = list_tabs(include_chrome=False)
tid = new_window("https://example.com")    # background window + attach
attach_tab(tid)                            # attach without focusing
print(current_tab())
print(page_info())
```

What CDP is good at:
- attach to a tab
- open a tab or window in the background
- inspect URL/title/viewport
- capture the attached tab's screenshot even if another tab is visibly frontmost

What CDP is bad at:
- matching the **left-to-right tab strip order** the user sees
- telling whether the attached target is an omnibox popup / internal page without URL filtering

## Visible order (platform UI)

### macOS

```applescript
tell application "Google Chrome"
  set out to {}
  set i to 1
  repeat with t in every tab of front window
    set end of out to {tab_index:i, tab_title:(title of t), tab_url:(URL of t)}
    set i to i + 1
  end repeat
  return out
end tell
```

### Linux

No AppleScript. Same split still applies:
- use CDP for background window/tab creation, attachment, and inspection
- use window-manager / browser UI automation when the user means visible order

Typical tools:
- `xdotool`
- `wmctrl`
- desktop-environment scripting (`gdbus`, KWin, GNOME Shell extensions, etc.)

## Rules that held up in practice

- `attach_tab()` and its compatibility alias `switch_tab()` never focus or raise a browser window.
- `new_tab()` stays in the background but Chrome may place it in an existing user window. Use `new_window()` for isolated agent work.
- Never call `Target.activateTarget` or platform activation APIs. If the user wants to see the window, let them select it themselves.
- `list_tabs()` includes `chrome://newtab/` by default; ask for `include_chrome=False` when you want only real pages.
- `chrome://omnibox-popup.top-chrome/` can appear as a fake page target; ignore it for user-facing tab lists.
- If a page has `w=0 h=0`, you may be attached to the wrong target or a non-window surface.
- For dynamic UIs, re-read element rects after opening dropdowns / modals before coordinate-clicking.
