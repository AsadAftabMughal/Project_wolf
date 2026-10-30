from datetime import datetime, timezone

import discord

from wolf.chat.redact import safe_message

NO_MENTIONS = discord.AllowedMentions.none()


def _now():
    return datetime.now(timezone.utc)


class ApprovalView(discord.ui.View):
    """Approve and Deny buttons for one request. Not persistent: a restart
    kills them, which fails closed."""

    def __init__(self, manager, request, approvals_channel_id, on_decision, ttl):
        super().__init__(timeout=ttl)
        self._m = manager
        self._req = request
        self._channel_id = approvals_channel_id
        self._on_decision = on_decision
        self.message = None

    def _disable(self):
        for child in self.children:
            child.disabled = True

    async def _handle(self, interaction, approve):
        if interaction.channel_id != self._channel_id:
            await interaction.response.send_message("Not allowed here.", ephemeral=True)
            return
        status = self._m.decide(self._req.request_id, interaction.user.id,
                                approve, _now())
        if status == "UNAUTHORIZED":
            await interaction.response.send_message("You are not authorised.",
                                                    ephemeral=True)
            return
        if status not in ("APPROVED", "DENIED"):
            await interaction.response.send_message("This request is no longer valid.",
                                                    ephemeral=True)
            return
        self._disable()
        await interaction.response.edit_message(
            content=safe_message("%s: %s" % (self._req.action, status)), view=self)
        self.stop()
        await self._on_decision(self._req, status)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):
        await self._handle(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction, button):
        await self._handle(interaction, False)

    async def on_timeout(self):
        self._disable()
        if self.message is not None:
            try:
                await self.message.edit(
                    content=safe_message("%s: EXPIRED" % self._req.action), view=self)
            except discord.HTTPException:
                pass
        await self._on_decision(self._req, "EXPIRED")


async def _channel(client, channel_id):
    ch = await client.fetch_channel(channel_id)
    if not isinstance(ch, discord.abc.Messageable):
        raise RuntimeError("channel cannot receive messages")
    return ch


async def send_alert(client, cfg, text):
    ch = await _channel(client, cfg.alerts_channel_id)
    await ch.send(safe_message(text), allowed_mentions=NO_MENTIONS)


async def request_approval(client, cfg, manager, action, details, on_decision):
    ch = await _channel(client, cfg.approvals_channel_id)
    now = _now()
    req = manager.request(action, details, now)
    ttl = max(1.0, (req.expires_at - now).total_seconds())
    view = ApprovalView(manager, req, cfg.approvals_channel_id, on_decision, ttl)
    text = safe_message("**Approval needed:** %s\n%s\nExpires in %d seconds"
                        % (action, details, ttl))
    view.message = await ch.send(text, view=view, allowed_mentions=NO_MENTIONS)
    return req
