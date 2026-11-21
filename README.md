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
| `PROMPT_CHANNEL_ID` | `#general` | Channel for the weekly prompt. |
| `SERVER_JAVA_HOST` / `SERVER_JAVA_PORT` | `odysseyland.aternos.me` / `25565` | Used by `/start` and `/server`. |
| `SERVER_BEDROCK_HOST` / `SERVER_BEDROCK_PORT` | `odysseyland.aternos.me` / `19132` | Shown for Bedrock players. |
| `SERVER_PANEL_URL` | `https://aternos.org/go/` | Link in `/start`. |

## Scheduling note

The workflow runs the bot on a GitHub Actions runner every 5 hours with a
285-minute budget, which keeps one process inside one schedule slot. The state
file on a runner is per-run, so **coins reset each run until the bot is hosted
somewhere always-on** — set `ODYSSEY_STATE_FILE` to a persistent path there and
the same code keeps everything.
