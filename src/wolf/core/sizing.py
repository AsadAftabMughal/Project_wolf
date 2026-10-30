from decimal import Decimal, ROUND_DOWN

def _d(x):
    return Decimal(str(x))

def position_size(balance, risk_pct, stop_distance, value_per_unit,
                  min_lot, lot_step, max_lot):
    """Lots to trade, or None if the trade must be skipped.

    risk_pct is in percent (1 means 1%). value_per_unit is the account-currency
    gain or loss per 1.0 price move per 1 lot. Never rounds up.
    """
    balance, risk_pct, stop = _d(balance), _d(risk_pct), _d(stop_distance)
    value, min_lot, step, max_lot = _d(value_per_unit), _d(min_lot), _d(lot_step), _d(max_lot)
    if stop <= 0 or value <= 0 or balance <= 0 or step <= 0:
        raise ValueError("invalid input")
    max_loss = balance * risk_pct / 100
    raw = max_loss / (stop * value)
    lots = (raw / step).to_integral_value(rounding=ROUND_DOWN) * step
    if lots < min_lot:
        return None
    return min(lots, max_lot)
