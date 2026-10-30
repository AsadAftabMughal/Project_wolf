from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AccountInfo:
    account_id: str
    balance: Decimal
    equity: Decimal


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    min_lot: Decimal
    lot_step: Decimal
    max_lot: Decimal
    value_per_unit: Decimal  # account-currency P&L per 1.0 price move per 1 lot


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: Decimal
    ask: Decimal
    time_utc: datetime


@dataclass(frozen=True)
class OrderRequest:
    account_id: str
    symbol: str
    side: str  # "buy" or "sell"
    lots: Decimal
    stop_loss: Decimal  # mandatory: no order exists without one
    take_profit: Optional[Decimal] = None

    def __post_init__(self):
        if self.side not in ("buy", "sell"):
            raise ValueError("side must be buy or sell")
        if self.lots <= 0:
            raise ValueError("lots must be positive")
        if self.stop_loss is None or self.stop_loss <= 0:
            raise ValueError("a stop loss is mandatory")
        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("invalid take profit")


@dataclass(frozen=True)
class Position:
    position_id: str
    account_id: str
    symbol: str
    side: str
    lots: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Optional[Decimal]


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    position_id: Optional[str]
    fill_price: Optional[Decimal]
    reject_reason: Optional[str]


class Broker(ABC):
    """Every broker (cTrader first) implements exactly this."""

    @abstractmethod
    def account(self) -> AccountInfo: ...

    @abstractmethod
    def symbol_spec(self, symbol: str) -> SymbolSpec: ...

    @abstractmethod
    def quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def positions(self) -> tuple: ...

    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResult: ...

    @abstractmethod
    def close_position(self, position_id: str) -> Decimal: ...
