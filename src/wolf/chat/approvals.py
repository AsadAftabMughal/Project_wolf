import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta


@dataclass
class ApprovalRequest:
    request_id: str
    action: str
    details: str
    expires_at: datetime
    status: str = "PENDING"


def _aware(now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")


class ApprovalManager:
    """Single-use, expiring approvals that only allowlisted user IDs can decide.

    Held in memory on purpose: after a restart every pending approval is gone,
    which fails closed. Chat text is never an input here, only button decisions.
    """

    def __init__(self, approver_ids, ttl_seconds=120, max_pending=5):
        ids = frozenset(approver_ids)
        if not ids or not all(type(i) is int for i in ids):
            raise ValueError("approver_ids must be a non-empty set of ints")
        self._ids = ids
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max = max_pending
        self._reqs = {}

    def _purge(self, now):
        cutoff = timedelta(hours=1)
        for rid in [r for r, q in self._reqs.items()
                    if now >= q.expires_at + cutoff]:
            del self._reqs[rid]

    def request(self, action, details, now):
        _aware(now)
        self._purge(now)
        live = sum(1 for q in self._reqs.values()
                   if q.status == "PENDING" and now < q.expires_at)
        if live >= self._max:
            raise RuntimeError("too many pending approvals")
        rid = secrets.token_urlsafe(16)
        req = ApprovalRequest(rid, action, details, now + self._ttl)
        self._reqs[rid] = req
        return replace(req)

    def decide(self, request_id, user_id, approve, now):
        _aware(now)
        req = self._reqs.get(request_id)
        if req is None:
            return "UNKNOWN"
        if type(user_id) is not int or user_id not in self._ids:
            return "UNAUTHORIZED"  # leaves the request pending
        if req.status != "PENDING":
            return "ALREADY_DECIDED"
        if now >= req.expires_at:
            req.status = "EXPIRED"
            return "EXPIRED"
        req.status = "APPROVED" if approve else "DENIED"
        return req.status
