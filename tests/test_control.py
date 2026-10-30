import asyncio
from types import SimpleNamespace

from wolf import killswitch
from wolf.chat.control import ControlView

OWNER, CHAN = 111, 222
CFG = SimpleNamespace(approver_ids=frozenset({OWNER}),
                      approvals_channel_id=CHAN, alerts_channel_id=333)


class Resp:
    def __init__(self):
        self.sent = []

    async def send_message(self, content, ephemeral=False):
        self.sent.append((content, ephemeral))


def click(user_id=OWNER, channel_id=CHAN):
    return SimpleNamespace(user=SimpleNamespace(id=user_id),
                           channel_id=channel_id, response=Resp())


def make(tmp_path, request_error=None):
    path = str(tmp_path / "state" / "KILL")
    alerts, callbacks = [], []

    async def alert(client, cfg, text):
        alerts.append(text)

    async def request(client, cfg, manager, action, details, on_decision):
        if request_error:
            raise request_error
        callbacks.append(on_decision)

    return ControlView(None, CFG, None, path, alert, request), path, alerts, callbacks


def test_owner_stop_engages_and_alerts(tmp_path):
    async def go():
        v, path, alerts, _ = make(tmp_path)
        i = click()
        await v._handle_stop(i)
        assert killswitch.is_engaged(path)
        assert i.response.sent[0][1] is True
        assert len(alerts) == 1
    asyncio.run(go())


def test_stranger_cannot_stop(tmp_path):
    async def go():
        v, path, alerts, _ = make(tmp_path)
        i = click(user_id=999)
        await v._handle_stop(i)
        assert not killswitch.is_engaged(path)
        assert alerts == []
        assert i.response.sent[0][1] is True
    asyncio.run(go())


def test_wrong_channel_cannot_stop(tmp_path):
    async def go():
        v, path, alerts, _ = make(tmp_path)
        await v._handle_stop(click(channel_id=444))
        assert not killswitch.is_engaged(path)
    asyncio.run(go())


def test_stop_twice_is_fine(tmp_path):
    async def go():
        v, path, alerts, _ = make(tmp_path)
        await v._handle_stop(click())
        await v._handle_stop(click())
        assert killswitch.is_engaged(path)
        assert len(alerts) == 1
    asyncio.run(go())


def test_resume_when_not_stopped(tmp_path):
    async def go():
        v, path, alerts, callbacks = make(tmp_path)
        i = click()
        await v._handle_resume(i)
        assert callbacks == []
        assert "not stopped" in i.response.sent[0][0]
    asyncio.run(go())


def test_resume_needs_approval_first(tmp_path):
    async def go():
        v, path, alerts, callbacks = make(tmp_path)
        await v._handle_stop(click())
        await v._handle_resume(click())
        assert len(callbacks) == 1
        assert killswitch.is_engaged(path)
    asyncio.run(go())


def test_stranger_cannot_request_resume(tmp_path):
    async def go():
        v, path, alerts, callbacks = make(tmp_path)
        await v._handle_stop(click())
        await v._handle_resume(click(user_id=999))
        assert callbacks == []
        assert killswitch.is_engaged(path)
    asyncio.run(go())


def test_approved_resume_releases(tmp_path):
    async def go():
        v, path, alerts, callbacks = make(tmp_path)
        await v._handle_stop(click())
        await v._handle_resume(click())
        await callbacks[0](SimpleNamespace(action="RESUME trading"), "APPROVED")
        assert not killswitch.is_engaged(path)
    asyncio.run(go())


def test_denied_or_expired_resume_keeps_stopped(tmp_path):
    async def go():
        for status in ("DENIED", "EXPIRED"):
            v, path, alerts, callbacks = make(tmp_path)
            await v._handle_stop(click())
            await v._handle_resume(click())
            await callbacks[0](SimpleNamespace(action="RESUME trading"), status)
            assert killswitch.is_engaged(path)
    asyncio.run(go())


def test_too_many_pending_keeps_stopped(tmp_path):
    async def go():
        v, path, alerts, callbacks = make(tmp_path,
                                          request_error=RuntimeError("busy"))
        await v._handle_stop(click())
        i = click()
        await v._handle_resume(i)
        assert killswitch.is_engaged(path)
        assert "Too many" in i.response.sent[0][0]
    asyncio.run(go())
