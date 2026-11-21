import asyncio
import json
import os
import random
import socket
import struct
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from odyssey_data import (
    ACHIEVEMENTS,
    EXPLORE_LOCATIONS,
    FISH,
    OCEAN_EVENTS,
    PETS,
    QUESTS,
    TITLES,
    WEATHER_TYPES,
    WEEKLY_PROMPTS,
)

# ===== GUILD =====
GUILD_ID = 1345963951724171364             # Odyssey Lands

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True             # still needed for the ! prefix commands
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None,
                   case_insensitive=True)

# ===== DATA =====
player_data = {}
guild_data = {}
quest_log = {}
pet_data = {}
weather_status = "Calm"

# Profiles used to live in RAM only, so every Actions run started from an empty
# world - coins, levels, pets and streaks vanished every few hours. They are now
# written to disk after each command and reloaded on boot.
STATE_FILE = os.environ.get("ODYSSEY_STATE_FILE", "state/odyssey_state.json")
state_meta = {"last_weekly_prompt": None}

# How long one process may run. The workflow fires every 300 minutes, so this
# has to stay below that or two copies of the bot answer the same command.
RUN_BUDGET_MINUTES = int(os.environ.get("RUN_BUDGET_MINUTES", "285"))

# ===== THE SMP =====
# Aternos has no API and its terms forbid automating the website, so the bot
# cannot press Start. Share access is the sanctioned route, and any player who
# has been granted the "Start" permission can use it.
SERVER_NAME = "Odyssey Lands SMP"
SERVER_JAVA_HOST = os.environ.get("SERVER_JAVA_HOST", "odysseyland.aternos.me")
SERVER_JAVA_PORT = int(os.environ.get("SERVER_JAVA_PORT", "25565"))
SERVER_BEDROCK_HOST = os.environ.get("SERVER_BEDROCK_HOST", "odysseyland.aternos.me")
SERVER_BEDROCK_PORT = int(os.environ.get("SERVER_BEDROCK_PORT", "19132"))
SERVER_PANEL_URL = os.environ.get("SERVER_PANEL_URL", "https://aternos.org/go/")
SERVER_DISCORD_INVITE = "https://discord.gg/dgYqruDZx3"

# ===== CHANNELS =====
PROMPT_CHANNEL_ID = int(os.environ.get("PROMPT_CHANNEL_ID", "1345963952668020911"))  # #general
WEEKLY_PROMPT_WEEKDAY = 5          # Monday is 0, so 5 = Saturday
WEEKLY_PROMPT_HOUR_UTC = 17

def load_state():
    """Read saved profiles from disk. Missing or corrupt file just means a new world."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except FileNotFoundError:
        return
    except (OSError, ValueError) as exc:
        print(f"Could not read {STATE_FILE} ({exc}); starting empty")
        return

    for key, profile in (raw.get("players") or {}).items():
        try:
            user_id = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(profile, dict):
            player_data[user_id] = profile
    meta = raw.get("meta")
    if isinstance(meta, dict):
        state_meta.update(meta)
    print(f"Loaded {len(player_data)} saved profile(s) from {STATE_FILE}")


def save_state():
    """Write profiles atomically so a killed run can't leave half a JSON file."""
    folder = os.path.dirname(STATE_FILE)
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp_path = f"{STATE_FILE}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(
                {"players": {str(k): v for k, v in player_data.items()},
                 "meta": state_meta},
                handle, indent=1, sort_keys=True,
            )
        os.replace(tmp_path, STATE_FILE)
    except OSError as exc:
        print(f"Could not save {STATE_FILE}: {exc}")


def refresh_streak(player):
    """Keep the login streak current on use.

    This used to be a 24-hour tasks.loop, which never fired: each run is about
    five hours, so the streak was permanently stuck at zero.
    """
    today = datetime.now(timezone.utc).date()
    last = player.get("last_login")
    last_date = None
    if last:
        try:
            last_date = datetime.fromisoformat(str(last)).date()
        except ValueError:
            last_date = None
    if last_date == today:
        return
    if last_date and (today - last_date).days == 1:
        player["login_streak"] = player.get("login_streak", 0) + 1
    else:
        player["login_streak"] = 1
    player["last_login"] = today.isoformat()

# ===== WHERE TIDEWARDEN IS ALLOWED TO TALK =====
# The ocean/weather feed used to grab the first channel named "general" and post
# there ~150 times a day, which buried every real conversation. It now lives in
# #event-announcements. #general is for humans (and the bot is also denied Send
# Messages there, so a still-running old deployment can't spam it either).
FLAVOUR_CHANNEL_ID = 1345976335700328530   # #event-announcements
OCEAN_EVENT_MINUTES = 120                  # was 10
RANDOM_EVENT_MINUTES = 180                 # was 30

