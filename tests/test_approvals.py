from datetime import datetime, timedelta, timezone
import pytest
from wolf.chat.approvals import ApprovalManager

T0 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
OWNER = 111


def mgr(**kw):
    return ApprovalManager({OWNER}, **kw)


def sec(n):
    return T0 + timedelta(seconds=n)


def test_owner_can_approve():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, OWNER, True, sec(1)) == "APPROVED"


def test_owner_can_deny():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, OWNER, False, sec(1)) == "DENIED"


def test_unauthorized_user_does_not_consume_request():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, 999, True, sec(1)) == "UNAUTHORIZED"
    assert m.decide(r.request_id, OWNER, True, sec(2)) == "APPROVED"


def test_second_decision_is_rejected():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, OWNER, True, sec(1)) == "APPROVED"
    assert m.decide(r.request_id, OWNER, True, sec(2)) == "ALREADY_DECIDED"


def test_expired_request_cannot_be_approved():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, OWNER, True, sec(121)) == "EXPIRED"
    assert m.decide(r.request_id, OWNER, True, sec(122)) != "APPROVED"


def test_expiry_boundary():
    m = mgr()
    a = m.request("a", "x", T0)
    b = m.request("b", "x", T0)
    assert m.decide(a.request_id, OWNER, True, sec(119)) == "APPROVED"
    assert m.decide(b.request_id, OWNER, True, sec(120)) == "EXPIRED"


def test_unknown_request():
    assert mgr().decide("nope", OWNER, True, T0) == "UNKNOWN"


def test_empty_allowlist_rejected():
    with pytest.raises(ValueError):
        ApprovalManager(set())


def test_non_int_allowlist_rejected():
    with pytest.raises(ValueError):
        ApprovalManager({"111"})
    with pytest.raises(ValueError):
        ApprovalManager({True})


def test_string_user_id_is_unauthorized():
    m = mgr()
    r = m.request("close all", "x", T0)
    assert m.decide(r.request_id, "111", True, sec(1)) == "UNAUTHORIZED"


def test_too_many_pending():
    m = mgr(max_pending=2)
    m.request("a", "x", T0)
    m.request("b", "x", T0)
    with pytest.raises(RuntimeError):
        m.request("c", "x", T0)


def test_expired_requests_free_their_slot():
    m = mgr(max_pending=2)
    m.request("a", "x", T0)
    m.request("b", "x", T0)
    m.request("c", "x", sec(200))


def test_request_ids_are_unique():
    m = mgr(max_pending=200)
    ids = {m.request("a", "x", T0).request_id for _ in range(100)}
    assert len(ids) == 100


def test_naive_time_rejected():
    m = mgr()
    with pytest.raises(ValueError):
        m.request("a", "x", datetime(2026, 11, 3, 8, 0))
    r = m.request("a", "x", T0)
    with pytest.raises(ValueError):
        m.decide(r.request_id, OWNER, True, datetime(2026, 11, 3, 8, 0))
