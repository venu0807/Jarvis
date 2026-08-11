"""build_summary must surface portals whose auth session expired.

run_portal now returns (results, session_ok); main() collects portals with a
dead session into needs_relogin and hands it to build_summary, which records
it so the notifier can email a "re-login required" banner. Without this, a
stale session silently turned 0 applies and there was no signal to the user.
"""
from auto_applier import build_summary


def test_needs_relogin_included():
    s = build_summary([], needs_relogin=["cutshort", "wellfound"])
    assert s["needs_relogin"] == ["cutshort", "wellfound"]


def test_needs_relogin_empty_by_default():
    s = build_summary([], needs_relogin=[])
    assert s["needs_relogin"] == []


def test_always_has_key_for_notifier():
    # notifier reads summary.get("needs_relogin") — the key must exist even
    # when no portal failed login.
    s = build_summary([])
    assert "needs_relogin" in s