# ===== BUMP REMINDERS =====
# A bot account cannot run another bot's command - Discord does not deliver bot
# messages to other bots' command handlers - and DISBOARD's guidelines forbid
# auto-bumping outright. So Tidewarden cannot press these four for you. What it
# can do is make sure the nudge lands every 2 hours instead of never.
BUMP_CHANNEL_ID = 1472965935571664969      # #📣-bump
BUMP_REMINDER_MINUTES = 120               # DISBOARD's own cooldown
BUMP_QUIET_HOURS_UTC = (22, 5)            # no pings 01:00-07:59 UTC+3
BUMP_BOTS = [
    ("DISBOARD", "/bump"),
    ("Discadia", "/bump"),
    ("D-ify", "/bump"),
    ("DiscordHome (DH Bump)", "dh!bump"),
]


def flavour_channel(guild):
    """The only channel the ambient feed may post in. Never #general."""
    channel = guild.get_channel(FLAVOUR_CHANNEL_ID)
    if channel is None:
        return None
    if not channel.permissions_for(guild.me).send_messages:
        return None
    return channel

# ===== INITIALIZE PLAYER DATA =====
def get_player_data(user_id):
    """Fetch (or create) a profile, and keep the login streak honest."""
    if user_id not in player_data:
        player_data[user_id] = {
            "balance": 0,
            "inventory": [],
            "catches": 0,
            "explored": 0,
            "level": 1,
            "xp": 0,
            "xp_needed": 100,
            "achievements": [],
            "pet": None,
            "pet_level": 1,
            "guild": None,
            "titles": [],
            "active_title": None,
            "stats": {
                "total_coins_earned": 0,
                "total_fish_caught": 0,
                "total_duels": 0,
                "duel_wins": 0,
                "games_played": 0,
                "games_won": 0,
                "quests_completed": 0,
                "times_played": 0,
            },
            "daily_bonus": 0,  # Track last bonus date
            "login_streak": 0,
            "last_login": None,
            "quests": {},
            "quest_progress": {},
            "inventory_limit": 100,
        }
    player = player_data[user_id]
    refresh_streak(player)
    return player

def get_guild_data(guild_name):
    if guild_name not in guild_data:
        guild_data[guild_name] = {
            "name": guild_name,
            "created_at": datetime.now(),
            "members": [],
            "balance": 0,
            "level": 1,
            "perks": [],
        }
    return guild_data[guild_name]

# ===== EVENTS =====
def start_background_loops():
    """Start each loop exactly once.

    on_ready fires again after every reconnect, and calling .start() on a loop
    that is already running raises RuntimeError - which killed on_ready, so the
    later loops were never started at all.
    """
    for loop in (ocean_events, update_weather, random_events, bump_reminders,
                 weekly_prompt, autosave):
        if not loop.is_running():
            loop.start()


@bot.event
async def on_ready():
    print(f'✨ {bot.user} has set sail on Odyssey Lands!')
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print(f"Not a member of guild {GUILD_ID} yet - invite the bot and restart.")
    else:
        print(f"Guild: {guild.name} ({guild.id}), {guild.member_count} members")
    start_background_loops()
    print("Commands ready: " + ", ".join(sorted(c.name for c in bot.commands)))


@bot.event
async def on_message(message):
    """Commands only.

    The random 8% replies, 12% reactions, 18-keyword responder and the silence
    triggers that lived here made Tidewarden talk over real conversation in
    every channel. It now speaks when it is asked something.
    """
    await bot.process_commands(message)

@tasks.loop(minutes=OCEAN_EVENT_MINUTES)
async def ocean_events():
    for guild in bot.guilds:
        channel = flavour_channel(guild)
        if channel:
            try:
                event = random.choice(OCEAN_EVENTS)
                embed = discord.Embed(description=event, color=discord.Color.dark_teal())
                embed.set_footer(text=f"Weather: {weather_status}")
                await channel.send(embed=embed)
            except:
                pass

@tasks.loop(minutes=5)
async def update_weather():
    global weather_status
    weather_status = random.choice(WEATHER_TYPES)

@tasks.loop(minutes=5)
async def autosave():
    """Persist profiles. A 24-hour loop could never fire in a 5-hour run, so the
    streak work moved into refresh_streak() and only the save needs a timer."""
    save_state()


