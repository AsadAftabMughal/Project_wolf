import itertools
from datetime import datetime, timezone
from decimal import Decimal

from .base import (AccountInfo, Broker, OrderRequest, OrderResult,
                   Position, Quote, SymbolSpec)


def _d(x):
    return Decimal(str(x))


def _reject(reason):
    return OrderResult(False, None, None, reason)


class FakeBroker(Broker):
    """In-memory broker for tests and dry runs.

    The gold spec below is a placeholder: replace it with the real demo numbers.
    """

    def __init__(self, account_id="demo-1", balance="300",
                 bid="2000.00", ask="2000.30", spec=None, quote_time=None):
        self._account_id = account_id
        self._balance = _d(balance)
        self._spec = spec or SymbolSpec("XAUUSD", _d("0.01"), _d("0.01"),
                                        _d("5"), _d("100"))
        self._quote = Quote(self._spec.symbol, _d(bid), _d(ask),
                            quote_time or datetime.now(timezone.utc))
        self._positions = {}
        self._ids = itertools.count(1)

    def set_quote(self, bid, ask, time_utc=None):
        self._quote = Quote(self._spec.symbol, _d(bid), _d(ask),
                            time_utc or self._quote.time_utc)

    def account(self):
        return AccountInfo(self._account_id, self._balance, self._balance)

    def symbol_spec(self, symbol):
        if symbol != self._spec.symbol:
            raise KeyError(symbol)
        return self._spec

    def quote(self, symbol):
        if symbol != self._spec.symbol:
            raise KeyError(symbol)
        return self._quote

    def positions(self):
        return tuple(self._positions.values())

    def place_order(self, order):
        if order.account_id != self._account_id:
            return _reject("WRONG_ACCOUNT")
        if order.symbol != self._spec.symbol:
            return _reject("UNKNOWN_SYMBOL")
        s = self._spec
        if (order.lots < s.min_lot or order.lots > s.max_lot
                or order.lots % s.lot_step != 0):
            return _reject("BAD_VOLUME")
        buy = order.side == "buy"
        fill = self._quote.ask if buy else self._quote.bid
        if (buy and order.stop_loss >= fill) or (not buy and order.stop_loss <= fill):
            return _reject("BAD_STOP")
        tp = order.take_profit
        if tp is not None and ((buy and tp <= fill) or (not buy and tp >= fill)):
            return _reject("BAD_TARGET")
        pid = "P%d" % next(self._ids)
        self._positions[pid] = Position(pid, self._account_id, order.symbol,
                                        order.side, order.lots, fill,
                                        order.stop_loss, tp)
        return OrderResult(True, pid, fill, None)

    def tick(self, bid, ask, time_utc):
        """Move the market and close any position whose stop or target is hit.

        Exits happen at the new quote, so a gap past the stop loses more
        than planned.
        """
        self.set_quote(bid, ask, time_utc)
        closed = []
        for pid, pos in list(self._positions.items()):
            buy = pos.side == "buy"
            price = self._quote.bid if buy else self._quote.ask
            if buy:
                hit_stop = price <= pos.stop_loss
                hit_target = pos.take_profit is not None and price >= pos.take_profit
            else:
                hit_stop = price >= pos.stop_loss
                hit_target = pos.take_profit is not None and price <= pos.take_profit
            if hit_stop or hit_target:
                pnl = self.close_position(pid)
                closed.append((pid, pnl, "STOP" if hit_stop else "TARGET"))
        return closed

    def close_position(self, position_id):
        pos = self._positions.pop(position_id)  # KeyError if unknown
        buy = pos.side == "buy"
        exit_price = self._quote.bid if buy else self._quote.ask
        direction = 1 if buy else -1
        pnl = ((exit_price - pos.entry_price) * direction
               * pos.lots * self._spec.value_per_unit)
        self._balance += pnl
        return pnl
