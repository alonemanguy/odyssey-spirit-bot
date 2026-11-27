"""Content tables for Tidewarden.

Pure data, split out of odyssey_bot.py so the bot file stays readable. Nothing
in here imports discord or touches the network.
"""

WEEKLY_PROMPTS = [
    "What's the one build you keep promising yourself you'll finish? Screenshot it, finished or not.",
    "Drop the coordinates of your base. First person to visit gets bragging rights.",
    "What's the dumbest way you've died on the SMP?",
    "If Odyssey Lands got one new biome tomorrow, what would you add?",
    "Post your inventory. No sorting it first, no cheating.",
    "Who's your favourite person to team up with here, and why?",
    "What's one small thing the server could add that would make you play more?",
    "Post the oldest screenshot you still have from this server.",
    "What are you hoarding way too much of right now?",
    "Build night idea: what should we build together next?",
    "What's the best thing you've ever found in a chest someone else left?",
    "Rate spawn out of 10 and say what you'd change about it.",
]

# ===== THE WEEK, SAID TWICE =====
# Two standing evenings, both at 20:00 UTC+3, both posted by the routines loop.
# Plain text, no embed: an embed cannot ping, and these are the messages that
# should. The hour is deliberately the same on both days, so the habit is one
# sentence and the bot only has one time to get right.
SESSIONS = {
    2: {  # Wednesday - the session
        "nudge": (
            "⏰ **Session in an hour.** Java `odysseyland.aternos.me:56870` · Bedrock same "
            "address, port `19132`. Hop in voice even if you're not playing yet."
        ),
        "tonight": (
            "*Session tonight, 8pm UTC+3 - Java `odysseyland.aternos.me:56870`, "
            "Bedrock port `19132`.*"
        ),
    },
    6: {  # Sunday - build night
        "nudge": (
            "⏰ **Build night in an hour.** Java `odysseyland.aternos.me:56870` · Bedrock "
            "same address, port `19132`. Bring what you're working on, or come and "
            "look at everyone else's."
        ),
        "tonight": (
            "*Build night tonight, 8pm UTC+3 - same address, Bedrock port `19132`.*"
        ),
    },
}

# ===== VOTING =====
# Only the two vote pages whose URL is derivable from the guild id are listed,
# because a dead link is worse than a short list. Both are /vote command links.
VOTE_SITES = [
    ("DISBOARD", "https://disboard.org/server/1345963951724171364",
     "then `/bump` in #📣-bump"),
    ("top.gg", "https://top.gg/servers/1345963951724171364/vote", ""),
]

# ===== SELF-SERVE ROLE MENUS =====
# ~38 assignable roles is far past the 25-option and 25-button limits, so the
# menus are grouped by what a role is actually for. Every option is a role ID
# that already exists in the guild.
ROLE_MENUS = [
    ("pings", "🔔 Pings — what should be able to ping you?", 3, [
        (1472609658253607012, "📢 Event Pings", "Build nights, expeditions, movie nights"),
        (1472612132590981342, "🛒 Trading Pings", "Shop restocks and trade posts"),
        (1472612403039568041, "🎁 Giveaway Pings", "Giveaways only"),
        (1472612628634533939, "🎤 VC Enjoyer", "Someone hops into voice chat"),
    ]),
    ("platform", "🎮 Platform — how do you play?", 2, [
        (1472608072831860893, "💻 Java Player", "PC / Java Edition"),
        (1472607813489393674, "📱 Bedrock Player", "Phone, console or Windows Bedrock"),
    ]),
    ("playstyle", "⛏️ Playstyle — what do you actually do in-world?", 3, [
        (1472605904066183198, "🧱 Builder", "Big builds, detail work, terraforming"),
        (1472606131888066561, "⚔️ PvP Enjoyer", "Duels, arenas, a little chaos"),
        (1472606560059392000, "🔴 Redstone Nerd", "Farms, doors, machines"),
        (1472606757628022888, "🧭 Explorer", "Maps, loot, bases far from spawn"),
        (1472607349389656260, "💰 Trader", "Shops, villager halls, haggling"),
        (1472607579292303456, "🎭 Roleplayer", "Lore, characters, story arcs"),
    ]),
    ("vibe", "🌊 Vibe — pick the labels you like", 5, [
        (1472612863460905158, "🌙 Night Owl", "You play when everyone else sleeps"),
        (1472613213236363307, "🌞 Day Grinder", "Online while the sun is up"),
        (1472613387186737264, "🧪 Chaos Gremlin", "It was already on fire when you got there"),
        (1473656027349258302, "😇 Saint", "Never broke a rule, never will"),
        (1473656213584744549, "🐍 Snake", "Trusted by everyone, deserved by nobody"),
        (1473656379310084109, "🕊️ Pacifist", "Would rather build than fight"),
        (1473656598835494962, "🤝 Diplomat", "Settles the argument before it starts"),
        (1473656930521317439, "😈 Villain Arc", "It's not griefing, it's story"),
        (1473657111459139694, "💡 Mastermind", "Has a plan. Always has a plan"),
        (1473657286219268299, "🎲 Wing It King", "No plan, somehow it works"),
        (1473657568466436268, "🤯 Galaxy Brain", "Overthinks every redstone circuit"),
        (1473657735714177115, "🏚️ Dirt Mansion Resident", "It's a starter base, we promise"),
        (1473657984033886380, "🏰 Overachiever", "Your base has a base"),
        (1473658143400792139, "🌿 Cottagecore", "Flowers, lanterns, bees"),
        (1473658400146718831, "🕳️ Cave Dweller", "Has not seen the sun in weeks"),
        (1473658628551606302, "📦 Box Architect", "Square, functional, done"),
        (1473659232128864449, "📻 Ghost", "Says nothing, is always online"),
        (1473659434352906292, "💬 Yapper", "Types faster than you can read"),
        (1473659600916971664, "🔔 Lurker", "Reads everything, replies to nothing"),
        (1473659764440301608, "🎙️ Instigator", "Starts the bit, watches it land"),
    ]),
]


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
