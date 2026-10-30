from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from wolf.broker.base import OrderRequest
from wolf.broker.fake import FakeBroker

T = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
T1 = T + timedelta(seconds=1)


def open_pos(side, stop, target):
    b = FakeBroker(balance="1000", quote_time=T)
    r = b.place_order(OrderRequest("demo-1", "XAUUSD", side, D("0.01"),
                                   D(stop), D(target)))
    assert r.accepted
    return b


def test_buy_stop_hit():
    b = open_pos("buy", "1997.30", "2006.30")
    closed = b.tick("1997.00", "1997.30", T1)
    assert [(c[2]) for c in closed] == ["STOP"]
    assert closed[0][1] == D("-3.30")
    assert b.account().balance == D("996.70")
    assert b.positions() == ()


def test_buy_target_hit():
    b = open_pos("buy", "1997.30", "2006.30")
    closed = b.tick("2006.40", "2006.70", T1)
    assert closed[0][2] == "TARGET" and closed[0][1] == D("6.10")


def test_sell_stop_hit():
    b = open_pos("sell", "2003.00", "1994.00")
    closed = b.tick("2002.80", "2003.10", T1)
    assert closed[0][2] == "STOP" and closed[0][1] == D("-3.10")


def test_no_hit_leaves_position_open():
    b = open_pos("buy", "1997.30", "2006.30")
    assert b.tick("2001.00", "2001.30", T1) == []
    assert len(b.positions()) == 1


def test_gap_past_stop_loses_more_than_planned():
    b = open_pos("buy", "1997.30", "2006.30")
    closed = b.tick("1990.00", "1990.30", T1)
    assert closed[0][1] < D("-3.00")
