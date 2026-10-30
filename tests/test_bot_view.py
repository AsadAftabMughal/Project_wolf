import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from wolf.chat.approvals import ApprovalManager
from wolf.chat.bot import ApprovalView

OWNER, CHAN = 111, 222


class FakeResponse:
    def __init__(self):
        self.sent = []
        self.edited = []

    async def send_message(self, content, ephemeral=False):
        self.sent.append((content, ephemeral))

    async def edit_message(self, content=None, view=None):
        self.edited.append(content)


class FakeInteraction:
    def __init__(self, user_id, channel_id):
        self.user = SimpleNamespace(id=user_id)
        self.channel_id = channel_id
        self.response = FakeResponse()


def setup():
    m = ApprovalManager({OWNER})
    req = m.request("close all", "demo", datetime.now(timezone.utc))
    got = []

    async def cb(r, status):
        got.append(status)

    return m, req, got, ApprovalView(m, req, CHAN, cb, 120)


def test_owner_approve_in_right_channel():
    async def go():
        m, req, got, v = setup()
        i = FakeInteraction(OWNER, CHAN)
        await v._handle(i, True)
        assert got == ["APPROVED"]
        assert i.response.edited
        assert all(c.disabled for c in v.children)
    asyncio.run(go())


def test_owner_deny():
    async def go():
        m, req, got, v = setup()
        await v._handle(FakeInteraction(OWNER, CHAN), False)
        assert got == ["DENIED"]
    asyncio.run(go())


def test_stranger_is_rejected_and_request_stays_open():
    async def go():
        m, req, got, v = setup()
        i = FakeInteraction(999, CHAN)
        await v._handle(i, True)
        assert got == []
        assert i.response.sent and i.response.sent[0][1] is True
        await v._handle(FakeInteraction(OWNER, CHAN), True)
        assert got == ["APPROVED"]
    asyncio.run(go())


def test_wrong_channel_is_rejected():
    async def go():
        m, req, got, v = setup()
        i = FakeInteraction(OWNER, 333)
        await v._handle(i, True)
        assert got == []
        assert i.response.sent and i.response.sent[0][1] is True
        await v._handle(FakeInteraction(OWNER, CHAN), True)
        assert got == ["APPROVED"]
    asyncio.run(go())


def test_second_click_does_nothing():
    async def go():
        m, req, got, v = setup()
        await v._handle(FakeInteraction(OWNER, CHAN), True)
        i2 = FakeInteraction(OWNER, CHAN)
        await v._handle(i2, True)
        assert got == ["APPROVED"]
        assert i2.response.sent and i2.response.sent[0][1] is True
    asyncio.run(go())
