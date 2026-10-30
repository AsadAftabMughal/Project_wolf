import pytest
from wolf.chat.config import ConfigError, load_config

TOKEN = "A" * 24 + "." + "B" * 6 + "." + "C" * 38
GOOD = {"DISCORD_TOKEN": TOKEN, "DISCORD_APPROVER_IDS": "111",
        "DISCORD_APPROVALS_CHANNEL_ID": "222", "DISCORD_ALERTS_CHANNEL_ID": "333"}


def test_loads():
    c = load_config(GOOD)
    assert c.approver_ids == frozenset({111})
    assert c.approvals_channel_id == 222 and c.alerts_channel_id == 333


def test_repr_hides_token():
    assert TOKEN not in repr(load_config(GOOD))


def test_missing_token():
    with pytest.raises(ConfigError):
        load_config({k: v for k, v in GOOD.items() if k != "DISCORD_TOKEN"})


def test_placeholder_token():
    with pytest.raises(ConfigError):
        load_config({**GOOD, "DISCORD_TOKEN": "paste_token_here"})


def test_multiple_approvers():
    c = load_config({**GOOD, "DISCORD_APPROVER_IDS": "111, 222"})
    assert c.approver_ids == frozenset({111, 222})


def test_empty_approvers():
    with pytest.raises(ConfigError):
        load_config({**GOOD, "DISCORD_APPROVER_IDS": ""})


@pytest.mark.parametrize("key,val", [
    ("DISCORD_APPROVALS_CHANNEL_ID", ""),
    ("DISCORD_ALERTS_CHANNEL_ID", "abc"),
    ("DISCORD_APPROVER_IDS", "12x"),
])
def test_bad_numbers(key, val):
    with pytest.raises(ConfigError):
        load_config({**GOOD, key: val})


def test_error_never_contains_token():
    with pytest.raises(ConfigError) as e:
        load_config({**GOOD, "DISCORD_ALERTS_CHANNEL_ID": "abc"})
    assert TOKEN not in str(e.value)
