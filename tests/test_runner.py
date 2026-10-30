from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from wolf import killswitch
from wolf.broker.fake import FakeBroker
from wolf.core.risk_gate import RiskConfig
from wolf.executor import Signal
from wolf.heartbeat import read_heartbeat
from wolf.ledger import DayLedger
from wolf.runner import heartbeat, process_signal

T = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
CFG = RiskConfig()


def setup(balance="1000"):
    b = FakeBroker(balance=balance, quote_time=T)
    return b, DayLedger(b, T)


def sig(t, stop="3", target="6"):
    return Signal("XAUUSD", "buy", D(stop), D(target), t)


def test_placed_trade_counts(tmp_path):
    b, led = setup()
    out = process_signal(b, CFG, led, sig(T), str(tmp_path / "KILL"))
    assert out.status == "PLACED"
    assert led.state(T).trades_today == 1


def test_fourth_trade_blocked_by_daily_cap(tmp_path):
    b, led = setup()
    kill = str(tmp_path / "KILL")
    for i in range(3):
        t = T + timedelta(minutes=15 * i)
        b.set_quote("2000.00", "2000.30", t)
        out = process_signal(b, CFG, led, sig(t), kill)
        assert out.status == "PLACED"
        b.close_position(out.position_id)
    t = T + timedelta(minutes=45)
    b.set_quote("2000.00", "2000.30", t)
    out = process_signal(b, CFG, led, sig(t), kill)
    assert out.status == "BLOCKED" and "MAX_TRADES" in out.reasons


def test_kill_file_blocks_and_counts_nothing(tmp_path):
    b, led = setup()
    kill = str(tmp_path / "KILL")
    killswitch.engage(kill, "test")
    out = process_signal(b, CFG, led, sig(T), kill)
    assert out.status == "BLOCKED" and out.reasons == ("KILL_SWITCH",)
    assert led.state(T).trades_today == 0 and b.positions() == ()


def test_small_account_skip_counts_nothing(tmp_path):
    b, led = setup("300")
    out = process_signal(b, CFG, led, sig(T, "5", "10"), str(tmp_path / "KILL"))
    assert out.status == "SKIPPED_SIZE"
    assert led.state(T).trades_today == 0


def test_heartbeat_reports_open_positions(tmp_path):
    b, led = setup()
    process_signal(b, CFG, led, sig(T), str(tmp_path / "KILL"))
    heartbeat(b, str(tmp_path / "hb"), T)
    hb = read_heartbeat(str(tmp_path / "hb"), "trader")
    assert hb.positions_open == 1 and hb.time_utc == T
