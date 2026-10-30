import asyncio
import sys

import discord
from dotenv import load_dotenv

from wolf.chat.config import ConfigError, load_config
from wolf.chat.redact import safe_message


async def main():
    load_dotenv(override=False)
    try:
        cfg = load_config()
    except ConfigError as e:
        sys.exit("Config error: " + str(e))

    client = discord.Client(intents=discord.Intents.none())
    async with client:
        try:
            await client.login(cfg.token)
        except discord.LoginFailure:
            sys.exit("Login failed: token rejected. Reset it in the developer "
                     "portal and update .env")
        print("Authenticated as", client.user, "(id %s)" % client.user.id)

        guilds = [g async for g in client.fetch_guilds(limit=10)]
        print("Bot is in %d server(s): %s" % (len(guilds), ", ".join(g.name for g in guilds)))
        if len(guilds) != 1:
            print("WARNING: expected exactly 1 server")

        ok = True
        for name, cid in (("approvals", cfg.approvals_channel_id),
                          ("alerts", cfg.alerts_channel_id)):
            try:
                ch = await client.fetch_channel(cid)
                print("%s channel: #%s OK" % (name, ch.name))
            except discord.Forbidden:
                print("%s channel: no access (check channel permissions)" % name)
                ok = False
            except discord.NotFound:
                print("%s channel: not found (check the ID)" % name)
                ok = False
        if not ok:
            sys.exit(1)

        alerts = await client.fetch_channel(cfg.alerts_channel_id)
        await alerts.send(safe_message("Wolf online (smoke test)"),
                          allowed_mentions=discord.AllowedMentions.none())
        print("Test message sent to #alerts")


asyncio.run(main())
