import sys

import discord
from dotenv import load_dotenv

from wolf import killswitch
from wolf.chat.approvals import ApprovalManager
from wolf.chat.bot import send_alert
from wolf.chat.config import ConfigError, load_config
from wolf.chat.control import ControlView

KILL_PATH = "state/KILL"


def main():
    load_dotenv(override=False)
    try:
        cfg = load_config()
    except ConfigError as e:
        sys.exit("Config error: " + str(e))

    client = discord.Client(intents=discord.Intents.none())
    manager = ApprovalManager(cfg.approver_ids, ttl_seconds=120)
    started = {"done": False}

    @client.event
    async def on_ready():
        if started["done"]:
            return
        started["done"] = True
        view = ControlView(client, cfg, manager, KILL_PATH)
        ch = await client.fetch_channel(cfg.approvals_channel_id)
        state = "ENGAGED" if killswitch.is_engaged(KILL_PATH) else "clear"
        await ch.send("**Wolf control panel.** Kill switch: %s" % state, view=view,
                      allowed_mentions=discord.AllowedMentions.none())
        await send_alert(client, cfg, "Control panel online")
        print("Control panel posted. Ctrl+C to stop. Buttons die when this stops.")

    client.run(cfg.token)


main()
