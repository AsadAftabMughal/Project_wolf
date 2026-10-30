from decimal import Decimal as D
import pytest
from wolf.core.sizing import position_size

def size(balance, stop):
    return position_size(balance, 1, stop, 100, "0.01", "0.01", "5")

def test_skips_when_min_lot_risks_too_much():
    assert size(300, 5) is None

def test_sizes_down_to_lot_step():
    assert size(1000, 3) == D("0.03")

def test_loss_at_stop_never_exceeds_risk():
    for balance in (300, 1000, 5000):
        for stop in ("1.5", "3", "7.25", "12"):
            lots = size(balance, stop)
            if lots is not None:
                assert lots * D(stop) * 100 <= D(balance) * D("0.01")

def test_rejects_bad_stop():
    with pytest.raises(ValueError):
        size(300, 0)
