"""Ask the panel to start the SMP once, from a GitHub runner.

The bot does this on its own when a newcomer arrives, but a runner's address is
not always welcome at Cloudflare's front door, and when it is turned away the
bot can only say so. This is the manual version of the same call: dispatch
"Wake once" and it asks once, then says what happened in #event-announcements
(line 1345976335700328530) so the answer is visible to everyone, not just in a
job log that expires.

    ATERNOS_SESSION, ATERNOS_SERVER   the panel credentials (repo secrets)
    DISCORD_TOKEN                     only to post the outcome
"""

import asyncio
import json
import os
import urllib.request

import odyssey_aternos

CHANNEL_ID = os.environ.get("BOOT_NOTICE_CHANNEL_ID", "1345976335700328530")


async def ask():
    try:
        result = await odyssey_aternos.request_start()
    except odyssey_aternos.AternosError as exc:
        return f"**The server didn't wake.** {exc}"
    if result.get("started"):
        return ("**Bringing the server up** - give it a minute, then Java "
                "`odysseyland.aternos.me:56870` or Bedrock same host, port `19132`.")
    return f"**No start needed.** {result.get('message') or 'it was already up or starting'}"


def post(text):
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("no DISCORD_TOKEN, skipping the post")
        return
    body = json.dumps({"content": text[:1900]}).encode()
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        data=body,
        headers={"Authorization": f"Bot {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (https://github.com/alonemanguy/odyssey-spirit-bot, 1.0)"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print("posted:", response.status)
    except Exception as exc:  # the answer is already in the log below
        print("could not post:", type(exc).__name__, exc)


if __name__ == "__main__":
    if not odyssey_aternos.configured():
        message = "**Wake once** has no ATERNOS_SESSION / ATERNOS_SERVER to work with."
    else:
        message = asyncio.run(ask())
    print(message)
    post(message)
