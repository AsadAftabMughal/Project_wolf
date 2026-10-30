from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D
import pytest
from wolf.broker.base import OrderResult
from wolf.broker.fake import FakeBroker
from wolf.core.risk_gate import AccountState, RiskConfig
from wolf.executor import Signal, execute

CFG = RiskConfig()
STATE = AccountState(balance=D("1000"), daily_pnl=D("0"),
                     trades_today=0, open_positions=0)
TUE_0800 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
TUE_1130 = datetime(2026, 11, 3, 11, 30, tzinfo=timezone.utc)
SIG = Signal("XAUUSD", "buy", D("3"), D("6"), TUE_0800)


class Spy(FakeBroker):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.placed = 0

    def place_order(self, order):
        self.placed += 1
        return super().place_order(order)


class Rejecting(Spy):
    def place_order(self, order):
        self.placed += 1
        return OrderResult(False, None, None, "NOPE")


def broker(balance="1000"):
    return Spy(balance=balance)


def test_buy_is_sized_and_levels_are_set():
    b = broker()
    out = execute(b, CFG, STATE, SIG)
    assert out.status == "PLACED"
    assert out.lots == D("0.03")
    assert out.fill_price == D("2000.30")
    pos = b.positions()[0]
    assert pos.stop_loss == D("1997.30")
    assert pos.take_profit == D("2006.30")


def test_sell_levels_are_mirrored():
    b = broker()
    out = execute(b, CFG, STATE, replace(SIG, side="sell"))
    assert out.status == "PLACED"
    pos = b.positions()[0]
    assert pos.entry_price == D("2000.00")
    assert pos.stop_loss == D("2003.00")
    assert pos.take_profit == D("1994.00")


CASES = [
    ("KILL_SWITCH", replace(STATE, kill_switch=True), SIG),
    ("MAX_TRADES", replace(STATE, trades_today=3), SIG),
    ("OUTSIDE_WINDOW", STATE, replace(SIG, when_utc=TUE_1130)),
    ("REWARD_RISK", STATE, replace(SIG, target_distance=D("3"))),
    ("DAILY_LOSS_LIMIT", replace(STATE, daily_pnl=D("-30")), SIG),
]


@pytest.mark.parametrize("reason,state,sig", CASES)
def test_blocked_trade_never_reaches_broker(reason, state, sig):
    b = broker()
    out = execute(b, CFG, state, sig)
    assert out.status == "BLOCKED"
    assert reason in out.reasons
    assert b.placed == 0
    assert b.positions() == ()


def test_small_account_skips_instead_of_sizing_up():
    b = broker("300")
    state = replace(STATE, balance=D("300"))
    out = execute(b, CFG, state, replace(SIG, stop_distance=D("5"),
                                         target_distance=D("10")))
    assert out.status == "SKIPPED_SIZE"
    assert b.placed == 0


def test_broker_rejection_is_reported():
    b = Rejecting(balance="1000")
    out = execute(b, CFG, STATE, SIG)
    assert out.status == "REJECTED"
    assert out.reasons == ("NOPE",)
    assert b.placed == 1


def test_state_mismatch_blocks():
    b = broker()
    out = execute(b, CFG, replace(STATE, open_positions=1), SIG)
    assert out.status == "BLOCKED"
    assert out.reasons == ("STATE_MISMATCH",)
    assert b.placed == 0


def test_naive_time_raises_and_places_nothing():
    b = broker()
    with pytest.raises(ValueError):
        execute(b, CFG, STATE, replace(SIG, when_utc=datetime(2026, 11, 3, 8, 0)))
    assert b.placed == 0


def test_bad_side_raises_and_places_nothing():
    b = broker()
    with pytest.raises(ValueError):
        execute(b, CFG, STATE, replace(SIG, side="hold"))
    assert b.placed == 0


def test_loss_at_stop_stays_within_one_percent():
    b = broker()
    out = execute(b, CFG, STATE, SIG)
    b.set_quote("1997.30", "1997.60")
    assert b.close_position(out.position_id) >= D("-10")
