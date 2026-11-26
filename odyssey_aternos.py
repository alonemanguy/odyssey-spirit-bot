"""Ask Aternos to start the SMP.

Aternos publishes no API, and their terms discourage automating the panel. This
module does the one thing a person does when a newcomer arrives: it opens
`/server/` with a signed-in session, reads the page's own AJAX token, and POSTs
to the same `/ajax/server/start` endpoint the Start button uses. Nothing else is
touched, and it refuses to ask more than once every COOLDOWN_SECONDS.

Plain HTTP clients are turned away before the cookie is ever read: aternos.org
sits behind Cloudflare, which answers 403 "Just a moment..." to anything whose
TLS fingerprint is not a browser's - aiohttp included, and a spoofed User-Agent
does not change it. So the two calls go through curl_cffi with Chrome's
fingerprint, which Cloudflare accepted from this project's own machine where a
plain client was blocked. The fingerprint is only half of it - Cloudflare also
weighs the IP, and GitHub's runner addresses are still challenged, which is the
one wall this module cannot climb from Actions. It cannot, however, make an
expired session valid: with a dead cookie the panel simply lands on its login
page, which is what the redirect check below reports.

Credentials come from the environment and are never printed, logged or written
to the state file:

    ATERNOS_SESSION  the ATERNOS_SESSION cookie of a browser that is signed in
    ATERNOS_SERVER   the short server id from the panel URL

When the cookie expires, `request_start()` raises AternosError with a message
the bot can show in the channel, rather than failing silently.
"""

import json
import os
import re
import time

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError

PANEL = "https://aternos.org"

COOLDOWN_SECONDS = int(os.environ.get("ATERNOS_COOLDOWN_SECONDS", "300"))
TIMEOUT = 20
IMPERSONATE = "chrome"

_TOKEN_RE = re.compile(r"var\s+AJAX_TOKEN\s*=\s*['\"]([^'\"]+)['\"]")
_SEC_RE = re.compile(r"var\s+SEC\s*=\s*['\"]([^'\"]+)['\"]")
_SERVER_RE = re.compile(r"var\s+SERVER\s*=\s*['\"]([^'\"]+)['\"]")

# Only a Cloudflare interstitial carries these, so finding one means the request
# never reached the panel.
_INTERSTITIAL = ("just a moment", "cf_chl", "cf-browser-verification",
                 "challenge-platform", "attention required", "cf-error-details")

# Nothing in here is persisted: a restart simply means the next request is
# allowed again, which is what we want. None means "has not asked yet":
# monotonic() starts near zero on a fresh runner, so 0.0 reads as "asked a
# moment ago" and the very first wake is silently skipped.
_last_request_at = None


class AternosError(Exception):
    """A start attempt failed in a way worth telling a human about."""


def _cookie_value(raw):
    """Accept the cookie however it was pasted: quoted, as `name=value`, or bare."""
    value = (raw or "").strip().strip('"').strip("'")
    if value.lower().startswith("aternos_session="):
        value = value.split("=", 1)[1]
    return value.strip()


def configured():
    """True when both halves of the credential pair are present."""
    return bool(_cookie_value(os.environ.get("ATERNOS_SESSION"))) \
        and bool(os.environ.get("ATERNOS_SERVER"))


def seconds_until_allowed():
    """How long the cooldown still has to run."""
    if _last_request_at is None:
        return 0
    return max(0, int(COOLDOWN_SECONDS - (time.monotonic() - _last_request_at)))


def _is_login_page(response):
    """A dead cookie does not 403 - it quietly lands on /go/ instead."""
    url = str(getattr(response, "url", "") or "")
    return url.rstrip("/").endswith("/go")


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
        "ATERNOS_SESSION": _cookie_value(os.environ["ATERNOS_SESSION"]),
        "ATERNOS_SERVER": os.environ["ATERNOS_SERVER"],
    }
    _last_request_at = time.monotonic()

    try:
        async with AsyncSession(impersonate=IMPERSONATE, timeout=TIMEOUT) as http:
            response = await http.get(f"{PANEL}/server/", cookies=cookies)
            page = response.text or ""

            if _is_login_page(response):
                raise AternosError(
                    "Aternos sent us to its login page - the session cookie has "
                    "expired, sign in again and save a fresh ATERNOS_SESSION")
            if response.status_code != 200:
                blocked = any(marker in page.lower() for marker in _INTERSTITIAL)
                if blocked:
                    raise AternosError(
                        "the panel turned the request away before the server "
                        "heard it")
                raise AternosError(
                    f"the panel answered {response.status_code} - the session "
                    "cookie has probably expired")

            token = _TOKEN_RE.search(page)
            sec = _SEC_RE.search(page)
            if not token or not sec:
                raise AternosError(
                    "the panel did not return a start token - sign in again and "
                    "copy a fresh ATERNOS_SESSION")
            server_id = _SERVER_RE.search(page)
            params = {
                "TOKEN": token.group(1),
                "SEC": sec.group(1),
                "SERVER": server_id.group(1) if server_id else os.environ["ATERNOS_SERVER"],
            }

            started = await http.post(
                f"{PANEL}/ajax/server/start",
                params=params,
                cookies=cookies,
                headers={"Referer": f"{PANEL}/server/"},
            )
            body = started.text or ""
    except RequestsError as exc:
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
    if any(word in lowered for word in ("already", "online", "starting", "queue")):
        return {"started": False, "already": True, "message": message}

    raise AternosError(message or "the panel refused the start")
