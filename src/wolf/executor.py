from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from wolf.broker.base import Broker, OrderRequest
from wolf.core.risk_gate import Proposal, check
from wolf.core.sizing import position_size


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "buy" or "sell"
    stop_distance: Decimal
    target_distance: Decimal
    when_utc: datetime


@dataclass(frozen=True)
class Outcome:
    status: str  # PLACED, BLOCKED, SKIPPED_SIZE or REJECTED
    reasons: tuple = ()
    lots: Optional[Decimal] = None
    position_id: Optional[str] = None
    fill_price: Optional[Decimal] = None


def execute(broker: Broker, cfg, state, signal: Signal) -> Outcome:
    """Size, gate, then order. Nothing reaches the broker unless every step passes."""
    if signal.side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")

    # Our bookkeeping must match the broker's reality, or we do nothing.
    if len(broker.positions()) != state.open_positions:
        return Outcome("BLOCKED", ("STATE_MISMATCH",))

    spec = broker.symbol_spec(signal.symbol)
    lots = position_size(state.balance, cfg.max_risk_pct, signal.stop_distance,
                         spec.value_per_unit, spec.min_lot, spec.lot_step,
                         spec.max_lot)
    if lots is None:
        return Outcome("SKIPPED_SIZE", ("MIN_LOT_RISKS_TOO_MUCH",))

    decision = check(cfg, state, Proposal(lots, signal.stop_distance,
                                          signal.target_distance,
                                          spec.value_per_unit, signal.when_utc))
    if not decision.allowed:
        return Outcome("BLOCKED", decision.reasons, lots=lots)

    q = broker.quote(signal.symbol)
    if signal.side == "buy":
        entry = q.ask
        stop = entry - signal.stop_distance
        target = entry + signal.target_distance
    else:
        entry = q.bid
        stop = entry + signal.stop_distance
        target = entry - signal.target_distance

    result = broker.place_order(OrderRequest(
        account_id=broker.account().account_id, symbol=signal.symbol,
        side=signal.side, lots=lots, stop_loss=stop, take_profit=target))
    if not result.accepted:
        return Outcome("REJECTED", (result.reject_reason,), lots=lots)
    return Outcome("PLACED", (), lots, result.position_id, result.fill_price)
