import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from wolf.heartbeat import read_heartbeat, write_heartbeat

T0 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)


def test_roundtrip(tmp_path):
    write_heartbeat(str(tmp_path), "trader", T0, positions_open=1, status="ok")
    hb = read_heartbeat(str(tmp_path), "trader")
    assert hb.time_utc == T0 and hb.positions_open == 1 and hb.status == "ok"


def test_no_temp_file_left(tmp_path):
    write_heartbeat(str(tmp_path), "trader", T0)
    assert os.listdir(str(tmp_path)) == ["trader.json"]


def test_overwrite_replaces(tmp_path):
    write_heartbeat(str(tmp_path), "trader", T0, positions_open=1)
    later = T0 + timedelta(seconds=30)
    write_heartbeat(str(tmp_path), "trader", later, positions_open=0)
    hb = read_heartbeat(str(tmp_path), "trader")
    assert hb.time_utc == later and hb.positions_open == 0


@pytest.mark.parametrize("name", ["../x", "a/b", "", "A", "x" * 33, "a.b"])
def test_bad_names_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        write_heartbeat(str(tmp_path), name, T0)
    with pytest.raises(ValueError):
        read_heartbeat(str(tmp_path), name)


def test_naive_time_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_heartbeat(str(tmp_path), "trader", datetime(2026, 11, 3, 8, 0))


@pytest.mark.parametrize("bad", [-1, True, "1", 1.5])
def test_bad_positions_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        write_heartbeat(str(tmp_path), "trader", T0, positions_open=bad)


def test_missing_file_is_none(tmp_path):
    assert read_heartbeat(str(tmp_path), "trader") is None


def test_corrupt_file_is_none(tmp_path):
    (tmp_path / "trader.json").write_text("{not json")
    assert read_heartbeat(str(tmp_path), "trader") is None


def test_naive_timestamp_in_file_is_none(tmp_path):
    (tmp_path / "trader.json").write_text(json.dumps(
        {"time_utc": "2026-11-03T08:00:00", "positions_open": 0, "status": "ok"}))
    assert read_heartbeat(str(tmp_path), "trader") is None
