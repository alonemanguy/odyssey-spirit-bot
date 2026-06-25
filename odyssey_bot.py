import discord
from discord.ext import commands, tasks
import random
import json
from datetime import datetime, timedelta
import asyncio

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Data storage - MASSIVE EXPANSION
player_data = {}
guild_data = {}
quest_log = {}
pet_data = {}
weather_status = "Calm"
silent_guilds = set()
SILENCE_DURATION = 20 * 60
SILENCE_TRIGGERS = ["shut up", "shutup", "stfu", "shush", "shh", "shadup", "shaddup", "be quiet"]

# ===== ACHIEVEMENT SYSTEM =====
ACHIEVEMENTS = {
    "first_fish": {"name": "First Catch", "description": "Caught your first fish!", "reward": 100},
    "fish_master": {"name": "Fish Master", "description": "Caught 100 fish!", "reward": 500},
    "explorer": {"name": "Explorer", "description": "Visited all locations!", "reward": 1000},
    "millionaire": {"name": "Millionaire", "description": "Earned 1,000,000 coins!", "reward": 5000},
    "level_50": {"name": "Half Century", "description": "Reached level 50!", "reward": 2000},
    "level_100": {"name": "Legend", "description": "Reached level 100!", "reward": 10000},
    "duelist": {"name": "Duelist", "description": "Won 10 duels!", "reward": 800},
    "guild_master": {"name": "Guild Master", "description": "Created a guild!", "reward": 1500},
    "pet_lover": {"name": "Pet Lover", "description": "Adopted a pet!", "reward": 300},
    "quest_hero": {"name": "Quest Hero", "description": "Completed 10 quests!", "reward": 1200},
    "streak_warrior": {"name": "Streak Warrior", "description": "7-day login streak!", "reward": 2000},
    "treasure_hunter": {"name": "Treasure Hunter", "description": "Found a hidden treasure!", "reward": 5000},
}

# ===== QUESTS SYSTEM =====
QUESTS = [
    {"id": "catch_5", "name": "Catch 5 Fish", "description": "Catch 5 fish", "reward": 250, "type": "fishing", "target": 5},
    {"id": "explore_3", "name": "Explore 3 Locations", "description": "Explore 3 different locations", "reward": 300, "type": "exploring", "target": 3},
    {"id": "win_dice", "name": "Win 3 Dice Rolls", "description": "Win 3 dice rolls", "reward": 200, "type": "games", "target": 3},
    {"id": "earn_1k", "name": "Earn 1000 Coins", "description": "Earn 1000 coins total", "reward": 500, "type": "coins", "target": 1000},
    {"id": "duel_win", "name": "Win a Duel", "description": "Win a duel against another player", "reward": 400, "type": "duels", "target": 1},
    {"id": "level_up", "name": "Level Up", "description": "Reach next level", "reward": 300, "type": "level", "target": 1},
    {"id": "blackjack_win", "name": "Blackjack Ace", "description": "Win a blackjack game", "reward": 350, "type": "games", "target": 1},
    {"id": "mystery_box", "name": "Open Mystery Box", "description": "Open a mystery box", "reward": 450, "type": "items", "target": 1},
]

# ===== PETS SYSTEM =====
PETS = {
    "dolphin": {"name": "🐬 Dolphin", "rarity": "common", "cost": 500, "bonus": 1.1, "ability": "Faster fishing"},
    "phoenix": {"name": "🔥 Phoenix", "rarity": "rare", "cost": 2000, "bonus": 1.25, "ability": "2x rewards on critical"},
    "dragon": {"name": "🐉 Dragon", "rarity": "legendary", "cost": 10000, "bonus": 1.5, "ability": "Triple luck"},
    "mermaid": {"name": "🧜‍♀️ Mermaid", "rarity": "rare", "cost": 1500, "bonus": 1.2, "ability": "Ocean blessing"},
    "kraken": {"name": "🐙 Kraken", "rarity": "legendary", "cost": 15000, "bonus": 2.0, "ability": "Legendary spawns"},
    "shark": {"name": "🦈 Shark", "rarity": "rare", "cost": 1800, "bonus": 1.15, "ability": "Aggressive fishing"},
    "unicorn": {"name": "🦄 Unicorn", "rarity": "legendary", "cost": 12000, "bonus": 1.8, "ability": "Rainbow luck"},
    "phoenix_egg": {"name": "🥚 Phoenix Egg", "rarity": "epic", "cost": 5000, "bonus": 1.35, "ability": "Rebirth blessing"},
}

