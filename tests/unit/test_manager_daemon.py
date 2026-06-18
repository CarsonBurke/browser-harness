from browser_harness.manager_daemon import Manager


def _manager_with_lease(tmp_path):
    manager = Manager(tmp_path)
    lease = manager._allocate_lease("run-1", "agent-1", "cloud", "clean")
    manager.leases[lease.browser_id] = lease
    manager.active_by_agent["run-1/agent-1"] = lease.browser_id
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


def test_close_rejects_other_runs(tmp_path):
    manager, lease = _manager_with_lease(tmp_path)

    resp = manager.handle({
        "op": "close",
        "run_id": "other-run",
        "agent_id": "agent-1",
        "browser_id": lease.browser_id,
    })

    assert resp["ok"] is False
    assert resp["state"] == "forbidden"
    assert lease.browser_id in manager.leases