@tasks.loop(minutes=30)
async def weekly_prompt():
    """One conversation starter a week, in #general."""
    now = datetime.now(timezone.utc)
    if now.weekday() != WEEKLY_PROMPT_WEEKDAY or now.hour != WEEKLY_PROMPT_HOUR_UTC:
        return
    today = now.date().isoformat()
    if state_meta.get("last_weekly_prompt") == today:
        return

    channel = bot.get_channel(PROMPT_CHANNEL_ID)
    if channel is None:
        print(f"Weekly prompt: channel {PROMPT_CHANNEL_ID} not found")
        return
    if not channel.permissions_for(channel.guild.me).send_messages:
        print("Weekly prompt: no Send Messages permission in the prompt channel")
        return

    week = now.isocalendar()[1]
    prompt = WEEKLY_PROMPTS[week % len(WEEKLY_PROMPTS)]
    try:
        await channel.send(f"**This week:** {prompt}")
    except discord.HTTPException as exc:
        print(f"Weekly prompt failed: {exc}")
        return
    state_meta["last_weekly_prompt"] = today
    save_state()

@tasks.loop(minutes=RANDOM_EVENT_MINUTES)
async def random_events():
    """Trigger random world events"""
    if random.random() < 0.5:  # coin flip every 3 hours
        for guild in bot.guilds:
            channel = flavour_channel(guild)
            if channel:
                event_type = random.choice([
                    "treasure_found",
                    "pirate_attack",
                    "blessing",
                    "meteor_shower",
                    "bonus_hour",
                ])

                # Scene setting only. These used to promise 5000-coin claims,
                # free coin drops and 3x/10x reward windows that no command
                # actually implemented - players noticed nobody ever got paid.
                if event_type == "treasure_found":
                    embed = discord.Embed(
                        title="💎 Something glints on the tideline",
                        description="A chest has washed up somewhere on the coast. Nothing in it is scripted - go and look, then tell the others what you found.",
                        color=discord.Color.gold()
                    )
                elif event_type == "pirate_attack":
                    embed = discord.Embed(
                        title="🏴‍☠️ Sails on the horizon",
                        description="A pirate ship is drifting past the east shoal. Roleplay it out, or claim the wreck as your new base.",
                        color=discord.Color.red()
                    )
                elif event_type == "blessing":
                    embed = discord.Embed(
                        title="✨ The tide turns kind",
                        description="Flat water, clear sky, nothing trying to kill you. A good day for a long sail.",
                        color=discord.Color.gold()
                    )
                elif event_type == "meteor_shower":
                    embed = discord.Embed(
                        title="☄️ Meteor shower tonight",
                        description="Streaks of light over the north ridge. Worth climbing somewhere high for.",
                        color=discord.Color.purple()
                    )
                else:  # bonus_hour
                    embed = discord.Embed(
                        title="⚡ Golden hour",
                        description="The whole island is lit orange. Screenshot weather, nothing more.",
                        color=discord.Color.gold()
                    )

                embed.set_footer(text="Scene setting only - coins come from /fish, /explore and /daily.")

                try:
                    await channel.send(embed=embed)
                except:
                    pass

@tasks.loop(minutes=BUMP_REMINDER_MINUTES)
async def bump_reminders():
    """Nudge a human to run the listing bots' bump commands (bots can't)."""
    start, end = BUMP_QUIET_HOURS_UTC
    hour = datetime.now(timezone.utc).hour
    if start > end:
        if hour >= start or hour < end:
            return
    elif start <= hour < end:
        return

    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
        return

    # Plain text on purpose: @everyone is denied Embed Links in #📣-bump,
    # so an embed would fail there while the Bot role's Send Messages still works.
    lines = "\n".join(f"**{name}** - `{command}`" for name, command in BUMP_BOTS)
    message = (
        "**Bump time.** Four commands, about 15 seconds:\n"
        f"{lines}\n"
        "A bot can't run these - you can. This is what keeps the server in the listings."
    )
    try:
        await channel.send(message)
    except discord.HTTPException:
        pass


# ===== COMMANDS =====

@bot.hybrid_command(name='profile', description="Show a player's level, coins, pet and stats")
async def profile(ctx, member: discord.Member = None):
    """Check player profile with stats!"""
    if member is None:
        member = ctx.author

    player = get_player_data(member.id)

    embed = discord.Embed(
        title=f"⛵ {member.name}'s Profile",
        description=f"Level {player['level']} {player.get('active_title', '')}",
        color=discord.Color.blue()
    )

    embed.add_field(name="💰 Balance", value=f"🪙 {player['balance']}", inline=True)
    embed.add_field(name="📊 Level", value=f"Lvl {player['level']} ({player['xp']}/{player['xp_needed']} XP)", inline=True)
    embed.add_field(name="🎣 Catches", value=f"{player['catches']} fish", inline=True)
    embed.add_field(name="🗺️ Explored", value=f"{player['explored']} locations", inline=True)
    embed.add_field(name="🏆 Achievements", value=f"{len(player['achievements'])} unlocked", inline=True)
    embed.add_field(name="🐾 Pet", value=player['pet'] if player['pet'] else "None", inline=True)

    stats = player["stats"]
    embed.add_field(name="📈 Stats", value=f"""
    Total Coins: {stats['total_coins_earned']}
    Total Fish: {stats['total_fish_caught']}
    Duels: {stats['total_duels']} ({stats['duel_wins']} wins)
    Games: {stats['games_played']} ({stats['games_won']} wins)
    Quests: {stats['quests_completed']}
    """, inline=False)

    embed.add_field(name="📅 Streak", value=f"{player['login_streak']} days", inline=True)
    embed.add_field(name="🎯 Guild", value=player['guild'] if player['guild'] else "None", inline=True)

    await ctx.send(embed=embed)

