import discord

from wolf import killswitch
from wolf.chat.bot import request_approval, send_alert


class ControlView(discord.ui.View):
    """STOP is one tap. RESUME asks for a separate approval first.

    The kill file is the real switch, so it still works if Discord is down.
    """

    def __init__(self, client, cfg, manager, kill_path,
                 alert_fn=send_alert, request_fn=request_approval):
        super().__init__(timeout=None)
        self._client = client
        self._cfg = cfg
        self._manager = manager
        self._path = kill_path
        self._alert = alert_fn
        self._request = request_fn

    async def _check(self, interaction):
        if interaction.channel_id != self._cfg.approvals_channel_id:
            await interaction.response.send_message("Not allowed here.", ephemeral=True)
            return False
        uid = interaction.user.id
        if type(uid) is not int or uid not in self._cfg.approver_ids:
            await interaction.response.send_message("You are not authorised.",
                                                    ephemeral=True)
            return False
        return True

    async def _handle_stop(self, interaction):
        if not await self._check(interaction):
            return
        already = killswitch.is_engaged(self._path)
        if not already:
            try:
                killswitch.engage(self._path, "discord user %d" % interaction.user.id)
            except OSError:
                await interaction.response.send_message(
                    "FAILED to engage the kill switch. Stop trading manually.",
                    ephemeral=True)
                await self._alert(self._client, self._cfg,
                                  "KILL SWITCH FAILED to engage from Discord")
                return
        await interaction.response.send_message("Trading is STOPPED.", ephemeral=True)
        if not already:
            await self._alert(self._client, self._cfg,
                              "KILL SWITCH engaged from Discord")

    async def _handle_resume(self, interaction):
        if not await self._check(interaction):
            return
        if not killswitch.is_engaged(self._path):
            await interaction.response.send_message("Trading is not stopped.",
                                                    ephemeral=True)
            return

        async def on_decision(req, status):
            if status == "APPROVED":
                killswitch.release(self._path)
                await self._alert(self._client, self._cfg,
                                  "Trading RESUMED (approved in Discord)")
            else:
                await self._alert(self._client, self._cfg,
                                  "Resume %s: trading stays stopped" % status)

        try:
            await self._request(self._client, self._cfg, self._manager,
                                "RESUME trading",
                                "Releases the kill switch. Approve only if you "
                                "know why trading was stopped.", on_decision)
        except RuntimeError:
            await interaction.response.send_message(
                "Too many pending requests. Try again shortly.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Approval requested below. Trading stays stopped until you approve.",
            ephemeral=True)

    @discord.ui.button(label="STOP TRADING", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction, button):
        await self._handle_stop(interaction)

    @discord.ui.button(label="Resume trading", style=discord.ButtonStyle.secondary)
    async def resume_button(self, interaction, button):
        await self._handle_resume(interaction)
