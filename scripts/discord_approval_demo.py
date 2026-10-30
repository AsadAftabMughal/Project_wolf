import sys

import discord
from dotenv import load_dotenv

from wolf.chat.approvals import ApprovalManager
from wolf.chat.bot import request_approval, send_alert
from wolf.chat.config import ConfigError, load_config


def main():
    load_dotenv(override=False)
    try:
        cfg = load_config()
    except ConfigError as e:
        sys.exit("Config error: " + str(e))

    client = discord.Client(intents=discord.Intents.none())
    manager = ApprovalManager(cfg.approver_ids, ttl_seconds=120)
    started = {"done": False}

    async def on_decision(req, status):
        await send_alert(client, cfg, "Demo approval %s: %s" % (status, req.action))
        await client.close()

    @client.event
    async def on_ready():
        if started["done"]:
            return
        started["done"] = True
        print("Online as", client.user)
        await request_approval(client, cfg, manager, "DEMO: no real action",
                               "Press Approve or Deny. Nothing will be executed.",
                               on_decision)
        print("Approval request posted in #approvals. Waiting up to 120 seconds.")

    client.run(cfg.token)


main()
