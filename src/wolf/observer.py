from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from wolf.heartbeat import read_heartbeat, require_utc


@dataclass(frozen=True)
class Finding:
    bot: str
    state: str     # OK, STALE, MISSING or FUTURE
    severity: str  # OK, WARNING or CRITICAL
    age_seconds: Optional[float] = None
    positions_open: int = 0


def evaluate(directory, expected_bots, now, max_age_seconds=120, skew_seconds=5):
    """Read-only. CRITICAL when any problem exists while any bot's last known
    heartbeat showed open positions."""
    require_utc(now)
    raw = []
    for bot in expected_bots:
        hb = read_heartbeat(directory, bot)
        if hb is None:
            raw.append((bot, "MISSING", None, 0))
            continue
        age = (now - hb.time_utc).total_seconds()
        if age < -skew_seconds:
            state = "FUTURE"
        elif age > max_age_seconds:
            state = "STALE"
        else:
            state = "OK"
        raw.append((bot, state, age, hb.positions_open))
    exposure = any(p > 0 for _, _, _, p in raw)
    findings = []
    for bot, state, age, pos in raw:
        if state == "OK":
            severity = "OK"
        else:
            severity = "CRITICAL" if exposure else "WARNING"
        findings.append(Finding(bot, state, severity, age, pos))
    return findings


class AlertDeduper:
    """Alerts on a new problem, repeats every repeat_seconds, says RECOVERED once."""

    def __init__(self, repeat_seconds=900):
        self._repeat = timedelta(seconds=repeat_seconds)
        self._seen = {}

    def messages(self, findings, now):
        require_utc(now)
        out = []
        for f in findings:
            prev = self._seen.get(f.bot)
            if f.state == "OK":
                if prev is not None:
                    out.append("RECOVERED: %s heartbeat is back" % f.bot)
                    del self._seen[f.bot]
                continue
            key = (f.state, f.severity)
            if prev is None or prev[0] != key or now - prev[1] >= self._repeat:
                age = "" if f.age_seconds is None else " (%ds)" % int(f.age_seconds)
                out.append("[%s] %s heartbeat %s%s, positions open: %d"
                           % (f.severity, f.bot, f.state, age, f.positions_open))
                self._seen[f.bot] = (key, now)
        return out
