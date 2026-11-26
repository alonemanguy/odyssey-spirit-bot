"""Role menus and SMP status commands for Tidewarden.

`register(bot, cfg)` attaches the commands; nothing here imports odyssey_bot, so
running that file as __main__ cannot pull in a second copy of the bot.
"""

import asyncio
import json
import socket
import struct

import discord

from odyssey_data import ROLE_MENUS


# ===== SELF-SERVE ROLE MENUS =====
class RoleSelect(discord.ui.Select):
    """One menu. Options are toggles: tap a role to get it, tap it again to drop it."""

    def __init__(self, key, placeholder, max_values, roles):
        self.role_map = {role_id: label for role_id, label, _ in roles}
        super().__init__(
            placeholder=placeholder,
            min_values=0,
            max_values=max_values,
            custom_id=f"odyssey_roles_{key}",
            options=[
                discord.SelectOption(label=label, value=str(role_id),
                                     description=description[:100])
                for role_id, label, description in roles
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "This menu only works inside Odyssey Lands.", ephemeral=True)
            return
        if not guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "I can't hand out roles yet - I need the Manage Roles permission. "
                "Someone with admin has to tick it on my role.", ephemeral=True)
            return

        selected = {int(value) for value in self.values}
        added, removed, failed = [], [], []
        for role_id, label in self.role_map.items():
            role = guild.get_role(role_id)
            if role is None:
                continue
            name = label.split(" ", 1)[-1]
            try:
                if role_id in selected and role not in member.roles:
                    await member.add_roles(role, reason="Self-assigned from the role menu")
                    added.append(name)
                elif role_id not in selected and role in member.roles:
                    await member.remove_roles(role, reason="Self-removed from the role menu")
                    removed.append(name)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(name)

        lines = []
        if added:
            lines.append("Added: " + ", ".join(added))
        if removed:
            lines.append("Removed: " + ", ".join(removed))
        if failed:
            lines.append("Couldn't change: " + ", ".join(failed) + " (my role sits below those)")
        if not lines:
            lines.append("Nothing to change - you already had that.")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class RolePanelView(discord.ui.View):
    """Four menus, one per role group. Persistent: custom_ids survive restarts."""

    def __init__(self):
        super().__init__(timeout=None)
        for key, placeholder, max_values, roles in ROLE_MENUS:
            self.add_item(RoleSelect(key, placeholder, max_values, roles))


# ===== SERVER STATUS =====
def _varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _read_varint(sock):
    value = 0
    for index in range(5):
        chunk = sock.recv(1)
        if not chunk:
            raise OSError("connection closed")
        value |= (chunk[0] & 0x7F) << (7 * index)
        if not chunk[0] & 0x80:
            return value
    raise OSError("malformed varint")


