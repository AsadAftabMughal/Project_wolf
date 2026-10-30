import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

_NAME = re.compile(r"^[a-z0-9_-]{1,32}$")


@dataclass(frozen=True)
class Heartbeat:
    bot: str
    time_utc: datetime
    positions_open: int
    status: str


def require_utc(dt):
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError("timezone-aware UTC datetime required")


def _check_name(bot):
    if not _NAME.match(bot):
        raise ValueError("bad bot name")


def write_heartbeat(directory, bot, now, positions_open=0, status="ok"):
    """Atomic write, so a reader never sees a half-written file."""
    _check_name(bot)
    require_utc(now)
    if type(positions_open) is not int or positions_open < 0:
        raise ValueError("positions_open must be a non-negative int")
    os.makedirs(directory, exist_ok=True)
    final = os.path.join(directory, bot + ".json")
    tmp = final + ".tmp"
    data = {"time_utc": now.isoformat(), "positions_open": positions_open,
            "status": str(status)[:20]}
    with open(tmp, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, final)


def read_heartbeat(directory, bot):
    """Returns a Heartbeat, or None if missing, corrupt or not UTC."""
    _check_name(bot)
    try:
        with open(os.path.join(directory, bot + ".json")) as f:
            d = json.load(f)
        t = datetime.fromisoformat(d["time_utc"])
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            return None
        n = d["positions_open"]
        if type(n) is not int or n < 0:
            return None
        return Heartbeat(bot, t, n, str(d.get("status", ""))[:20])
    except (OSError, ValueError, KeyError, TypeError):
        return None
