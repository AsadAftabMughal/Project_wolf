from datetime import datetime, timedelta, timezone

import pytest

from wolf.heartbeat import write_heartbeat
from wolf.observer import AlertDeduper, Finding, evaluate

T0 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)


def hb(tmp, bot, age, pos=0):
    write_heartbeat(str(tmp), bot, T0 - timedelta(seconds=age), pos)


def find(tmp, bots=("trader", "manager")):
    return {f.bot: f for f in evaluate(str(tmp), list(bots), T0)}


def test_all_ok(tmp_path):
    hb(tmp_path, "trader", 10)
    hb(tmp_path, "manager", 10)
    f = find(tmp_path)
    assert f["trader"].state == "OK" and f["manager"].state == "OK"


def test_age_boundary(tmp_path):
    hb(tmp_path, "trader", 120)
    hb(tmp_path, "manager", 121)
    f = find(tmp_path)
    assert f["trader"].state == "OK"
    assert f["manager"].state == "STALE"


def test_missing_is_warning(tmp_path):
    f = find(tmp_path, ("trader",))
    assert f["trader"].state == "MISSING" and f["trader"].severity == "WARNING"


def test_future_timestamp(tmp_path):
    hb(tmp_path, "trader", -60)
    f = find(tmp_path, ("trader",))
    assert f["trader"].state == "FUTURE" and f["trader"].severity == "WARNING"


def test_small_clock_skew_ok(tmp_path):
    hb(tmp_path, "trader", -3)
    assert find(tmp_path, ("trader",))["trader"].state == "OK"


def test_stale_without_positions_is_warning(tmp_path):
    hb(tmp_path, "trader", 300, pos=0)
    f = find(tmp_path, ("trader",))
    assert f["trader"].state == "STALE" and f["trader"].severity == "WARNING"


def test_stale_with_positions_is_critical(tmp_path):
    hb(tmp_path, "trader", 300, pos=1)
    f = find(tmp_path, ("trader",))
    assert f["trader"].severity == "CRITICAL"


def test_other_bot_exposure_makes_critical(tmp_path):
    hb(tmp_path, "trader", 0, pos=1)
    hb(tmp_path, "manager", 300, pos=0)
    f = find(tmp_path)
    assert f["manager"].severity == "CRITICAL"
    assert f["trader"].severity == "OK"


def test_ok_with_positions_is_not_an_alert(tmp_path):
    hb(tmp_path, "trader", 0, pos=2)
    hb(tmp_path, "manager", 0)
    assert AlertDeduper().messages(evaluate(str(tmp_path), ["trader", "manager"], T0), T0) == []


def stale(tmp_path):
    hb(tmp_path, "trader", 300)
    return evaluate(str(tmp_path), ["trader"], T0)


def test_dedupe_repeats_only_after_interval(tmp_path):
    f = stale(tmp_path)
    d = AlertDeduper(900)
    assert len(d.messages(f, T0)) == 1
    assert d.messages(f, T0 + timedelta(seconds=899)) == []
    assert len(d.messages(f, T0 + timedelta(seconds=900))) == 1


def test_recovery_message_once(tmp_path):
    d = AlertDeduper()
    assert len(d.messages(stale(tmp_path), T0)) == 1
    hb(tmp_path, "trader", 0)
    ok = evaluate(str(tmp_path), ["trader"], T0)
    out = d.messages(ok, T0 + timedelta(seconds=10))
    assert len(out) == 1 and out[0].startswith("RECOVERED")
    assert d.messages(ok, T0 + timedelta(seconds=20)) == []


def test_state_change_alerts_again():
    d = AlertDeduper()
    assert len(d.messages([Finding("trader", "STALE", "WARNING")], T0)) == 1
    assert len(d.messages([Finding("trader", "MISSING", "WARNING")], T0)) == 1


def test_severity_escalation_alerts_again():
    d = AlertDeduper()
    assert len(d.messages([Finding("trader", "STALE", "WARNING")], T0)) == 1
    assert len(d.messages([Finding("trader", "STALE", "CRITICAL")], T0)) == 1


def test_naive_now_rejected(tmp_path):
    with pytest.raises(ValueError):
        evaluate(str(tmp_path), ["trader"], datetime(2026, 11, 3, 8, 0))
