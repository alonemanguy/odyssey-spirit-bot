# odyssey-spirit-bot

Tidewarden, the bot for the Odyssey Lands Discord: fishing, exploring, quests,
levels, pets, self-serve roles, and a status check for the SMP.

All 18 commands are hybrid, so `/fish` and `!fish` both work.

- **Command guide:** [COMMANDS.md](COMMANDS.md) — also available in Discord as `/guide`.
- **Running it:** `pip install -r requirements.txt`, set `DISCORD_TOKEN`, then
  `python odyssey_bot.py`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DISCORD_TOKEN` | — | Required. |
| `RUN_BUDGET_MINUTES` | `285` | How long the process may run before it saves and stops itself. |
| `ODYSSEY_STATE_FILE` | `state/odyssey_state.json` | Where profiles are saved. |
| `ROUTINE_CHANNEL_ID` | `#event-announcements` | Channel for the daily question and the Wednesday nudge. Never `#general`. |
| `SERVER_JAVA_HOST` / `SERVER_JAVA_PORT` | `odysseyland.aternos.me` / `25565` | Used by `/start` and `/server`. |
| `SERVER_BEDROCK_HOST` / `SERVER_BEDROCK_PORT` | `odysseyland.aternos.me` / `19132` | Shown for Bedrock players. |
| `SERVER_PANEL_URL` | `https://aternos.org/go/` | Link in `/start`. |
| `ATERNOS_SESSION` | — | Cookie from a signed-in browser. Presses Start when a newcomer arrives. Unset = that feature stays quiet. |
| `ATERNOS_SERVER` | — | The short server id from the panel URL. Pair with the cookie. |
| `ATERNOS_COOLDOWN_SECONDS` | `300` | Minimum gap between start requests. |
| `BOOT_NOTICE_CHANNEL_ID` | `#event-announcements` | Where "bringing the server up" is posted. |
| `NEWCOMER_POLL_MINUTES` | `2` | How often to look for a rising member count or a spent invite. |
| `ENABLE_MEMBER_INTENT` | unset | Set `1` **only after** enabling the Server Members intent in the Discord developer portal. Gets exact joins and invite attribution; the poll above covers it without. |

## Routines

The bot keeps the server's rhythm itself, so nobody has to remember it:

- **One question a day**, at 18:00 UTC+3, always the same hour. The questions
  rotate by day of the year through `WEEKLY_PROMPTS` in `odyssey_data.py`.
- **A nudge an hour before each standing evening**, at 19:00 UTC+3, with the
  address in it: Wednesday is the session, Sunday is build night. On those days
  the daily question carries a "tonight" line, so the day produces one
  notification rather than two. Which days, and both wordings, live in `SESSIONS`
  in `odyssey_data.py`.

Both are posted in `ROUTINE_CHANNEL_ID` (`#event-announcements`), because the
bot is denied Send Messages in `#general` on purpose. Each post is date-guarded
in `state_meta`, so the 30-minute tick cannot repeat one - but the guard lives
in the state file, so on an Actions runner a *second* run in the same hour could
post the question twice. It doesn't happen with the 5-hour schedule; it would
with a 30-minute one.

## Server wake and first-join

- `odyssey_aternos.py` presses the panel's own Start button (no API exists) when
  somebody new arrives, and `#event-announcements` gets a "give it a minute"
  line. `/wake` does the same on demand, with a five-minute cooldown.
- Arrivals are detected by polling `member_count` and the invite use counts, so
  the privileged members intent is optional. `odyssey_growth.py` turns the same
  invite diff into `/recruits`.
- `welcome-pack/` is the first-join datapack: title, starter kit, and the three
  lines a newcomer needs. Install instructions are in that folder.

## Scheduling note

The workflow runs the bot on a GitHub Actions runner every 5 hours with a
285-minute budget, which keeps one process inside one schedule slot. The state
file on a runner is per-run, so **coins reset each run until the bot is hosted
somewhere always-on** — set `ODYSSEY_STATE_FILE` to a persistent path there and
the same code keeps everything.