# ===== TITLES SYSTEM =====
TITLES = {
    "fisherman": "🎣 Master Fisherman",
    "explorer": "🗺️ Ocean Explorer",
    "rich": "💎 Coin Magnate",
    "legendary": "⭐ Legend",
    "duelist": "⚔️ Duelist King",
    "guild_master": "👑 Guild Master",
    "pet_master": "🐾 Pet Master",
    "quest_hero": "🎯 Quest Hero",
    "gambler": "🎰 Gambler",
    "collector": "🏆 Collector",
    "speedrunner": "⚡ Speedrunner",
    "immortal": "💀 Immortal",
    "conqueror": "🚀 Conqueror",
    "merchant": "💰 Merchant",
    "alchemist": "🧪 Alchemist",
}

# ===== OCEAN EVENTS =====
OCEAN_EVENTS = [
    "🌊 A pod of dolphins swims past Odyssey Lands!",
    "⚓ An ancient shipwreck is spotted on the horizon...",
    "🐙 A mysterious octopus emerges from the depths!",
    "🌩️ Dark clouds gather over the ocean...",
    "🏝️ A new island appears through the fog!",
    "💎 Gleaming pearls wash ashore on the beach!",
    "🦈 A shark fin cuts through the water!",
    "🌅 The most beautiful sunrise breaks over the waters...",
    "🗺️ An old treasure map washes up on shore!",
    "🪼 Jellyfish glow beneath the surface!",
    "👻 A ghost ship appears in the mist!",
    "⛈️ A massive storm approaches the island!",
    "🎆 Magical aurora lights dance across the sky!",
    "🌙 The moon shines with mysterious power!",
    "🏴‍☠️ A pirate ship sails by menacingly!",
    "✨ Magical sparkles appear in the water!",
    "🌺 Exotic flowers bloom across the island!",
    "❄️ Unexpected snow falls on the tropical island!",
    "🔥 Volcanic eruption in the distance!",
    "🎭 Mystical beings appear from nowhere!",
]

# ===== CHAT RESPONSES =====
CHAT_RESPONSES = [
    "Yo, that's cool! 😎", "Facts! 🔥", "Lmaooo 💀", "Real talk! 🤔",
    "That hits different 🎯", "Let's goooo! 🚀", "Straight up! 💪",
    "That's fire 🔥", "Bet! 🙌", "No cap! 💯", "Ate and left no crumbs! 💅",
    "Period sis! 💋", "Slay! 👑", "Snatched! 💪", "Unmatched! 🔝",
    "W take! 🏆", "Icon behavior! 👑", "Periodt! ✨",
]

