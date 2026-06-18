---
name: browser-harness
description: Direct browser control via CDP — automate, scrape, test, or interact with web pages by driving the user's already-running Chrome (or a Browser Use cloud browser). Use when the user wants to click, screenshot, fill forms, extract data, or navigate real web pages. Default to screenshots + coordinate clicks, not selector hunting. Requires the one-time `browser-harness` CLI install (see references/install.md).
---

# browser-harness

Direct browser control via CDP. You drive a selected browser with Python helpers run through the `browser-harness` command.

## Prerequisite (one-time — NOT part of the AI workflow)

This skill is instructions only. It assumes the `browser-harness` command is already on `$PATH`. If `command -v browser-harness` fails, do the one-time install in [references/install.md](references/install.md) first, then continue. Installation and browser-connection setup are a prerequisite; once `browser-harness <<'PY' … PY` prints page info, never run install/connection steps again as part of normal work.

## Usage

Managed browsers have short explicit ids. Create or receive an id, then select it inside each script.

Create and use a private browser:

```bash
browser-harness <<'PY'
b = browser_new("private")
browser(b["id"])
new_tab("https://docs.browser-use.com")
wait_for_load()
print({"id": b["id"], "page": page_info()})
PY
```

Use an existing managed browser:

```bash
browser-harness <<'PY'
browser("abc123")
print(page_info())
PY
```

Inspect managed browsers:

```bash
browser-harness <<'PY'
print(browser_list())
print(browser_status("abc123"))
PY
```

- `browser(id)` selects a browser for this script only. Do not rely on a current browser across separate shell commands.
- `browser_list()` shows `state: "busy"` while a script is actively using that browser, including the current script.
- Invoke as `browser-harness` — it's on `$PATH` after install. No `cd`, no `uv run`.
- Use the heredoc form for every multi-line command. It prevents shell quote mangling inside Python strings and JavaScript snippets.
- First navigation is `new_tab(url)`, not `goto_url(url)` — goto runs in the user's active tab and clobbers their work.
- Helpers are pre-imported and the daemon auto-starts; you never start/stop it manually unless you want to.

## Choose Browser

- User's logged-in local Chrome: use normal helpers. If setup asks for a profile, run `browser_profiles()`, ask the user which `id` to use, then run `browser_use_profile(id)` and retry.
- Isolated local browser: `browser_new("private")`, then keep the returned `id`.
- Browser Use cloud browser with live view: `browser_new("cloud")`, then keep the returned `id`.
- Managed browser page work: call `browser(id)` first in the script.
- Subagent: if the parent gives an id, start browser scripts with `browser(id)` and do not close it unless asked.
- Done with a private or cloud browser: `browser_close(id)`.

## Browser Helpers

```python
browser_status(id)
browser_profiles()
browser_use_profile(profile_id)
browser_new("private")
browser_new("cloud")
browser(id)
browser_list()
browser_close(id)
```

If `browser_new("cloud")` reports `cloud-auth-required`, run `browser-harness auth login`.

## What actually works

- **Screenshots first.** `capture_screenshot()` to understand the page, find visible targets, and decide whether you need a click, a selector, or more navigation.
- **Clicking.** `capture_screenshot()` → read the pixel off the image → `click_at_xy(x, y)` → `capture_screenshot()` to verify. Suppress the Playwright-habit reflex of "locate first, then click" — no `getBoundingClientRect`, no selector hunt. Drop to DOM only when the target has no visible geometry. Hit-testing happens in Chrome's browser process, so clicks pass through iframes / shadow DOM / cross-origin without extra work.
- **Bulk HTTP.** `http_get(url)` + `ThreadPoolExecutor`. No browser needed for static pages.
- **After goto:** `wait_for_load()`.
- **Wrong/stale tab:** `ensure_real_tab()`.
- **Verification:** `print(page_info())` is the simplest "is this alive?" check; screenshots are the default way to verify whether a visible action worked.
- **DOM reads:** use `js(...)` for inspection/extraction when a screenshot shows coordinates are the wrong tool.
- **Auth wall:** redirected to login → stop and ask the user. Don't type credentials from screenshots.
- **Raw CDP** for anything helpers don't cover: `cdp("Domain.method", params)`.

After every meaningful action, re-screenshot before assuming it worked.

## Interaction skills (progressive disclosure)

If you struggle with a specific UI mechanic, read the matching file under `${CLAUDE_PLUGIN_ROOT}/interaction-skills/` before inventing an approach. Available: browser-wall, connection, cookies, cross-origin-iframes, dialogs, downloads, drag-and-drop, dropdowns, iframes, network-requests, print-as-pdf, profile-sync, screenshots, scrolling, shadow-dom, tabs, uploads, viewport.

## Task-specific edits

For task-specific helper additions, edit `${CLAUDE_PLUGIN_ROOT}/agent-workspace/agent_helpers.py`. Keep core helpers short.

## Domain skills (opt-in)

Community per-site playbooks live in `${CLAUDE_PLUGIN_ROOT}/agent-workspace/domain-skills/<host>/` and are **off by default**. Set `BH_DOMAIN_SKILLS=1` to enable them; when enabled and the task is site-specific, read every file in the matching `<site>/` directory before inventing an approach.

## Design constraints

- Coordinate clicks default. `Input.dispatchMouseEvent` goes through iframes/shadow/cross-origin at the compositor level.
- Connect to the user's running Chrome. Don't launch your own browser.
- Prefer compositor-level actions (screenshots, coordinate clicks, raw key input) over framework/DOM hacks. Reach for `interaction-skills/` only when those are the wrong tool.