@bot.hybrid_command(name='fish', description="Cast a line and catch a fish")
async def fish(ctx):
    """Cast a line and catch fish!"""
    player = get_player_data(ctx.author.id)

    # Pet bonus
    pet_bonus = 1.0
    if player['pet']:
        pet_bonus = PETS[player['pet']]["bonus"]

    if random.random() < 0.7:
        rarity_roll = random.random()
        if rarity_roll < 0.6:
            fish_type = random.choice([f for f in FISH if FISH[f]["rarity"] == "common"])
        elif rarity_roll < 0.85:
            fish_type = random.choice([f for f in FISH if FISH[f]["rarity"] == "rare"])
        elif rarity_roll < 0.95:
            fish_type = random.choice([f for f in FISH if FISH[f]["rarity"] == "epic"])
        else:
            fish_type = random.choice([f for f in FISH if FISH[f]["rarity"] == "legendary"])

        fish_info = FISH[fish_type]
        value = int(fish_info["value"] * pet_bonus)
        xp = int(fish_info["xp"] * (1 + player['level'] / 10))

        player["inventory"].append(fish_type)
        player["balance"] += value
        player["catches"] += 1
        player["xp"] += xp
        player["stats"]["total_coins_earned"] += value
        player["stats"]["total_fish_caught"] += 1

        # Level up check
        while player["xp"] >= player["xp_needed"]:
            player["xp"] -= player["xp_needed"]
            player["level"] += 1
            player["xp_needed"] = int(player["xp_needed"] * 1.15)

        embed = discord.Embed(
            title=f"Caught: {fish_type}",
            description=f"{fish_info['emoji']} **+{value} coins** | **+{xp} XP**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Catches", value=player["catches"])
        embed.add_field(name="Balance", value=f"🪙 {player['balance']}")
        embed.add_field(name="Level", value=f"Lvl {player['level']} ({player['xp']}/{player['xp_needed']} XP)")
    else:
        embed = discord.Embed(
            title="Nothing on the line",
            description="It got away. Cast again.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Weather: {weather_status}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name='explore', description="Explore an ocean location for coins and XP")
async def explore(ctx):
    """Explore mysterious locations!"""
    player = get_player_data(ctx.author.id)
    location = random.choice(EXPLORE_LOCATIONS)

    pet_bonus = 1.0
    if player['pet']:
        pet_bonus = PETS[player['pet']]["bonus"]

    reward = int(random.randint(location["reward"][0], location["reward"][1]) * pet_bonus)
    xp = int(location["xp"] * (1 + player['level'] / 10))

    player["balance"] += reward
    player["explored"] += 1
    player["xp"] += xp
    player["stats"]["total_coins_earned"] += reward

    while player["xp"] >= player["xp_needed"]:
        player["xp"] -= player["xp_needed"]
        player["level"] += 1
        player["xp_needed"] = int(player["xp_needed"] * 1.15)

    embed = discord.Embed(
        title=f"⛵ Explored {location['name']}! {location['emoji']}",
        description=f"*{location['description']}*\n\n**Found {reward} coins!** | **+{xp} XP**",
        color=discord.Color.green()
    )
    embed.add_field(name="Total Explorations", value=player["explored"])
    embed.add_field(name="Balance", value=f"🪙 {player['balance']}")
    embed.add_field(name="Level", value=f"Lvl {player['level']} ({player['xp']}/{player['xp_needed']} XP)")
    embed.set_footer(text=f"Weather: {weather_status}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name='daily', description="Claim your daily coins, streak bonus included")
async def daily(ctx):
    """Claim your daily bonus!"""
    player = get_player_data(ctx.author.id)

    today = datetime.now().date()
    last_bonus = player.get("daily_bonus", 0)

    if isinstance(last_bonus, str):
        last_bonus_date = datetime.fromisoformat(last_bonus).date()
    else:
        last_bonus_date = None

    if last_bonus_date == today:
        await ctx.send("Already claimed today. Back tomorrow.")
        return

    # Base bonus + streak bonus
    base_bonus = 100
    streak_bonus = player["login_streak"] * 50
    total_bonus = base_bonus + streak_bonus

    player["balance"] += total_bonus
    player["daily_bonus"] = datetime.now().isoformat()

    embed = discord.Embed(
        title="Daily coins",
        description=f"**+{total_bonus}** ({base_bonus} base + {streak_bonus} streak)",
        color=discord.Color.gold()
    )
    embed.add_field(name="Login Streak", value=f"🔥 {player['login_streak']} days", inline=True)
    embed.add_field(name="New Balance", value=f"🪙 {player['balance']}", inline=True)
    await ctx.send(embed=embed)

@bot.hybrid_command(name='duel', description="Duel another member for coins and XP")
async def duel(ctx, opponent: discord.Member):
    """Challenge someone to a duel!"""
    if opponent.bot:
        await ctx.send("Bots don't duel.")
        return

    challenger = get_player_data(ctx.author.id)
    opponent_data = get_player_data(opponent.id)

    challenger["stats"]["total_duels"] += 1
    opponent_data["stats"]["total_duels"] += 1

    # Weighted by level
    challenger_power = challenger["level"] + random.randint(1, 20)
    opponent_power = opponent_data["level"] + random.randint(1, 20)

    if challenger_power > opponent_power:
        reward = max(50, int(opponent_data["balance"] * 0.1))
        challenger["balance"] += reward
        challenger["stats"]["duel_wins"] += 1
        challenger["xp"] += 50

        embed = discord.Embed(
            title="⚔️ Duel Complete!",
            description=f"🏆 {ctx.author.mention} defeated {opponent.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Winner Rewards", value=f"**+{reward} coins** | **+50 XP**")
    else:
        reward = max(50, int(challenger["balance"] * 0.1))
        opponent_data["balance"] += reward
        opponent_data["stats"]["duel_wins"] += 1
        opponent_data["xp"] += 50

        embed = discord.Embed(
            title="⚔️ Duel Complete!",
            description=f"🏆 {opponent.mention} defeated {ctx.author.mention}!",
            color=discord.Color.red()
        )
        embed.add_field(name="Winner Rewards", value=f"**+{reward} coins** | **+50 XP**")

    await ctx.send(embed=embed)

@bot.hybrid_command(name='blackjack', description="Play a hand of blackjack")
async def blackjack(ctx):
    """Play blackjack!"""
    player = get_player_data(ctx.author.id)

    # Simple blackjack
    player_score = random.randint(10, 21)
    dealer_score = random.randint(10, 21)

    player["stats"]["games_played"] += 1

    if player_score > 21:
        embed = discord.Embed(title="♠️ Blackjack", description="❌ BUST! You lose!", color=discord.Color.red())
    elif dealer_score > 21:
        reward = random.randint(100, 300)
        player["balance"] += reward
        player["stats"]["games_won"] += 1
        embed = discord.Embed(
            title="♠️ Blackjack",
            description=f"🏆 Dealer busts! You win **{reward} coins**!",
            color=discord.Color.green()
        )
    elif player_score > dealer_score:
        reward = random.randint(100, 300)
        player["balance"] += reward
        player["stats"]["games_won"] += 1
        embed = discord.Embed(
            title="♠️ Blackjack",
            description=f"🏆 You win **{reward} coins**! ({player_score} vs {dealer_score})",
            color=discord.Color.green()
        )
    elif player_score == dealer_score:
        embed = discord.Embed(
            title="♠️ Blackjack",
            description=f"🤝 Push! You tie with the dealer! ({player_score})",
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="♠️ Blackjack",
            description=f"❌ Dealer wins! ({player_score} vs {dealer_score})",
            color=discord.Color.red()
        )

    embed.add_field(name="Your Score", value=player_score)
    embed.add_field(name="Dealer Score", value=dealer_score)
    embed.add_field(name="Balance", value=f"🪙 {player['balance']}")

    await ctx.send(embed=embed)

@bot.hybrid_command(name='slots', description="Spin the slot machine")
async def slots(ctx):
    """Spin the slot machine!"""
    player = get_player_data(ctx.author.id)

    symbols = ["🍎", "🍊", "🍋", "🎰", "💎", "👑"]
    spin = [random.choice(symbols) for _ in range(3)]

    player["stats"]["games_played"] += 1

    embed = discord.Embed(title="🎰 SLOTS", description=f"**{spin[0]} | {spin[1]} | {spin[2]}**", color=discord.Color.gold())

    if spin[0] == spin[1] == spin[2]:
        if spin[0] == "💎":
            reward = 5000
        elif spin[0] == "👑":
            reward = 3000
        else:
            reward = 500

        player["balance"] += reward
        player["stats"]["games_won"] += 1
        embed.add_field(name="Result", value=f"🎉 JACKPOT! Won **{reward} coins**!")
        embed.color = discord.Color.gold()
    elif spin[0] == spin[1] or spin[1] == spin[2]:
        reward = 200
        player["balance"] += reward
        player["stats"]["games_won"] += 1
        embed.add_field(name="Result", value=f"✨ Two match! Won **{reward} coins**!")
        embed.color = discord.Color.blue()
    else:
        embed.add_field(name="Result", value="❌ No match. Better luck next time!")
        embed.color = discord.Color.red()

    embed.add_field(name="Balance", value=f"🪙 {player['balance']}")

    await ctx.send(embed=embed)

@bot.hybrid_command(name='coin_flip', description="Flip a coin")
async def coin_flip(ctx):
    """Flip a coin!"""
    player = get_player_data(ctx.author.id)
    amount = random.randint(10, 50)

    player["stats"]["games_played"] += 1

    if random.random() < 0.5:
        player["balance"] += amount
        player["stats"]["games_won"] += 1
        await ctx.send(f"🪙 Heads! You won **{amount} coins**! Balance: **{player['balance']}**")
    else:
        await ctx.send(f"🪙 Tails! Better luck next time! Balance: **{player['balance']}**")

@bot.hybrid_command(name='dice', description="Roll a die")
async def dice(ctx):
    """Roll the dice!"""
    player = get_player_data(ctx.author.id)
    roll = random.randint(1, 6)
    reward = roll * 25

    player["balance"] += reward
    player["stats"]["games_played"] += 1
    player["stats"]["games_won"] += 1

    await ctx.send(f"🎲 You rolled a **{roll}**! Won **{reward} coins**! Balance: **{player['balance']}**")

@bot.hybrid_command(name='roulette', description="Spin the roulette wheel")
async def roulette(ctx):
    """Spin the roulette wheel!"""
    player = get_player_data(ctx.author.id)
    prizes = [100, 50, 75, 25, 150, 10, 500, 200]
    prize = random.choice(prizes)

    player["balance"] += prize
    player["stats"]["games_played"] += 1
    if prize >= 150:
        player["stats"]["games_won"] += 1

    await ctx.send(f"🎡 Spin! You won **{prize} coins**! Balance: **{player['balance']}**")

@bot.hybrid_command(name='quest', description="Show your active quests")
async def quest(ctx):
    """View and complete quests!"""
    player = get_player_data(ctx.author.id)

    if not player.get("quests"):
        # Assign random quests
        player["quests"] = {q["id"]: {"progress": 0, "completed": False} for q in random.sample(QUESTS, 3)}

    embed = discord.Embed(title="📋 Active Quests", color=discord.Color.purple())

    for quest_id, quest_data in player["quests"].items():
        quest_info = next((q for q in QUESTS if q["id"] == quest_id), None)
        if quest_info:
            progress = quest_data.get("progress", 0)
            target = quest_info["target"]
            status = "✅ COMPLETED" if quest_data.get("completed") else f"{progress}/{target}"
            embed.add_field(
                name=quest_info["name"],
                value=f"{quest_info['description']}\n💰 Reward: {quest_info['reward']} coins\nProgress: {status}",
                inline=False
            )

    await ctx.send(embed=embed)

@bot.hybrid_command(name='pet', description="Browse, adopt or inspect pets")
async def pet(ctx, action=None, pet_name=None):
    """Manage your pet!"""
    player = get_player_data(ctx.author.id)

    if action == "shop":
        embed = discord.Embed(title="🐾 Pet Shop", color=discord.Color.purple())
        for key, pet_info in PETS.items():
            embed.add_field(
                name=pet_info["name"],
                value=f"Cost: {pet_info['cost']} coins\nBonus: {int((pet_info['bonus']-1)*100)}%\nAbility: {pet_info['ability']}",
                inline=False
            )
        embed.add_field(name="Usage", value="!pet adopt [pet_name]", inline=False)
        await ctx.send(embed=embed)

    elif action == "adopt" and pet_name:
        pet_name = pet_name.lower()
        if pet_name not in PETS:
            await ctx.send("No pet by that name. `/pet shop` lists them.")
            return

        pet_info = PETS[pet_name]
        if player["balance"] < pet_info["cost"]:
            await ctx.send(f"That costs {pet_info['cost']}. You have {player['balance']}.")
            return

        player["balance"] -= pet_info["cost"]
        player["pet"] = pet_name
        player["pet_level"] = 1

        await ctx.send(f"Adopted {pet_info['name']} - {int((pet_info['bonus']-1)*100)}% bonus from now on.")

    elif action == "info":
        if not player["pet"]:
            await ctx.send("You don't have a pet yet. `/pet shop` has them.")
            return

        pet_info = PETS[player["pet"]]
        embed = discord.Embed(
            title=f"🐾 Your Pet: {pet_info['name']}",
            description=f"Level: {player['pet_level']}\nAbility: {pet_info['ability']}\nBonus: {int((pet_info['bonus']-1)*100)}%",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(title="🐾 Pet Commands", description="""
        !pet shop - Browse available pets
        !pet adopt [name] - Adopt a pet
        !pet info - View your pet info
        """, color=discord.Color.purple())
        await ctx.send(embed=embed)

@bot.hybrid_command(name='achievements', description="Show achievements and progress")
async def achievements(ctx, member: discord.Member = None):
    """View achievements!"""
    if member is None:
        member = ctx.author

    player = get_player_data(member.id)

    embed = discord.Embed(title=f"🏆 {member.name}'s Achievements", color=discord.Color.gold())

    for achievement_id, achievement_info in ACHIEVEMENTS.items():
        if achievement_id in player["achievements"]:
            status = "✅"
        else:
            status = "🔒"
        embed.add_field(
            name=f"{status} {achievement_info['name']}",
            value=f"{achievement_info['description']}\n💰 {achievement_info['reward']} coins",
            inline=False
        )

    embed.add_field(name="Total Unlocked", value=f"{len(player['achievements'])}/{len(ACHIEVEMENTS)}", inline=False)

    await ctx.send(embed=embed)

@bot.hybrid_command(name='title', description="Set the title shown on your profile")
async def title(ctx, title_name=None):
    """Set your title!"""
    player = get_player_data(ctx.author.id)

    if title_name is None:
        embed = discord.Embed(title="👑 Available Titles", color=discord.Color.gold())
        for title_key, title_text in TITLES.items():
            embed.add_field(name=title_key, value=title_text, inline=False)
        embed.add_field(name="Usage", value="!title [title_name]", inline=False)
        await ctx.send(embed=embed)
    else:
        if title_name.lower() not in TITLES:
            await ctx.send("No title by that name. `/title` lists them.")
            return

        player["active_title"] = TITLES[title_name.lower()]
        await ctx.send(f"Title set: {player['active_title']}")

@bot.hybrid_command(name='leaderboard', description="Top 10 explorers by coins")
async def leaderboard(ctx):
    """View the leaderboard!"""
    if not player_data:
        await ctx.send("Nobody's on the board yet.")
        return

    sorted_players = sorted(player_data.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]

    embed = discord.Embed(title="🏆 Odyssey Lands Leaderboard", description="Top 10 Richest Explorers", color=discord.Color.gold())

    for idx, (user_id, data) in enumerate(sorted_players, 1):
        try:
            user = await bot.fetch_user(user_id)
            embed.add_field(
                name=f"#{idx} - {user.name}",
                value=f"🪙 {data['balance']} | Lvl {data['level']} | 🎣 {data['catches']} catches",
                inline=False
            )
        except:
            pass

    await ctx.send(embed=embed)

@bot.hybrid_command(name='inventory', description="Show a player's fish and coins")
async def inventory(ctx, member: discord.Member = None):
    """Check inventory!"""
    if member is None:
        member = ctx.author

    player = get_player_data(member.id)

    embed = discord.Embed(title=f"🎒 {member.name}'s Inventory", color=discord.Color.purple())

    if player["inventory"]:
        fish_count = {}
        for fish in player["inventory"]:
            fish_count[fish] = fish_count.get(fish, 0) + 1

        inventory_text = ""
        for fish, count in fish_count.items():
            emoji = FISH[fish]["emoji"]
            inventory_text += f"{emoji} **{fish}** x{count}\n"

        embed.add_field(name="Fish Caught", value=inventory_text, inline=False)
    else:
        embed.add_field(name="Fish Caught", value="*Empty... time to go fishing!*")

    embed.add_field(name="💰 Balance", value=f"🪙 {player['balance']} coins")
    embed.add_field(name="🎣 Total Catches", value=player["catches"])
    embed.add_field(name="⛵ Locations Explored", value=player["explored"])

    await ctx.send(embed=embed)

@bot.hybrid_command(name='weather', description="Current ocean weather")
async def weather(ctx):
    """Check weather!"""
    embed = discord.Embed(title="🌊 Ocean Weather", description=f"Current Conditions: **{weather_status}**", color=discord.Color.blue())

    weather_descriptions = {
        "Calm": "Flat water, no wind.",
        "Stormy": "Rough swell, bad visibility.",
        "Misty": "Fog on the water.",
        "Sunny": "Clear sky.",
        "Foggy": "Low visibility.",
        "Magical": "Something in the air.",
        "Cursed": "The water looks wrong.",
        "Blessed": "Kind weather for once.",
    }

    embed.add_field(name="Conditions", value=weather_descriptions.get(weather_status, "Unknown"))
    await ctx.send(embed=embed)

@bot.hybrid_command(name='help_odyssey', description="Full Tidewarden command guide")
async def help_odyssey(ctx):
    """Every command, with the prefix and slash names."""
    embed = discord.Embed(
        title="⛵ Tidewarden — command guide",
        description=(
            "Every command works both ways: slash (`/fish`) or prefix (`!fish`). "
            "Slash is easier — type `/` and Discord shows the list with descriptions.\n\n"
            "**New here?** Start with `/profile`, then `/fish` and `/daily`."
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(name="🎣 SMP and server", value=(
        "`/start` — is the server online, and how to start it if not\n"
        "`/server` — addresses, ports and live status\n"
        "`/roles` — the self-serve role menu\n"
        "`/guide` — this guide"
    ), inline=False)

    embed.add_field(name="🎮 Core", value=(
        "`/fish` — catch something\n"
        "`/explore` — visit a location for coins and XP\n"
        "`/daily` — daily coins, bigger with a streak\n"
        "`/duel @player` — duel for coins\n"
        "`/profile [@player]` — level, coins, pet, stats"
    ), inline=False)

    embed.add_field(name="🎰 Mini-games", value=(
        "`/blackjack` · `/slots` · `/coin_flip` · `/dice` · `/roulette`"
    ), inline=False)

    embed.add_field(name="🎯 Progression", value=(
        "`/quest` — your active quests\n"
        "`/achievements [@player]` — unlocked and locked\n"
        "`/title [name]` — set your profile title\n"
        "`/pet [shop|adopt|info]` — pets and their bonuses"
    ), inline=False)

    embed.add_field(name="📊 Info", value=(
        "`/inventory [@player]` · `/leaderboard` · `/weather`"
    ), inline=False)

    embed.add_field(name="📌 Notes", value=(
        "• Coins and levels are saved between restarts.\n"
        "• The ambient ocean events in #event-announcements are flavour only — "
        "no rewards are attached to them.\n"
        "• Tidewarden cannot press Start on the Aternos panel; `/start` explains "
        "who can."
    ), inline=False)

    await ctx.send(embed=embed)


@bot.hybrid_command(name='guide', description="The full Tidewarden command guide")
async def guide(ctx):
    """Same guide as /help_odyssey, posted as a normal message people can pin."""
    await help_odyssey.callback(ctx)


# ===== WIRING =====
import odyssey_community

odyssey_community.register(bot, {
    "name": SERVER_NAME,
    "java_host": SERVER_JAVA_HOST,
    "java_port": SERVER_JAVA_PORT,
    "bedrock_host": SERVER_BEDROCK_HOST,
    "bedrock_port": SERVER_BEDROCK_PORT,
    "panel_url": SERVER_PANEL_URL,
    "invite": SERVER_DISCORD_INVITE,
})


async def setup_hook():
    """Registered before the gateway connects: load profiles, re-attach the role
    menus, and publish the slash commands so they appear immediately."""
    load_state()
    bot.add_view(odyssey_community.RolePanelView())

    guild = discord.Object(id=GUILD_ID)
    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} slash command(s) to guild {GUILD_ID}")
    except discord.HTTPException as exc:
        print(f"Guild slash sync failed ({exc}); trying a global sync instead")
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s) globally "
                  "(Discord can take up to an hour to show these)")
        except discord.HTTPException as fallback_exc:
            print(f"Global slash sync failed too: {fallback_exc}")

    asyncio.create_task(run_budget_watchdog())


async def run_budget_watchdog():
    """Stop cleanly before the next cron run starts, so two bots never answer the
    same command. The old workflow ran 350 minutes on a 300-minute schedule."""
    await asyncio.sleep(RUN_BUDGET_MINUTES * 60)
    print(f"Run budget of {RUN_BUDGET_MINUTES} minutes reached — saving and stopping.")
    save_state()
    await bot.close()


bot.setup_hook = setup_hook

# Run bot
if __name__ == '__main__':
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass
    token = os.environ.get('DISCORD_TOKEN')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("DISCORD_TOKEN environment variable is not set. Refusing to start.")
        raise SystemExit("DISCORD_TOKEN environment variable is not set.")
    bot.run(token)