# ===== MEGA KEYWORDS =====
MEGA_KEYWORDS = {
    "meme": ["Hahaha! 😂", "That's hilarious! 😭", "Peak comedy! 💀", "Send more memes! 🤣"],
    "funny": ["I'm dead! 😂", "That's too good! 🔥", "Stop it! 😂", "I can't breathe! 😭"],
    "lol": ["Right?? 😂", "I know right! 🤣", "Too funny! 😭", "Lmaoooo 🤣"],
    "omg": ["That's insane! 🤯", "No way! 😱", "That's crazy! 💥", "Mind blown! 🤯"],
    "67": ["That's 67! 🔥", "East London gang! 🏴", "Drill szn! 🎤", "Road man energy! 🌍"],
    "drill": ["Drill beats! 🔥", "That flow! 💯", "UK drill! 🏴", "Bars! 🔥"],
    "fanum tax": ["Fanum tax! 🍗", "He ate! 😂", "Food gone! 🍴", "That's the move! 💪"],
    "kai cenat": ["Kai vibes! 🎮", "Streaming legend! 📹", "That's a W! 🏆", "Content king! 👑"],
    "valid": ["That's valid! ✅", "Facts! 💯", "Can't argue! 🙏", "I agree! 👍"],
    "slay": ["Slay queen! 👑", "That's slaying! 💅", "Serving! 💃", "Killed it! 💀"],
    "ate": ["You ate! 🍽️", "Consumed! 😋", "Devoured! 🤤", "That's serving! 🍴"],
    "gaming": ["What game? 🎮", "Gaming life! 🎯", "Gaming szn! 🚀", "That gameplay! 🔥"],
    "minecraft": ["Minecraft goated! 🎮", "Building time! 🏗️", "Creative szn! 🎨", "That base! 🏰"],
    "fortnite": ["Victory royale! 👑", "That build! 🏗️", "Shotgun pop! 💥", "Bush camping! 🌳"],
    "valorant": ["One tap! 💀", "Plant spike! 💣", "Clutch! 🔥", "That crosshair! 🎯"],
    "music": ["Music life! 🎵", "What's playing? 🎧", "That song slaps! 🎵", "Drop banger! 🔥"],
    "happy": ["Yay! 🎉", "Good vibes! ✨", "Happiness! 😊", "Let's go! 🙌"],
    "sad": ["Gets better! 💙", "I'm here! 🤝", "You're strong! 💪", "Better days! 🌈"],
}

# ===== FISH TYPES =====
FISH = {
    "Common Bass": {"rarity": "common", "value": 10, "emoji": "🐟", "xp": 5},
    "Silver Flounder": {"rarity": "common", "value": 15, "emoji": "🐟", "xp": 8},
    "Golden Seahorse": {"rarity": "rare", "value": 50, "emoji": "🐴", "xp": 25},
    "Crystal Angelfish": {"rarity": "rare", "value": 60, "emoji": "✨🐟", "xp": 30},
    "Legendary Kraken Tentacle": {"rarity": "legendary", "value": 500, "emoji": "🐙", "xp": 100},
    "Mythical Leviathan Scale": {"rarity": "legendary", "value": 750, "emoji": "🔷", "xp": 150},
    "Glowing Jellyfish": {"rarity": "epic", "value": 200, "emoji": "🪼", "xp": 50},
    "Ghost Fish": {"rarity": "epic", "value": 180, "emoji": "👻", "xp": 45},
    "Rainbow Trout": {"rarity": "rare", "value": 75, "emoji": "🌈", "xp": 35},
    "Cursed Fish": {"rarity": "legendary", "value": 600, "emoji": "💀", "xp": 120},
}

# ===== EXPLORE LOCATIONS =====
EXPLORE_LOCATIONS = [
    {"name": "Coral Reef", "emoji": "🪸", "reward": (20, 40), "description": "A vibrant underwater garden", "xp": 10},
    {"name": "Shipwreck Graveyard", "emoji": "⚓", "reward": (50, 100), "description": "Ruins of ancient vessels", "xp": 25},
    {"name": "Luminescent Cavern", "emoji": "✨", "reward": (60, 120), "description": "A cave filled with glowing crystals", "xp": 30},
    {"name": "Mermaid Lagoon", "emoji": "🧜‍♀️", "reward": (40, 80), "description": "A mysterious hidden lagoon", "xp": 20},
    {"name": "Volcanic Island", "emoji": "🌋", "reward": (80, 150), "description": "Hot lava flows and rare minerals", "xp": 40},
    {"name": "Ghost Ship", "emoji": "👻", "reward": (100, 200), "description": "A cursed vessel from the past", "xp": 50},
    {"name": "Atlantis Ruins", "emoji": "🏛️", "reward": (150, 300), "description": "Lost city of Atlantis!", "xp": 75},
    {"name": "Kraken's Lair", "emoji": "🐙", "reward": (200, 400), "description": "Home of the mighty Kraken", "xp": 100},
    {"name": "Dragon's Peak", "emoji": "🐉", "reward": (180, 350), "description": "Mountain where dragons dwell", "xp": 85},
    {"name": "Treasure Vault", "emoji": "💎", "reward": (250, 500), "description": "Hidden treasure chamber", "xp": 120},
]