def java_status(host, port=25565, timeout=4.0):
    """Server-list ping, hand-rolled so no extra dependency is needed.

    Returns (online, detail). Any socket problem simply means "offline".
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            host_bytes = host.encode("utf-8")
            handshake = (
                _varint(0)                 # packet id: handshake
                + _varint(767)             # protocol version
                + _varint(len(host_bytes))
                + host_bytes
                + struct.pack(">H", port)
                + _varint(1)               # next state: status
            )
            sock.sendall(_varint(len(handshake)) + handshake)
            sock.sendall(_varint(1) + _varint(0))

            _read_varint(sock)             # packet length
            _read_varint(sock)             # packet id
            length = _read_varint(sock)
            payload = b""
            while len(payload) < length:
                chunk = sock.recv(length - len(payload))
                if not chunk:
                    break
                payload += chunk
            data = json.loads(payload.decode("utf-8", "replace") or "{}")
    except (OSError, ValueError):
        return False, ""

    version = (data.get("version") or {}).get("name") or "responding"
    players = data.get("players") or {}
    detail = str(version)
    if players.get("online") is not None and players.get("max"):
        detail += f", {players['online']}/{players['max']} players"
    return True, detail


def register(bot, cfg):
    """Attach /roles, /server and /start to `bot`."""

    @bot.hybrid_command(name='roles', description="Post the self-serve role menu (staff)")
    async def roles_cmd(ctx):
        """Post the role menus. Re-running it posts a fresh copy."""
        if ctx.guild is None or not ctx.author.guild_permissions.manage_roles:
            await ctx.send("Only staff can post the role menu.")
            return

        embed = discord.Embed(
            title="Roles",
            description=(
                "Pick what fits from the menus below. Tap a role again to drop it.\n"
                "Pings only ping you if you take them. The rest is cosmetic."
            ),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=RolePanelView())


    @bot.hybrid_command(name='wake', description="Ask Aternos to start the SMP right now")
    async def wake_cmd(ctx):
        """The same Start button the panel has, without the login."""
        await ctx.defer()
        wake = cfg.get('wake')
        if wake is None:
            await ctx.send("The wake-up wiring is not configured.")
            return

        waiting = cfg['wake_cooldown']() if cfg.get('wake_cooldown') else 0
        if waiting:
            await ctx.send(f"Already asked a moment ago - try again in {waiting // 60 + 1} min.")
            return

        started = await wake()
        if started:
            # wake() posts the address itself, in the channel it belongs in.
            await ctx.send("Asked. It takes about a minute to come up.")
        else:
            await ctx.send(
                "It was already up or already starting, or the start failed - "
                "`/start` shows the panel link if it stays offline.")


    @bot.hybrid_command(name='server', description="Addresses, ports and live status for the SMP")
    async def server_cmd(ctx):
        """Addresses, ports and status for the SMP."""
        await ctx.defer()
        online, detail = await asyncio.to_thread(
            java_status, cfg['java_host'], cfg['java_port'])

        embed = discord.Embed(
            title=f"⛵ {cfg['name']}",
            description="**Java:** `%s`\n**Bedrock:** `%s` — port `%s`" % (
                cfg['java_host'], cfg['bedrock_host'], cfg['bedrock_port']),
            color=discord.Color.green() if online else discord.Color.dark_grey(),
        )
        embed.add_field(
            name="Status",
            value=(f"Online - {detail}" if online else "Offline - `/start` shows how to bring it up"),
            inline=False)
        embed.add_field(
            name="Griefing",
            value="No griefing or stealing outside agreed wars. Accidents get rolled back.",
            inline=False)
        embed.add_field(name="Discord", value=cfg['invite'], inline=False)
        await ctx.send(embed=embed)


    @bot.hybrid_command(name='start', description="Is the SMP online? And how to start it if it isn't")
    async def start_cmd(ctx):
        """Status check plus the two sanctioned ways to start the server."""
        await ctx.defer()
        online, detail = await asyncio.to_thread(
            java_status, cfg['java_host'], cfg['java_port'])

        if online:
            embed = discord.Embed(
                title="The server is up",
                description="**Java:** `%s`\n**Bedrock:** `%s` - port `%s`" % (
                    cfg['java_host'], cfg['bedrock_host'], cfg['bedrock_port']),
                color=discord.Color.green(),
            )
            embed.add_field(name="Status", value=detail or "responding", inline=False)
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="The server is offline",
            description=(
                "Aternos shuts a free server down when nobody is on it. You don't need "
                "staff to start it - anyone with share access can.\n\n"
                f"**1.** Open {cfg['panel_url']} and press Start.\n"
                "**2.** Or use the Dawn launcher: log in to Aternos, press Start on the "
                "shared server.\n\n"
                f"Then join `{cfg['java_host']}` on Java, or `{cfg['bedrock_host']}` port "
                f"`{cfg['bedrock_port']}` on Bedrock."
            ),
            color=discord.Color.dark_grey(),
        )
        embed.add_field(
            name="How to get share access",
            value=(
                "Ask the owner to add your Aternos username under Access with Start "
                "permission. That's all you need - it doesn't hand over the account."
            ),
            inline=False)
        embed.set_footer(text="I can't press Start myself: Aternos has no API and their terms forbid automating the site.")
        await ctx.send(embed=embed)
