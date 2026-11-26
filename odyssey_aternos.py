"""Ask Aternos to start the SMP.

Aternos publishes no API, and their terms discourage automating the panel. This
module does the one thing a person does when a newcomer arrives: it opens
`/server/` with a signed-in session and POSTs to the same `/ajax/server/start`
endpoint the Start button uses. Nothing else is touched, and it refuses to ask
more than once every COOLDOWN_SECONDS.

Two things about the panel are worth knowing before reading the request:

* Plain HTTP clients are turned away before the cookie is ever read: aternos.org
  sits behind Cloudflare, which answers 403 "Just a moment..." to anything whose
  TLS fingerprint is not a browser's - aiohttp included, and a spoofed
  User-Agent does not change it. So both calls go through curl_cffi with
  Chrome's fingerprint. The fingerprint is only half of it - Cloudflare also
  weighs the IP, and GitHub's runner addresses are still challenged, which is
  the one wall this module cannot climb from Actions.
* The panel used to print `var AJAX_TOKEN = "..."` in the page. It no longer
  does: the page's inline script picks one of two constant tokens depending on
  whether the browser looks real, and `SEC` is a `key:value` pair the page
  invents and mirrors into an `ATERNOS_SEC_<key>` cookie. Both tokens are
  accepted, so this module uses the same pair and its own cookie rather than
  scraping anything. A dead cookie still cannot be faked: the panel quietly
  lands on its login page, which is what `_is_login_page` reports.

Credentials come from the environment and are never printed, logged or written
to the state file:

    ATERNOS_SESSION  the ATERNOS_SESSION cookie of a browser that is signed in
    ATERNOS_SERVER   the short server id from the panel URL

When the cookie expires, `request_start()` raises AternosError with a message
the bot can show in the channel, rather than failing silently.
"""

import json
import os
import secrets
import string
import time

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError

PANEL = "https://aternos.org"

COOLDOWN_SECONDS = int(os.environ.get("ATERNOS_COOLDOWN_SECONDS", "300"))
TIMEOUT = 20
IMPERSONATE = "chrome"

# The two token strings the panel's inline script chooses between, in the order
# it writes them. Either is accepted by /ajax/server/start.
_AJAX_TOKENS = ("HP2qIWSGp2d2pEp4f3L2", "qRyqjWrArgfE4L1y7QtX")
_SEC_ALPHABET = string.ascii_letters + string.digits
_SEC_LENGTH = 16

# Only a Cloudflare interstitial carries these, so finding one means the request
# never reached the panel.
_INTERSTITIAL = ("just a moment", "cf_chl", "cf-browser-verification",
                 "challenge-platform", "attention required", "cf-error-details")

# States the panel reports through data.status. None of them is a failure.
_ALREADY = ("already", "online", "starting", "queue", "queued", "stopping")

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


def _sec_pair():
    """The panel's own CSRF pair: a cookie key and the value sent back in SEC."""
    key = "".join(secrets.choice(_SEC_ALPHABET) for _ in range(_SEC_LENGTH))
    value = "".join(secrets.choice(_SEC_ALPHABET) for _ in range(_SEC_LENGTH))
    return key, value


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

    server_id = os.environ["ATERNOS_SERVER"]
    key, value = _sec_pair()
    cookies = {
        "ATERNOS_SESSION": _cookie_value(os.environ["ATERNOS_SESSION"]),
        "ATERNOS_SERVER": server_id,
        f"ATERNOS_SEC_{key}": value,
    }
    params = {"TOKEN": _AJAX_TOKENS[0], "SEC": f"{key}:{value}", "SERVER": server_id}
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

            started = await http.post(
                f"{PANEL}/ajax/server/start",
                params=params,
                cookies=cookies,
                headers={"Content-Type": "application/json",
                         "Referer": f"{PANEL}/server/"},
                data="{}",
            )
            body = started.text or ""
    except RequestsError as exc:
        raise AternosError(f"could not reach aternos.org ({type(exc).__name__})") from exc

    try:
        payload = json.loads(body)
    except ValueError:
        raise AternosError("the panel answered something that is not JSON") from None

    data = payload.get("data") or {}
    status = str(data.get("status") or "").lower()
    # The panel's own "error" field is the unhelpful "Sorry, an error occured!"
    # even when data.status says the server is simply already up, so status wins.
    message = str(data.get("message") or "")
    error = str(payload.get("error") or "")

    if payload.get("success") and status not in _ALREADY:
        return {"started": True, "already": False, "message": message}
    if status in _ALREADY or any(word in message.lower() for word in _ALREADY):
        return {"started": False, "already": True, "message": message or status}
    if status or error:
        raise AternosError(message or error or f"the panel answered status {status}")
    raise AternosError("the panel refused the start")
