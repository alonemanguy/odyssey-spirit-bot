"""Ask Aternos to start the SMP.

Aternos publishes no API, and their terms discourage automating the panel. This
module does the one thing a person does when a newcomer arrives: it opens
`/server/` with a signed-in session, reads the page's own AJAX token, and POSTs
to the same `/ajax/server/start` endpoint the Start button uses. Nothing else is
touched, and it refuses to ask more than once every COOLDOWN_SECONDS.

Credentials come from the environment and are never printed, logged or written
to the state file:

    ATERNOS_SESSION  the ATERNOS_SESSION cookie of a browser that is signed in
    ATERNOS_SERVER   the short server id from the panel URL

When the cookie expires the panel stops returning a token; `request_start()`
raises AternosError with a message the bot can show in the channel, rather than
failing silently.
"""

import json
import os
import re
import time

import aiohttp

PANEL = "https://aternos.org"

COOLDOWN_SECONDS = int(os.environ.get("ATERNOS_COOLDOWN_SECONDS", "300"))
TIMEOUT = aiohttp.ClientTimeout(total=20)

_TOKEN_RE = re.compile(r"var\s+AJAX_TOKEN\s*=\s*['\"]([^'\"]+)['\"]")
_SEC_RE = re.compile(r"var\s+SEC\s*=\s*['\"]([^'\"]+)['\"]")
_SERVER_RE = re.compile(r"var\s+SERVER\s*=\s*['\"]([^'\"]+)['\"]")

# Nothing in here is persisted: a restart simply means the next request is
# allowed again, which is what we want.
_last_request_at = 0.0


class AternosError(Exception):
    """A start attempt failed in a way worth telling a human about."""


def configured():
    """True when both halves of the credential pair are present."""
    return bool(os.environ.get("ATERNOS_SESSION")) and bool(os.environ.get("ATERNOS_SERVER"))


def seconds_until_allowed():
    """How long the cooldown still has to run."""
    return max(0, int(COOLDOWN_SECONDS - (time.monotonic() - _last_request_at)))


async def request_start():
    """Ask the panel to start the server.

    Returns {"started": bool, "already": bool, "message": str}. "already" covers
    the harmless cases - it is up, it is already starting, or we asked moments
    ago - so a caller can stay quiet about those.
    """
    global _last_request_at

    if not configured():
        raise AternosError("ATERNOS_SESSION and ATERNOS_SERVER are not set")

    waiting = seconds_until_allowed()
    if waiting:
        return {"started": False, "already": True,
                "message": f"asked {COOLDOWN_SECONDS - waiting}s ago"}

    cookies = {
        "ATERNOS_SESSION": os.environ["ATERNOS_SESSION"],
        "ATERNOS_SERVER": os.environ["ATERNOS_SERVER"],
    }
    _last_request_at = time.monotonic()

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT, cookies=cookies) as http:
            async with http.get(f"{PANEL}/server/") as response:
                if response.status != 200:
                    raise AternosError(
                        f"the panel answered {response.status} - the session cookie "
                        "has probably expired")
                page = await response.text()

            token = _TOKEN_RE.search(page)
            sec = _SEC_RE.search(page)
            if not token or not sec:
                raise AternosError(
                    "the panel did not return a start token - sign in again and copy "
                    "a fresh ATERNOS_SESSION")
            server_id = _SERVER_RE.search(page)
            params = {
                "TOKEN": token.group(1),
                "SEC": sec.group(1),
                "SERVER": server_id.group(1) if server_id else os.environ["ATERNOS_SERVER"],
            }

            async with http.post(f"{PANEL}/ajax/server/start", params=params) as response:
                body = await response.text()
    except aiohttp.ClientError as exc:
        raise AternosError(f"could not reach aternos.org ({type(exc).__name__})") from exc

    try:
        payload = json.loads(body)
    except ValueError:
        raise AternosError("the panel answered something that is not JSON") from None

    message = str(payload.get("message") or "")
    if payload.get("success"):
        return {"started": True, "already": False, "message": message}

    # Aternos says "Server is already online", "Already starting", "Queued" and
    # friends with success=false. None of those is a failure worth reporting.
    lowered = message.lower()
    if any(word in lowered for word in ("already", "online", "starting", "queue", "starting")):
        return {"started": False, "already": True, "message": message}

    raise AternosError(message or "the panel refused the start")
