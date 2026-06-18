---
name: browser
description: Control a browser with Python helpers. Use for web automation, scraping, testing, or interacting with pages.
---

# browser-harness

There is one active browser. Normal page helpers act on it:

```bash
browser-harness <<'PY'
new_tab("https://docs.browser-use.com")
wait_for_load()
print(page_info())
PY
```

Use `browser_*` helpers only to choose, set up, or close the active browser.

## Choose Browser

- User's logged-in local Chrome: use normal helpers. If setup asks for a profile, run `browser_profiles()`, ask the user which `id` to use, then run `browser_use_profile(id)` and retry.
- Isolated local browser: `browser_new("private")`.
- Browser Use cloud browser with live view: `browser_new("cloud")`.
- Subagent: use `browser_new("private")` unless the parent gave you a `browser_id`.
- Given a `browser_id`: `browser_switch(browser_id)`.
- Done with a private or cloud browser: `browser_close()`.

## Browser Helpers

```python
browser_status()
browser_profiles()
browser_use_profile(profile_id)
browser_new("private")
browser_new("cloud")
browser_list()
browser_switch(browser_id)
browser_close()
```

`browser_profiles()` and `browser_use_profile(...)` are local setup calls. They do not start browser work.

After `browser_new(...)` or `browser_switch(...)`, keep using the normal page helpers: `new_tab`, `page_info`, `capture_screenshot`, `click_at_xy`, `type_text`, `js`, and `cdp`.

If `browser_new("cloud")` reports `cloud-auth-required`, run:

```bash
browser-harness auth login
```

If the user directly provides an API key, store it through stdin:

```bash
browser-harness auth login --api-key-stdin
```

Never put API keys in command-line arguments.

## Page Workflow

- First navigation is `new_tab(url)`, not `goto_url(url)`.
- Screenshots are the default way to understand and verify visible state: `capture_screenshot()`.
- Click visible targets by screenshot coordinates: `click_at_xy(x, y)`.
- Use `js(...)` for DOM inspection or extraction when coordinates are the wrong tool.
- After navigation, call `wait_for_load()`.
- If the current tab is stale or internal, call `ensure_real_tab()`.
- If redirected to a login wall, stop and ask the user. Do not type credentials from screenshots.
- For anything helpers do not cover, use raw CDP: `cdp("Domain.method", params)`.

## Interaction Skills

If you get stuck on a browser mechanic, check `interaction-skills/` for focused guidance:

- connection.md
- cookies.md
- cross-origin-iframes.md
- dialogs.md
- downloads.md
- drag-and-drop.md
- dropdowns.md
- iframes.md
- network-requests.md
- print-as-pdf.md
- profile-sync.md
- screenshots.md
- scrolling.md
- shadow-dom.md
- tabs.md
- uploads.md
- viewport.md

## Domain Skills

Domain skills are off by default. If `BH_DOMAIN_SKILLS=1` and the task is site-specific, read every file in `agent-workspace/domain-skills/<site>/` before inventing an approach.

When enabled, `goto_url(...)` returns up to 10 matching skill filenames for the current host.
