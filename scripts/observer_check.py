import asyncio
import sys
from datetime import datetime, timezone

import discord
from dotenv import load_dotenv

from wolf.chat.bot import send_alert
from wolf.chat.config import ConfigError, load_config
from wolf.observer import AlertDeduper, evaluate

HB_DIR = "state/heartbeats"
EXPECTED = ["trader", "manager"]


async def main():
    load_dotenv(override=False)
    try:
        cfg = load_config()
    except ConfigError as e:
        sys.exit("Config error: " + str(e))
    now = datetime.now(timezone.utc)
    findings = evaluate(HB_DIR, EXPECTED, now)
    for f in findings:
        print(f.bot, f.state, f.severity)
    msgs = AlertDeduper().messages(findings, now)
    if not msgs:
        print("Nothing to report.")
        return
    client = discord.Client(intents=discord.Intents.none())
    async with client:
        await client.login(cfg.token)
        for m in msgs:
            await send_alert(client, cfg, m)
    print("Sent %d alert(s) to #alerts" % len(msgs))


asyncio.run(main())
