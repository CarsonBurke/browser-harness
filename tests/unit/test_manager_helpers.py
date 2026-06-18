import pytest

from browser_harness import context, manager_helpers


def _manager_response(tmp_path):
    return {
        "ok": True,
        "ready": True,
        "state": "ready",
        "id": "abc123",
        "backend": "private",
        "shared": False,
        "binding": {
            "browser_id": "abc123",
            "bu_name": "bh_123",
            "runtime_dir": str(tmp_path / "r"),
            "tmp_dir": str(tmp_path / "t"),
            "download_dir": str(tmp_path / "downloads"),
            "artifact_dir": str(tmp_path / "artifacts"),
            "cdp_url": "http://127.0.0.1:4567",
            "cdp_ws": None,
        },
    }


def test_browser_new_creates_without_activating_binding(monkeypatch, tmp_path):
    acquired = []
    old = context.get_active_binding()
    try:
        monkeypatch.setattr(manager_helpers.manager_client, "new_browser", lambda *args, **kwargs: _manager_response(tmp_path))
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "acquire_execution_for_binding",
            lambda binding: acquired.append(binding.browser_id),
        )

        state = manager_helpers.browser_new(backend="managed", reason="test")
        binding = context.get_active_binding()
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert state["id"] == "abc123"
    assert "binding" not in state
    assert binding == old
    assert acquired == []


def test_browser_new_private_maps_to_managed_backend(monkeypatch, tmp_path):
    calls = []
    old = context.get_active_binding()
    try:
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "new_browser",
            lambda *args, **kwargs: calls.append((args, kwargs)) or _manager_response(tmp_path),
        )
        manager_helpers.browser_new("private", reason="test")
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert calls[0][1]["backend"] == "managed"


def test_browser_new_cloud_maps_to_cloud_backend(monkeypatch, tmp_path):
    calls = []
    old = context.get_active_binding()
    try:
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "new_browser",
            lambda *args, **kwargs: calls.append((args, kwargs)) or _manager_response(tmp_path),
        )
        manager_helpers.browser_new("cloud")
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert calls[0][1]["backend"] == "cloud"


def test_browser_profiles_returns_concise_payload(monkeypatch):
    monkeypatch.setattr(
        manager_helpers.local_profiles,
        "list_browser_profiles_payload",
        lambda verbose=False: {"selected": "google-chrome:Default", "profiles": []},
    )

    assert manager_helpers.browser_profiles() == {
        "selected": "google-chrome:Default",
        "profiles": [],
    }


def test_browser_use_profile_returns_selected_profile(monkeypatch):
    monkeypatch.setattr(
        manager_helpers.local_profiles,
        "use_browser_profile",
        lambda profile_id: {"selected": profile_id, "label": "Google Chrome - Default"},
    )

    assert manager_helpers.browser_use_profile("google-chrome:Default") == {
        "selected": "google-chrome:Default",
        "label": "Google Chrome - Default",
    }


def test_browser_select_activates_binding_and_acquires_lock(monkeypatch, tmp_path):
    acquired = []
    old = context.get_active_binding()
    try:
        monkeypatch.setattr(manager_helpers.manager_client, "switch_browser", lambda browser_id: _manager_response(tmp_path))
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "acquire_execution_for_binding",
            lambda binding: acquired.append(binding.browser_id),
        )

        state = manager_helpers.browser("abc123")
        binding = context.get_active_binding()
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert state["id"] == "abc123"
    assert "binding" not in state
    assert binding is not None
    assert binding.bu_name == "bh_123"
    assert acquired == ["abc123"]


def test_browser_switch_aliases_browser(monkeypatch):
    calls = []
    monkeypatch.setattr(manager_helpers, "browser", lambda browser_id: calls.append(browser_id) or {"id": browser_id})

    assert manager_helpers.browser_switch("abc123") == {"id": "abc123"}
    assert calls == ["abc123"]


def test_browser_does_not_activate_binding_when_lock_fails(monkeypatch, tmp_path):
    old = context.get_active_binding()
    previous = context.BrowserBinding(
        browser_id="old123",
        bu_name="bh_old",
        runtime_dir=tmp_path / "old-r",
        tmp_dir=tmp_path / "old-t",
        manager_mode=True,
    )
    context.activate_binding(previous)
    try:
        monkeypatch.setattr(manager_helpers.manager_client, "switch_browser", lambda browser_id: _manager_response(tmp_path))
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "acquire_execution_for_binding",
            lambda binding: (_ for _ in ()).throw(
                manager_helpers.manager_client.ManagerError({
                    "state": "busy",
                    "reason": "browser is currently active in another browser-harness process",
                })
            ),
        )

        with pytest.raises(manager_helpers.manager_client.ManagerError, match="currently active"):
            manager_helpers.browser("abc123")
        active = context.get_active_binding()
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert active == previous


def test_browser_close_releases_lock_and_clears_active_binding(monkeypatch, tmp_path):
    released = []
    closed = []
    old = context.get_active_binding()
    context.activate_binding(context.BrowserBinding(
        browser_id="abc123",
        bu_name="bh_123",
        runtime_dir=tmp_path / "r",
        tmp_dir=tmp_path / "t",
        manager_mode=True,
    ))
    try:
        monkeypatch.setattr(manager_helpers.manager_client, "release_active_execution_lock", lambda: released.append(True))
        monkeypatch.setattr(
            manager_helpers.manager_client,
            "close_browser",
            lambda browser_id=None: closed.append(browser_id) or {"ok": True, "state": "closed", "id": "abc123"},
        )

        state = manager_helpers.browser_close("abc123")
        active = context.get_active_binding()
    finally:
        if old is not None:
            context.activate_binding(old)
        else:
            context.clear_active_binding()

    assert state == {"state": "closed", "id": "abc123"}
    assert released == [True]
    assert closed == ["abc123"]
    assert active is None


def test_browser_close_requires_explicit_id():
    with pytest.raises(ValueError, match="browser_close\\(id\\)"):
        manager_helpers.browser_close()