# ===== CONSTANTS =====
WEATHER_TYPES = ["Calm", "Stormy", "Misty", "Sunny", "Foggy", "Magical", "Cursed", "Blessed"]
FUN_EMOJIS = ["😂", "🔥", "💯", "🎉", "✨", "🚀", "💪", "👑", "🙌", "💛", "😎", "💀", "🌟", "⚡", "🏆", "💎", "🎯", "💥"]

# ===== INITIALIZE PLAYER DATA =====
def get_player_data(user_id):
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
    return player_data[user_id]

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
@bot.event
async def on_ready():
    print(f'✨ {bot.user} has set sail on Odyssey Lands!')
    ocean_events.start()
    update_weather.start()
    daily_reset.start()
    random_events.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.guild and message.guild.id in silent_guilds:
        await bot.process_commands(message)
        return

    message_lower = message.content.lower()

    # Silence triggers
    for trig in SILENCE_TRIGGERS:
        if trig in message_lower:
            guild_id = message.guild.id if message.guild else None
            if guild_id and guild_id not in silent_guilds:
                silent_guilds.add(guild_id)
                try:
                    await message.channel.send("Alright, I'll shut up for 20 minutes. 🤫")
                except:
                    pass

                async def _unsilence_after(gid):
                    await asyncio.sleep(SILENCE_DURATION)
                    silent_guilds.discard(gid)
                    try:
                        guild = bot.get_guild(gid)
                        if guild:
                            general_channel = discord.utils.get(guild.text_channels, name='general')
                            if general_channel and general_channel.permissions_for(guild.me).send_messages:
                                await general_channel.send("I'm back! Odyssey Spirit is awake! 🌊")
                    except:
                        pass

                asyncio.create_task(_unsilence_after(guild_id))
            await bot.process_commands(message)
            return

    # Check keywords
    for keyword, responses in MEGA_KEYWORDS.items():
        if keyword in message_lower:
            response = random.choice(responses)
            try:
                await message.reply(response, mention_author=False)
            except:
                try:
                    await message.channel.send(response)
                except:
                    pass
            if random.random() < 0.6:
                try:
                    await message.add_reaction(random.choice(FUN_EMOJIS))
                except:
                    pass
            await bot.process_commands(message)
            return

    # Random responses
    if random.random() < 0.08:
        response = random.choice(CHAT_RESPONSES)
        try:
            await message.reply(response, mention_author=False)
        except:
            try:
                await message.channel.send(response)
            except:
                pass

    # Random reactions
    if random.random() < 0.12:
        try:
            await message.add_reaction(random.choice(FUN_EMOJIS))
        except:
            pass

    await bot.process_commands(message)

@tasks.loop(minutes=10)
async def ocean_events():
    for guild in bot.guilds:
        if guild.id in silent_guilds:
            continue
        general_channel = discord.utils.get(guild.text_channels, name='general')
        if general_channel and general_channel.permissions_for(guild.me).send_messages:
            try:
                event = random.choice(OCEAN_EVENTS)
                embed = discord.Embed(title="🌊 Ocean Event!", description=event, color=discord.Color.blue())
                embed.set_footer(text=f"Weather: {weather_status}")
                await general_channel.send(embed=embed)
            except:
                pass

@tasks.loop(minutes=5)
async def update_weather():
    global weather_status
    weather_status = random.choice(WEATHER_TYPES)

