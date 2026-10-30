import argparse
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from wolf import killswitch
from wolf.broker.fake import FakeBroker
from wolf.core.risk_gate import RiskConfig
from wolf.executor import Signal
from wolf.ledger import DayLedger
from wolf.runner import heartbeat, process_signal

KILL = "state/dryrun/KILL"
HB = "state/dryrun/heartbeats"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance", default="300")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--kill-at", default=None, help="HH:MM UTC")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    killswitch.release(KILL)
    start = datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc)  # a Tuesday
    end = start.replace(hour=17)
    broker = FakeBroker(balance=args.balance, quote_time=start)
    ledger = DayLedger(broker, start)
    cfg = RiskConfig()
    kill_at = None
    if args.kill_at:
        h, m = args.kill_at.split(":")
        kill_at = start.replace(hour=int(h), minute=int(m))

    mid = D("2000.00")
    outcomes, exits = Counter(), []
    t = start
    while t < end:
        mid += D(str(round(rng.gauss(0, 0.25), 2)))
        for _, pnl, why in broker.tick(mid - D("0.15"), mid + D("0.15"), t):
            exits.append((pnl, why))
        if kill_at is not None and t >= kill_at and not killswitch.is_engaged(KILL):
            killswitch.engage(KILL, "dry run")
        if t.minute % 15 == 0:
            side = rng.choice(("buy", "sell"))
            out = process_signal(broker, cfg, ledger,
                                 Signal("XAUUSD", side, D("3"), D("6"), t), KILL)
            key = out.status + (": " + ",".join(out.reasons) if out.reasons else "")
            outcomes[key] += 1
        heartbeat(broker, HB, t)
        t += timedelta(minutes=1)

    for pos in broker.positions():
        exits.append((broker.close_position(pos.position_id), "END OF DAY"))
    killswitch.release(KILL)

    print("Signals: %d" % sum(outcomes.values()))
    for k, v in sorted(outcomes.items()):
        print("  %s x %d" % (k, v))
    kinds = Counter(w for _, w in exits)
    print("Closed trades: %d  %s" % (len(exits), dict(kinds)))
    worst = min((p for p, _ in exits), default=D("0"))
    print("Start balance %s, end balance %s" % (args.balance, broker.account().balance))
    print("Worst single loss %s vs 1%% risk %s" % (worst, D(args.balance) / 100))


main()
