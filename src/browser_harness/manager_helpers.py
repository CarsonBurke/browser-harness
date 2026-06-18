"""Model-visible browser lifecycle helpers."""
from __future__ import annotations

from . import context
from . import local_profiles
from . import manager_client


def browser_status():
    """Return lifecycle state for the active browser binding."""
    return manager_client.status()


def browser_profiles(verbose=False):
    """List local Chrome/Chromium profiles for browser_use_profile(...)."""
    return local_profiles.list_browser_profiles_payload(verbose=verbose)


def browser_use_profile(profile_id):
    """Select the local browser profile future normal helper calls should use."""
    return local_profiles.use_browser_profile(profile_id)


def _manager_backend(kind, backend=None):
    value = backend if backend is not None else kind
    if value in (None, "private", "managed"):
        return "managed"
    if value == "cloud":
        return "cloud"
    raise ValueError("browser_new kind must be 'private' or 'cloud'")


def browser_new(kind="private", *, backend=None, profile="clean", proxy_country=None, reason=None):
    """Create a browser, switch this agent to it, and return concise state."""
    resp = manager_client.new_browser(
        backend=_manager_backend(kind, backend),
        profile=profile,
        proxy_country=proxy_country,
        reason=reason,
    )
    binding = manager_client.binding_from_response(resp)
    manager_client.acquire_execution_for_binding(binding)
    context.activate_binding(binding)
    return manager_client.public_state(resp)


def browser_switch(browser_id):
    """Switch this agent/process to an existing allowed browser id."""
    resp = manager_client.switch_browser(browser_id)
    binding = manager_client.binding_from_response(resp)
    manager_client.acquire_execution_for_binding(binding)
    context.activate_binding(binding)
    return manager_client.public_state(resp)


def browser_list():
    """List concise browser ids visible to this run/agent."""
    return manager_client.list_browsers()


def browser_close(browser_id=None):
    """Close private browsers or release this agent's access to shared browsers."""
    active = context.get_active_binding()
    closing_active = browser_id is None or (active and active.browser_id == browser_id)
    if closing_active:
        manager_client.release_active_execution_lock()
    resp = manager_client.close_browser(browser_id)
    if closing_active:
        context.clear_active_binding()
    return manager_client.public_state(resp)