@tasks.loop(hours=24)
async def daily_reset():
    """Reset daily bonuses and streaks"""
    for user_id in player_data:
        player = player_data[user_id]
        today = datetime.now().date()
        last_login = player.get("last_login")
        
        if last_login:
            last_login_date = datetime.fromisoformat(last_login).date()
            if last_login_date == today:
                continue
            elif (today - last_login_date).days == 1:
                player["login_streak"] += 1
            else:
                player["login_streak"] = 1
        else:
            player["login_streak"] = 1
        
        player["daily_bonus"] = 0
        player["last_login"] = datetime.now().isoformat()

@tasks.loop(minutes=30)
async def random_events():
    """Trigger random world events"""
    if random.random() < 0.3:  # 30% chance every 30 mins
        for guild in bot.guilds:
            if guild.id in silent_guilds:
                continue
            general_channel = discord.utils.get(guild.text_channels, name='general')
            if general_channel and general_channel.permissions_for(guild.me).send_messages:
                event_type = random.choice([
                    "treasure_found",
                    "pirate_attack",
                    "blessing",
                    "meteor_shower",
                    "bonus_hour",
                ])
                
                if event_type == "treasure_found":
                    embed = discord.Embed(
                        title="💎 TREASURE FOUND!",
                        description="A hidden treasure has been discovered! First person to claim it gets 5000 coins!",
                        color=discord.Color.gold()
                    )
                elif event_type == "pirate_attack":
                    embed = discord.Embed(
                        title="🏴‍☠️ PIRATE ATTACK!",
                        description="Pirates are attacking! Win a duel to defend your coins!",
                        color=discord.Color.red()
                    )
                elif event_type == "blessing":
                    embed = discord.Embed(
                        title="✨ BLESSING FROM THE GODS!",
                        description="The gods have blessed the server! Everyone gets 500 free coins!",
                        color=discord.Color.gold()
                    )
                elif event_type == "meteor_shower":
                    embed = discord.Embed(
                        title="☄️ METEOR SHOWER!",
                        description="Rare legendary fish are spawning! Quick, fish now for 10x rewards!",
                        color=discord.Color.purple()
                    )
                else:  # bonus_hour
                    embed = discord.Embed(
                        title="⚡ GOLDEN HOUR!",
                        description="All rewards are 3x for the next hour!",
                        color=discord.Color.gold()
                    )
                
                try:
                    await general_channel.send(embed=embed)
                except:
                    pass

# ===== COMMANDS =====

@bot.command(name='profile')
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

@bot.command(name='fish')
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
            title=f"🎣 Caught a {fish_type}!",
            description=f"You reeled in a **{fish_type}** {fish_info['emoji']}\n**+{value} Coins** | **+{xp} XP**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Catches", value=player["catches"])
        embed.add_field(name="Balance", value=f"🪙 {player['balance']}")
        embed.add_field(name="Level", value=f"Lvl {player['level']} ({player['xp']}/{player['xp_needed']} XP)")
    else:
        embed = discord.Embed(
            title="🎣 The Fish Got Away!",
            description="Better luck next time, explorer!",
            color=discord.Color.red()
        )
    
    embed.set_footer(text=f"Weather: {weather_status}")
    await ctx.send(embed=embed)

@bot.command(name='explore')
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

@bot.command(name='daily')
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
        await ctx.send("⏰ You already claimed your daily bonus! Come back tomorrow!")
        return
    
    # Base bonus + streak bonus
    base_bonus = 100
    streak_bonus = player["login_streak"] * 50
    total_bonus = base_bonus + streak_bonus
    
    player["balance"] += total_bonus
    player["daily_bonus"] = datetime.now().isoformat()
    
    embed = discord.Embed(
        title="✨ Daily Bonus Claimed!",
        description=f"**+{total_bonus} coins!**\nBase: {base_bonus} | Streak Bonus: {streak_bonus}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Login Streak", value=f"🔥 {player['login_streak']} days")
    embed.add_field(name="New Balance", value=f"🪙 {player['balance']}")
    await ctx.send(embed=embed)

@bot.command(name='duel')
async def duel(ctx, opponent: discord.Member):
    """Challenge someone to a duel!"""
    if opponent.bot:
        await ctx.send("❌ You can't duel a bot!")
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

