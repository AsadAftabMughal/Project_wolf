import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class ChatConfig:
    token: str = field(repr=False)
    approver_ids: frozenset
    approvals_channel_id: int
    alerts_channel_id: int


def _int(env, name):
    raw = env.get(name, "").strip()
    if not raw.isdigit():
        raise ConfigError(name + " must be a number")
    return int(raw)


def load_config(env=None):
    env = os.environ if env is None else env
    token = env.get("DISCORD_TOKEN", "").strip()
    if len(token) < 50 or any(c.isspace() for c in token):
        raise ConfigError("DISCORD_TOKEN is missing or not a real token")
    parts = [p.strip() for p in env.get("DISCORD_APPROVER_IDS", "").split(",")]
    if not parts or not all(p.isdigit() for p in parts):
        raise ConfigError("DISCORD_APPROVER_IDS must be comma-separated numbers")
    return ChatConfig(
        token=token,
        approver_ids=frozenset(int(p) for p in parts),
        approvals_channel_id=_int(env, "DISCORD_APPROVALS_CHANNEL_ID"),
        alerts_channel_id=_int(env, "DISCORD_ALERTS_CHANNEL_ID"),
    )
