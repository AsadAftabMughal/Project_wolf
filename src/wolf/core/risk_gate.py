from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

@dataclass(frozen=True)
class RiskConfig:
    max_risk_pct: Decimal = Decimal("1")
    daily_loss_limit_pct: Decimal = Decimal("3")
    max_trades_per_day: int = 3
    max_open_positions: int = 2
    min_reward_risk: Decimal = Decimal("1.5")
    # UTC windows. London shifts by an hour with daylight saving; fix later with zoneinfo.
    windows_utc: tuple = ((time(7, 0), time(11, 0)), (time(12, 30), time(16, 0)))
    friday_cutoff_utc: time = time(14, 0)

@dataclass(frozen=True)
class AccountState:
    balance: Decimal          # balance at the start of the day
    daily_pnl: Decimal
    trades_today: int
    open_positions: int
    kill_switch: bool = False

@dataclass(frozen=True)
class Proposal:
    lots: Decimal
    stop_distance: Decimal
    target_distance: Decimal
    value_per_unit: Decimal
    when_utc: datetime

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reasons: tuple

def check(cfg, state, p):
    """PASS or BLOCK. Every failing rule is reported, not just the first."""
    if p.when_utc.tzinfo is None or p.when_utc.utcoffset() != timedelta(0):
        raise ValueError("when_utc must be timezone-aware UTC")
    if p.stop_distance <= 0 or p.value_per_unit <= 0 or p.lots <= 0:
        raise ValueError("invalid proposal")
    r = []
    if state.kill_switch:
        r.append("KILL_SWITCH")
    if p.lots * p.stop_distance * p.value_per_unit > state.balance * cfg.max_risk_pct / 100:
        r.append("RISK_TOO_HIGH")
    if state.daily_pnl <= -(state.balance * cfg.daily_loss_limit_pct / 100):
        r.append("DAILY_LOSS_LIMIT")
    if state.trades_today >= cfg.max_trades_per_day:
        r.append("MAX_TRADES")
    if state.open_positions >= cfg.max_open_positions:
        r.append("MAX_OPEN")
    if p.target_distance / p.stop_distance < cfg.min_reward_risk:
        r.append("REWARD_RISK")
    t = p.when_utc.time()
    in_window = p.when_utc.weekday() < 5 and any(a <= t < b for a, b in cfg.windows_utc)
    if not in_window:
        r.append("OUTSIDE_WINDOW")
    elif p.when_utc.weekday() == 4 and t >= cfg.friday_cutoff_utc:
        r.append("FRIDAY_CUTOFF")
    return Decision(allowed=not r, reasons=tuple(r))
