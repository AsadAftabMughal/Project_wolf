from wolf import killswitch
from wolf.executor import execute
from wolf.heartbeat import write_heartbeat


def heartbeat(broker, hb_dir, now, status="ok"):
    write_heartbeat(hb_dir, "trader", now, len(broker.positions()), status)


def process_signal(broker, cfg, ledger, signal, kill_path):
    """Ledger state, then the executor. Only a PLACED order counts as a trade."""
    now = signal.when_utc
    state = ledger.state(now, killswitch.is_engaged(kill_path))
    out = execute(broker, cfg, state, signal, kill_switch_path=kill_path)
    if out.status == "PLACED":
        ledger.record_open(now)
    return out
