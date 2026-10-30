from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from wolf.broker.base import OrderRequest
from wolf.broker.fake import FakeBroker
from wolf.ledger import DayLedger

T = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)


def make():
    b = FakeBroker(balance="1000", quote_time=T)
    return b, DayLedger(b, T)


def test_initial_state():
    b, led = make()
    s = led.state(T)
    assert s.balance == D("1000") and s.daily_pnl == 0
    assert s.trades_today == 0 and s.open_positions == 0 and not s.kill_switch


def test_record_open_counts_trades():
    b, led = make()
    led.record_open(T)
    led.record_open(T)
    assert led.state(T).trades_today == 2


def test_realized_loss_shows_in_daily_pnl():
    b, led = make()
    r = b.place_order(OrderRequest("demo-1", "XAUUSD", "buy", D("0.01"), D("1990")))
    assert led.state(T).open_positions == 1
    b.set_quote("1997.30", "1997.60", T)
    b.close_position(r.position_id)
    s = led.state(T)
    assert s.daily_pnl == D("-3.00")
    assert s.balance == D("1000")  # start-of-day balance stays fixed
    assert s.open_positions == 0


def test_new_day_resets():
    b, led = make()
    led.record_open(T)
    r = b.place_order(OrderRequest("demo-1", "XAUUSD", "buy", D("0.01"), D("1990")))
    b.set_quote("1997.30", "1997.60", T)
    b.close_position(r.position_id)
    s = led.state(T + timedelta(days=1))
    assert s.trades_today == 0 and s.daily_pnl == 0
    assert s.balance == D("997.00")


def test_naive_time_rejected():
    b, led = make()
    with pytest.raises(ValueError):
        led.state(datetime(2026, 11, 3, 8, 0))
    with pytest.raises(ValueError):
        DayLedger(b, datetime(2026, 11, 3, 8, 0))