@bot.command(name='blackjack')
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

@bot.command(name='slots')
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

@bot.command(name='coin_flip')
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

@bot.command(name='dice')
async def dice(ctx):
    """Roll the dice!"""
    player = get_player_data(ctx.author.id)
    roll = random.randint(1, 6)
    reward = roll * 25
    
    player["balance"] += reward
    player["stats"]["games_played"] += 1
    player["stats"]["games_won"] += 1
    
    await ctx.send(f"🎲 You rolled a **{roll}**! Won **{reward} coins**! Balance: **{player['balance']}**")

@bot.command(name='roulette')
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

@bot.command(name='quest')
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

@bot.command(name='pet')
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
            await ctx.send("❌ That pet doesn't exist! Use !pet shop to see available pets.")
            return
        
        pet_info = PETS[pet_name]
        if player["balance"] < pet_info["cost"]:
            await ctx.send(f"❌ You need {pet_info['cost']} coins! You have {player['balance']}.")
            return
        
        player["balance"] -= pet_info["cost"]
        player["pet"] = pet_name
        player["pet_level"] = 1
        
        await ctx.send(f"🎉 You adopted a {pet_info['name']}! It gives you a {int((pet_info['bonus']-1)*100)}% bonus!")
    
    elif action == "info":
        if not player["pet"]:
            await ctx.send("❌ You don't have a pet! Use !pet shop to adopt one.")
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

@bot.command(name='achievements')
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

@bot.command(name='title')
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
            await ctx.send("❌ That title doesn't exist!")
            return
        
        player["active_title"] = TITLES[title_name.lower()]
        await ctx.send(f"✨ Your new title: {player['active_title']}")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """View the leaderboard!"""
    if not player_data:
        await ctx.send("No one has started their adventure yet!")
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

@bot.command(name='inventory')
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

@bot.command(name='weather')
async def weather(ctx):
    """Check weather!"""
    embed = discord.Embed(title="🌊 Ocean Weather", description=f"Current Conditions: **{weather_status}**", color=discord.Color.blue())
    
    weather_descriptions = {
        "Calm": "Perfect conditions! 😊",
        "Stormy": "Dangerous waters! ⛈️",
        "Misty": "Mysteries hide in the fog... 🌫️",
        "Sunny": "Beautiful day! 🌞",
        "Foggy": "Low visibility! 🌫️",
        "Magical": "Mystical energy! ✨",
        "Cursed": "Dark forces! ☠️",
        "Blessed": "Divine power! 💫",
    }
    
    embed.add_field(name="Conditions", value=weather_descriptions.get(weather_status, "Unknown"))
    await ctx.send(embed=embed)

@bot.command(name='help_odyssey')
async def help_odyssey(ctx):
    """Full command guide!"""
    embed = discord.Embed(title="⛵ Odyssey Spirit Bot - Complete Guide", description="Everything you need to know!", color=discord.Color.blue())
    
    embed.add_field(name="🎮 CORE COMMANDS", value="""
    !fish - Catch fish
    !explore - Explore locations
    !duel [@player] - Duel someone
    !profile [@player] - View profile
    !daily - Claim daily bonus
    """, inline=False)
    
    embed.add_field(name="🎰 MINI-GAMES", value="""
    !blackjack - Play blackjack
    !slots - Spin slots
    !coin_flip - Flip a coin
    !dice - Roll dice
    !roulette - Spin roulette
    """, inline=False)
    
    embed.add_field(name="🎯 PROGRESSION", value="""
    !quest - View quests
    !achievements - View achievements
    !title - Set your title
    !pet - Manage pets
    """, inline=False)
    
    embed.add_field(name="📊 INFO", value="""
    !inventory - Check inventory
    !leaderboard - View rankings
    !weather - Check weather
    """, inline=False)
    
    await ctx.send(embed=embed)

# Run bot
bot.run('YOUR_BOT_TOKEN_HERE')
