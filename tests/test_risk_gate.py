from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D
import pytest
from wolf.core.risk_gate import RiskConfig, AccountState, Proposal, check

CFG = RiskConfig()
STATE = AccountState(balance=D("1000"), daily_pnl=D("0"), trades_today=0, open_positions=0)
TUE_0800 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
PROP = Proposal(lots=D("0.03"), stop_distance=D("3"), target_distance=D("6"),
                value_per_unit=D("100"), when_utc=TUE_0800,
                spread=D("0.30"), quote_age_seconds=D("1"))

def reasons(state=STATE, prop=PROP):
    return set(check(CFG, state, prop).reasons)

def test_good_trade_passes():
    d = check(CFG, STATE, PROP)
    assert d.allowed and d.reasons == ()

def test_kill_switch_blocks():
    assert reasons(state=replace(STATE, kill_switch=True)) == {"KILL_SWITCH"}

def test_risk_too_high():
    assert reasons(prop=replace(PROP, lots=D("0.04"))) == {"RISK_TOO_HIGH"}

def test_daily_loss_limit():
    assert reasons(state=replace(STATE, daily_pnl=D("-30"))) == {"DAILY_LOSS_LIMIT"}
    assert reasons(state=replace(STATE, daily_pnl=D("-29"))) == set()

def test_max_trades():
    assert reasons(state=replace(STATE, trades_today=3)) == {"MAX_TRADES"}

def test_max_open_positions():
    assert reasons(state=replace(STATE, open_positions=2)) == {"MAX_OPEN"}

def test_reward_risk_too_low():
    assert reasons(prop=replace(PROP, target_distance=D("3"))) == {"REWARD_RISK"}

def test_outside_window():
    t = datetime(2026, 11, 3, 11, 30, tzinfo=timezone.utc)
    assert reasons(prop=replace(PROP, when_utc=t)) == {"OUTSIDE_WINDOW"}

def test_weekend_blocked():
    t = datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc)
    assert reasons(prop=replace(PROP, when_utc=t)) == {"OUTSIDE_WINDOW"}

def test_friday_cutoff():
    ok = datetime(2026, 11, 6, 13, 0, tzinfo=timezone.utc)
    late = datetime(2026, 11, 6, 14, 30, tzinfo=timezone.utc)
    assert reasons(prop=replace(PROP, when_utc=ok)) == set()
    assert reasons(prop=replace(PROP, when_utc=late)) == {"FRIDAY_CUTOFF"}

def test_all_reasons_are_collected():
    s = replace(STATE, kill_switch=True, trades_today=3)
    assert reasons(state=s) == {"KILL_SWITCH", "MAX_TRADES"}

def test_naive_time_rejected():
    with pytest.raises(ValueError):
        check(CFG, STATE, replace(PROP, when_utc=datetime(2026, 11, 3, 8, 0)))

def test_bad_stop_rejected():
    with pytest.raises(ValueError):
        check(CFG, STATE, replace(PROP, stop_distance=D("0")))


def test_spread_too_wide():
    assert reasons(prop=replace(PROP, spread=D("0.61"))) == {"SPREAD_TOO_WIDE"}


def test_spread_at_limit_passes():
    assert reasons(prop=replace(PROP, spread=D("0.60"))) == set()


def test_unknown_spread_blocks():
    assert reasons(prop=replace(PROP, spread=None)) == {"SPREAD_TOO_WIDE"}


def test_stale_quote():
    assert reasons(prop=replace(PROP, quote_age_seconds=D("6"))) == {"QUOTE_STALE"}


def test_quote_age_at_limit_passes():
    assert reasons(prop=replace(PROP, quote_age_seconds=D("5"))) == set()


def test_unknown_or_future_quote_blocks():
    assert reasons(prop=replace(PROP, quote_age_seconds=None)) == {"QUOTE_STALE"}
    assert reasons(prop=replace(PROP, quote_age_seconds=D("-1"))) == {"QUOTE_STALE"}
