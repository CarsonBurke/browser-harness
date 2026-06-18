from browser_harness import manager_daemon
from browser_harness import auth
from browser_harness.manager_daemon import Manager


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"ok": true}'


def _manager_with_lease(tmp_path):
    manager = Manager(tmp_path)
    lease = manager._allocate_lease("run-1", "agent-1", "cloud", "clean")
    manager.leases[lease.browser_id] = lease
    return manager, lease


def test_lock_is_exclusive_across_client_processes(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)

    first = manager.handle({
        "op": "lock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-1",
        "browser_id": lease.browser_id,
    })
    second = manager.handle({
        "op": "lock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-2",
        "browser_id": lease.browser_id,
    })

    assert first["ok"] is True
    assert second["ok"] is False
    assert second["state"] == "busy"


def test_unlock_requires_same_client_process(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)
    first = manager.handle({
        "op": "lock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-1",
        "browser_id": lease.browser_id,
    })

    wrong = manager.handle({
        "op": "unlock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-2",
        "browser_id": lease.browser_id,
        "lock_id": first["lock_id"],
    })
    second = manager.handle({
        "op": "lock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-2",
        "browser_id": lease.browser_id,
    })

    assert wrong["ok"] is True
    assert second["ok"] is False
    assert second["state"] == "busy"


def test_close_requires_explicit_id(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)

    resp = manager.handle({
        "op": "close",
        "run_id": "run-1",
        "agent_id": "agent-1",
    })

    assert resp["ok"] is False
    assert resp["state"] == "bad-request"
    assert lease.browser_id in manager.leases


def test_close_rejects_browser_busy_in_another_client(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)
    manager.handle({
        "op": "lock",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-1",
        "browser_id": lease.browser_id,
    })

    resp = manager.handle({
        "op": "close",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "client_id": "client-2",
        "browser_id": lease.browser_id,
    })

    assert resp["ok"] is False
    assert resp["state"] == "busy"
    assert lease.browser_id in manager.leases


def test_short_browser_ids_have_no_prefix(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)

    assert len(lease.browser_id) == 6
    assert not lease.browser_id.startswith("br_")


def test_cloud_live_url_is_exposed_in_ready_state(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)
    lease.cloud_live_url = "https://live.example/session"

    resp = manager.handle({
        "op": "status",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "browser_id": lease.browser_id,
    })

    assert resp["ok"] is True
    assert resp["id"] == lease.browser_id
    assert resp["live_url"] == "https://live.example/session"


def test_cloud_browser_id_is_exposed_in_ready_state(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)
    lease.cloud_browser_id = "browser-123"

    resp = manager.handle({
        "op": "status",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "browser_id": lease.browser_id,
    })

    assert resp["ok"] is True
    assert resp["id"] == lease.browser_id
    assert resp["cloud_browser_id"] == "browser-123"


def test_cloud_live_url_is_exposed_in_browser_list(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)
    lease.cloud_browser_id = "browser-123"
    lease.cloud_live_url = "https://live.example/session"

    resp = manager.handle({
        "op": "list",
        "run_id": "run-1",
        "agent_id": "agent-1",
    })

    assert resp["ok"] is True
    assert resp["browsers"] == [
        {
            "id": lease.browser_id,
            "backend": "cloud",
            "owner": "agent-1",
            "owned_by_this_agent": True,
            "shared": False,
            "state": "ready",
            "cloud_browser_id": "browser-123",
            "live_url": "https://live.example/session",
        }
    ]


def test_start_cloud_backend_fetches_missing_live_url(monkeypatch, tmp_path):
    lease = Manager(tmp_path)._allocate_lease("run-1", "agent-1", "cloud", "clean")
    calls = []

    def fake_browser_use(path, method, body=None):
        calls.append((path, method, body))
        if (path, method) == ("/browsers", "POST"):
            return {"id": "browser-123", "cdpUrl": "https://cdp.initial"}
        if (path, method) == ("/browsers/browser-123", "GET"):
            return {"id": "browser-123", "cdpUrl": "https://cdp.refreshed", "liveUrl": "https://live.example/session"}
        raise AssertionError((path, method, body))

    monkeypatch.setattr(manager_daemon.auth, "get_browser_use_api_key", lambda: "stored-key")
    monkeypatch.setattr(manager_daemon, "_browser_use", fake_browser_use)
    monkeypatch.setattr(manager_daemon, "start_harness_daemon", lambda lease: None)

    manager_daemon.start_cloud_backend(lease, proxy_country=None)

    assert calls == [
        ("/browsers", "POST", {}),
        ("/browsers/browser-123", "GET", None),
    ]
    assert lease.cloud_browser_id == "browser-123"
    assert lease.cloud_live_url == "https://live.example/session"
    assert lease.cdp_url == "https://cdp.refreshed"


def test_cloud_new_reports_auth_required(monkeypatch, tmp_path):
    manager = Manager(tmp_path)
    monkeypatch.setattr(
        "browser_harness.manager_daemon.auth.get_browser_use_api_key",
        lambda: (_ for _ in ()).throw(auth.CloudAuthRequired()),
    )

    resp = manager.handle({
        "op": "new",
        "run_id": "run-1",
        "agent_id": "agent-1",
        "backend": "cloud",
    })

    assert resp["ok"] is False
    assert resp["state"] == "cloud-auth-required"
    assert "browser-harness auth login" in resp["reason"]


def test_browser_use_api_uses_auth_resolution(monkeypatch):
    captured = []
    monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
    monkeypatch.setattr(manager_daemon.auth, "get_browser_use_api_key", lambda: "stored-key")
    monkeypatch.setattr(
        manager_daemon.urllib.request,
        "urlopen",
        lambda req, timeout=60: captured.append(req) or _FakeResponse(),
    )

    assert manager_daemon._browser_use("/browsers", "POST", {}) == {"ok": True}

    assert captured
    assert captured[0].get_header("X-browser-use-api-key") == "stored-key"


def test_find_browser_binary_skips_unusable_path_candidate_and_uses_mac_app(monkeypatch):
    monkeypatch.delenv("BH_CHROME_PATH", raising=False)
    monkeypatch.delenv("CHROME_PATH", raising=False)
    monkeypatch.setattr(manager_daemon.sys, "platform", "darwin")
    monkeypatch.setattr(manager_daemon.shutil, "which", lambda name: "/broken/chromium" if name == "chromium" else None)
    monkeypatch.setattr(manager_daemon, "MAC_BROWSER_PATHS", ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",))
    monkeypatch.setattr(
        manager_daemon,
        "_browser_binary_usable",
        lambda path: path == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )

    assert manager_daemon.find_browser_binary() == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
