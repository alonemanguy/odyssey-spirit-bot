"""Growth plumbing: which invite brought someone, and the vote claim.

Two small records live in the bot's own state file, so they survive a restart:

    meta["invite_uses"]  {code: uses} from the last guild.invites() read
    meta["recruits"]     {user_id: how many people they brought}
    meta["vote_claims"]  {user_id: ISO timestamp of the last claim}

Attribution is a diff: Discord does not say which invite was used, so the uses
count on each code is compared with the previous reading. That works while the
bot is up (and, if the state file persists, across runs); a join that happens
while the process is stopped is simply not attributed.
"""

from datetime import datetime, timedelta, timezone

import discord

from odyssey_data import VOTE_SITES

VOTE_REWARD_COINS = 250
VOTE_REWARD_XP = 25
VOTE_CLAIM_HOURS = 12


def _add_xp(player, amount):
    """Same level curve as the rest of the bot."""
    player["xp"] += amount
    while player["xp"] >= player["xp_needed"]:
        player["xp"] -= player["xp_needed"]
        player["level"] += 1
        player["xp_needed"] = int(player["xp_needed"] * 1.15)


async def snapshot(guild, meta, save):
    """Record a baseline so the next diff means something."""
    try:
        invites = await guild.invites()
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"Growth: could not read invites ({exc})")
        return
    meta["invite_uses"] = {invite.code: (invite.uses or 0) for invite in invites}
    save()


async def note_join(member, meta, save):
    """Credit whoever's invite was just spent.

    Returns (inviter, code, their_total) or None.
    """
    guild = member.guild
    try:
        invites = await guild.invites()
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"Growth: could not read invites ({exc})")
        return None

    previous = meta.get("invite_uses") or {}
    best = None
    for invite in invites:
        spent = (invite.uses or 0) - previous.get(invite.code, 0)
        if spent > 0 and (best is None or spent > best[1]):
            best = (invite, spent)
    meta["invite_uses"] = {invite.code: (invite.uses or 0) for invite in invites}
    save()

    if best is None:
        return None
    invite = best[0]
    inviter = invite.inviter
    if inviter is None or inviter.bot or inviter.id == member.id:
        return None

    recruits = meta.setdefault("recruits", {})
    key = str(inviter.id)
    recruits[key] = recruits.get(key, 0) + 1
    save()
    return inviter, invite.code, recruits[key]


def register(bot, cfg):
    """Attach /vote and /recruits. cfg carries the state dict and callbacks."""

    @bot.hybrid_command(name="vote", description="Where to vote, and your claim for it")
    async def vote_cmd(ctx):
        """Links, plus a small claim so voting is worth a click."""
        player = cfg["player"](ctx.author.id)
        claims = cfg["state"].setdefault("vote_claims", {})
        key = str(ctx.author.id)
        now = datetime.now(timezone.utc)

        ready_at = None
        last = claims.get(key)
        if last:
            try:
                ready_at = datetime.fromisoformat(last) + timedelta(hours=VOTE_CLAIM_HOURS)
            except ValueError:
                ready_at = None

        lines = ["**Voting keeps us in the listings.** Once each:"]
        for label, url, note in VOTE_SITES:
            line = f"• **{label}** — {url}"
            if note:
                line += f" — {note}"
            lines.append(line)

        if ready_at and ready_at > now:
            left = ready_at - now
            hours, minutes = divmod(int(left.total_seconds()) // 60, 60)
            lines.append(f"\nAlready claimed. Next claim in {hours}h {minutes:02d}m.")
            await ctx.send("\n".join(lines))
            return

        player["balance"] += VOTE_REWARD_COINS
        player["stats"]["total_coins_earned"] += VOTE_REWARD_COINS
        _add_xp(player, VOTE_REWARD_XP)
        claims[key] = now.isoformat()
        cfg["save"]()

        lines.append(
            f"\n**+{VOTE_REWARD_COINS} coins, +{VOTE_REWARD_XP} xp.** "
            f"Next claim in {VOTE_CLAIM_HOURS}h.")
        lines.append("_This claim doesn't check that you voted — I can't see the vote "
                     "sites. It's on your honour._")
        await ctx.send("\n".join(lines))

    @bot.hybrid_command(name="recruits", description="Who has brought the most people here")
    async def recruits_cmd(ctx):
        """Invite attribution, newest numbers first."""
        recruits = cfg["state"].get("recruits") or {}
        if not recruits:
            await ctx.send(
                "Nobody on the board yet. Share your own link and the count starts:\n"
                "Server Settings → Invites shows the uses on each code.")
            return

        guild = bot.get_guild(cfg["guild_id"])
        rows = []
        for user_id, count in sorted(recruits.items(), key=lambda pair: -pair[1])[:10]:
            member = guild.get_member(int(user_id)) if guild else None
            name = member.display_name if member else f"`{user_id}`"
            rows.append(f"**{count}** — {name}")

        embed = discord.Embed(
            title="Recruiters",
            description="\n".join(rows),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Counted from invite uses. A join while the bot is offline isn't counted.")
        await ctx.send(embed=embed)
