# Tidewarden — command guide

Every command works two ways: **slash** (`/fish`) or **prefix** (`!fish`). Slash is
easier — type `/` in Discord and the list appears with descriptions.

If a command does nothing, it usually means the bot process is between GitHub
Actions runs (it runs ~4h45m out of every 5h) or that its slash commands were
never synced. A restart syncs them automatically.

## SMP / server

| Command | What it does |
| --- | --- |
| `/start` | Checks whether the SMP is online. If it is, gives the join addresses. If not, explains the two ways to start it (Aternos panel or the Dawn launcher) and how share access works. |
| `/server` | Addresses, ports and live status in one card. |
| `/wake` | Asks Aternos to start the SMP right now (five-minute cooldown), for when nobody wants to open the panel. |
| `/roles` | Staff only. Posts the four self-serve role menus. Re-running posts a fresh copy. |
| `/guide` | This guide, in Discord. |

`/wake` presses the panel's own Start button using a signed-in session cookie
kept in the bot's secrets, and it retries nothing on failure — if Aternos answers
with an error, the channel says so and a human presses Start. **Anyone with
share access** can do that, not just staff.

## Core

| Command | What it does |
| --- | --- |
| `/fish` | Catch a fish. Rarity roll, pet bonus, XP and coins. |
| `/explore` | Visit one of ten ocean locations for coins and XP. |
| `/daily` | Daily coins; the streak multiplier grows each consecutive day. |
| `/duel @player` | Level-weighted duel for coins and XP. |
| `/profile [@player]` | Level, balance, catches, pet, streak, lifetime stats. |

## Mini-games

`/blackjack` · `/slots` · `/coin_flip` · `/dice` · `/roulette`

## Progression

| Command | What it does |
| --- | --- |
| `/quest` | Your three active quests and their progress. |
| `/achievements [@player]` | Everything unlocked and everything still locked. |
| `/title [name]` | Sets the title shown on your profile. `/title` alone lists them. |
| `/pet` | `/pet shop` lists pets, `/pet adopt <name>` buys one, `/pet info` shows yours. |

## Info

`/inventory [@player]` · `/leaderboard` · `/weather`

## What changed (phase 1)

- Commands are **hybrid**: the same 18 commands answer both `/slash` and `!prefix`.
  Slash commands are synced on startup, so they actually exist now — before, the
  bot registered none and every command depended on a privileged intent.
- The chatty `on_message` responder is gone (random replies, random reactions,
  keyword triggers, silence triggers). Tidewarden answers when asked.
- Ocean events in `#event-announcements` are flavour only. They no longer promise
  coin drops or 3x/10x windows that no command implemented.
- Profiles (coins, levels, inventory, pets, streaks, met titles) are saved to disk
  and reloaded on boot instead of vanishing on every restart.
- The 24-hour streak loop that could never fire inside a 5-hour process was
  replaced by a lazy streak check on every command.
- One weekly conversation prompt in `#general`, Saturdays at 17:00 UTC.
- The run budget is 285 minutes and the workflow stops at 300, so two copies of
  the bot can no longer overlap and answer the same command twice.
