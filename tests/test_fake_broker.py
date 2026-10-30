from decimal import Decimal as D
import pytest
from wolf.broker.base import OrderRequest
from wolf.broker.fake import FakeBroker
from wolf.core.sizing import position_size


def order(**kw):
    base = dict(account_id="demo-1", symbol="XAUUSD", side="buy",
                lots=D("0.01"), stop_loss=D("1995"))
    base.update(kw)
    return OrderRequest(**base)


def test_no_order_without_stop():
    with pytest.raises(ValueError):
        order(stop_loss=None)


def test_stop_is_required_argument():
    with pytest.raises(TypeError):
        OrderRequest(account_id="demo-1", symbol="XAUUSD", side="buy",
                     lots=D("0.01"))


def test_bad_side():
    with pytest.raises(ValueError):
        order(side="hold")


def test_fill_prices_use_spread():
    b = FakeBroker()
    assert b.place_order(order()).fill_price == D("2000.30")
    r = b.place_order(order(side="sell", stop_loss=D("2005")))
    assert r.accepted and r.fill_price == D("2000.00")


def test_stop_on_wrong_side():
    b = FakeBroker()
    assert b.place_order(order(stop_loss=D("2001"))).reject_reason == "BAD_STOP"
    r = b.place_order(order(side="sell", stop_loss=D("1995")))
    assert r.reject_reason == "BAD_STOP"


def test_target_on_wrong_side():
    b = FakeBroker()
    r = b.place_order(order(take_profit=D("1999")))
    assert r.reject_reason == "BAD_TARGET"


def test_bad_volume():
    b = FakeBroker()
    for lots in ("0.005", "0.015", "6"):
        r = b.place_order(order(lots=D(lots)))
        assert r.reject_reason == "BAD_VOLUME"


def test_wrong_account():
    b = FakeBroker()
    assert b.place_order(order(account_id="other")).reject_reason == "WRONG_ACCOUNT"


def test_close_updates_balance():
    b = FakeBroker(balance="300")
    r = b.place_order(order())
    b.set_quote("2005.30", "2005.60")
    pnl = b.close_position(r.position_id)
    assert pnl == D("5.00")
    assert b.account().balance == D("305.00")


def test_position_removed_after_close():
    b = FakeBroker()
    r = b.place_order(order())
    assert len(b.positions()) == 1
    b.close_position(r.position_id)
    assert b.positions() == ()


def test_loss_at_stop_within_risk():
    b = FakeBroker(balance="1000")
    spec = b.symbol_spec("XAUUSD")
    stop_distance = D("3")
    lots = position_size(b.account().balance, 1, stop_distance,
                         spec.value_per_unit, spec.min_lot,
                         spec.lot_step, spec.max_lot)
    entry = b.quote("XAUUSD").ask
    r = b.place_order(order(lots=lots, stop_loss=entry - stop_distance))
    assert r.accepted
    b.set_quote("1997.30", "1997.60")
    assert b.close_position(r.position_id) >= D("-10")
