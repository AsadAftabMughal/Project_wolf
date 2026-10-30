from wolf.core.risk_gate import AccountState
from wolf.heartbeat import require_utc


class DayLedger:
    """Builds the AccountState the risk gate needs. Resets at each UTC day."""

    def __init__(self, broker, now):
        require_utc(now)
        self._broker = broker
        self._start(now)

    def _start(self, now):
        self._day = now.date()
        self._start_balance = self._broker.account().balance
        self._trades = 0

    def _roll(self, now):
        require_utc(now)
        if now.date() != self._day:
            self._start(now)

    def record_open(self, now):
        self._roll(now)
        self._trades += 1

    def state(self, now, kill_switch=False):
        self._roll(now)
        balance = self._broker.account().balance
        return AccountState(
            balance=self._start_balance,
            daily_pnl=balance - self._start_balance,
            trades_today=self._trades,
            open_positions=len(self._broker.positions()),
            kill_switch=kill_switch,
        )
