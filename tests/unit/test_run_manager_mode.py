import os
import sys
from io import StringIO
from unittest.mock import patch

from browser_harness import run


def test_manager_mode_skips_legacy_daemon_start(monkeypatch):
    monkeypatch.setenv("BH_MANAGER_SOCKET", "/tmp/nonexistent-manager.sock")
    stdout = StringIO()
    fake_stdin = StringIO("print('manager mode ok')")

    with patch.object(sys, "argv", ["browser-harness"]), \
         patch("sys.stdin", fake_stdin), \
         patch("sys.stdout", stdout), \
         patch("browser_harness.run.print_update_banner"), \
         patch("browser_harness.run.ensure_daemon") as ensure_daemon:
        run.main()

    ensure_daemon.assert_not_called()
    assert stdout.getvalue().strip() == "manager mode ok"


def test_manager_helper_call_enables_manager_mode_without_env(monkeypatch):
    monkeypatch.delenv("BH_MANAGER_SOCKET", raising=False)
    monkeypatch.delenv("BH_MANAGER_MODE", raising=False)
    stdout = StringIO()
    fake_stdin = StringIO("print(browser_status())")

    with patch.object(sys, "argv", ["browser-harness"]), \
         patch("sys.stdin", fake_stdin), \
         patch("sys.stdout", stdout), \
         patch("browser_harness.run.print_update_banner"), \
         patch("browser_harness.run.ensure_daemon") as ensure_daemon, \
         patch("browser_harness.run.browser_status", lambda: "manager helper mode ok"), \
         patch("browser_harness.run.manager_client.release_active_execution_lock"):
        run.main()

    ensure_daemon.assert_not_called()
    assert stdout.getvalue().strip() == "manager helper mode ok"
    assert "BH_MANAGER_MODE" in os.environ


def test_manager_mode_releases_execution_lock_on_exception(monkeypatch):
    monkeypatch.setenv("BH_MANAGER_SOCKET", "/tmp/nonexistent-manager.sock")
    fake_stdin = StringIO("raise RuntimeError('boom')")
    released = []

    with patch.object(sys, "argv", ["browser-harness"]), \
         patch("sys.stdin", fake_stdin), \
         patch("browser_harness.run.print_update_banner"), \
         patch("browser_harness.run.manager_client.release_active_execution_lock", lambda: released.append(True)):
        try:
            run.main()
        except RuntimeError as e:
            assert str(e) == "boom"
        else:
            raise AssertionError("expected RuntimeError")

    assert released == [True]
