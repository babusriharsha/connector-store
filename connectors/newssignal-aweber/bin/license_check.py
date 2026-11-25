#!/usr/bin/env python3
"""License check for the AWeber connector (Plugvana, CALL SNAP SYSTEMS LLC).

How licensing works
-------------------
- The connector runs a 30-day free trial from its first activation (the first
  live command ever run on this install). Trial state is kept locally in
  ``license_state.json`` beside this package. Nothing about the user's
  AWeber account is ever read or stored here.
- A paid license key activates the connector past the trial. The key is read,
  in order, from:
    1. the ``AWEBER_CONNECTOR_LICENSE_KEY`` environment variable,
    2. a ``license.json`` file beside this package: {"license_key": "..."},
    3. the Muse connection entry ``license_key`` on ``custom.newssignal-aweber``
       (a surrogate is fetched through Muse's dynamic-credential flow; the
       real key is swapped in only on the request to the validation host,
       which the installing Muse must register for that connection).
- Validation is a single POST to the license server's /v1/check endpoint
  (below). Results are cached locally for 24 hours. If the endpoint cannot
  be reached, a 7-day offline grace applies from the last successful check
  (or from activation when no check has succeeded yet).
- On the first live run this module also POSTs /v1/activate with
  {product, install_id, shop_hash, version} and adopts the server's
  trial_start as the authoritative trial start (activation is idempotent
  per account server-side, so a trial cannot be restarted for the same
  account). install_id is a random uuid4 persisted in the local state
  file (this module has always kept one). shop_hash is a one-way SHA-256
  of the AWeber account id, computed locally -- the raw account id is
  never sent; when the account id is not known yet at check time,
  shop_hash is sent empty rather than blocking the command. If the
  license server is unreachable, the local trial / grace rules below
  govern and activation is retried on a later run.
- After the trial with no valid license, live commands stop with a polite
  refusal and a subscribe message. Demo mode (--demo) never checks a
  license and never touches the network.

Zero-cost note: this runs entirely on the customer's own Muse. The store
stores nothing about the customer; the only network calls are the license
activation/validation POSTs above.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

# TODO(store-owner): replace this placeholder base URL with the production
# license service URL before distributing the connector (deploy time).
# Both endpoint URLs are built from this one base constant. Until then,
# remote calls fail as "unreachable" and the trial / offline-grace rules
# below govern. NOTE (deploy time): the host of LICENSE_API_BASE must be
# registered in the custom.newssignal-aweber connection, or Muse will refuse
# the outbound license requests and never swap in the real license_key
# on egress.
LICENSE_API_BASE = os.environ.get(
    "AWEBER_LICENSE_API_BASE", "https://plugvana-licenses.vercel.app"
)
VALIDATION_ENDPOINT = os.environ.get(
    "AWEBER_LICENSE_ENDPOINT", LICENSE_API_BASE.rstrip("/") + "/v1/check"
)


def _activate_url() -> str:
    return LICENSE_API_BASE.rstrip("/") + "/v1/activate"


PRODUCT = "newssignal-aweber"
CONNECTOR_VERSION = "1.0.0"
TRIAL_DAYS = 30
CACHE_HOURS = 24
GRACE_DAYS = 7
# Monthly plan checkout (Stripe Payment Link). Annual plans are not offered yet.
SUBSCRIBE_URL = "https://buy.stripe.com/eVqcN57Hb8TGdye8gS4AU0A"
BOUND_ELSEWHERE_MESSAGE = (
    "This license key is already bound to a different AWeber "
    "account. A license covers one account, so it cannot be used for "
    "this account. Subscribe for this account at Plugvana "
    "by CALL SNAP SYSTEMS LLC, or contact support if you believe this "
    "is a mistake."
)

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PKG_DIR, "license_state.json")
LICENSE_FILE = os.path.join(PKG_DIR, "license.json")
CONNECTION_NAME = "custom.newssignal-aweber"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
    except OSError:
        pass  # a read-only install still gets trial behaviour from memory


def shop_hash_for(account_id) -> str:
    """One-way SHA-256 of the AWeber account id ("" when unknown).

    The raw account id never leaves this machine -- only this hash is
    sent to the license server.
    """
    if not account_id:
        return ""
    return hashlib.sha256(str(account_id).strip().encode("utf-8")).hexdigest()


def _post_json(url: str, payload: dict, timeout: int = 15) -> dict | None:
    """POST JSON and return the parsed body, or None on any failure."""
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body if isinstance(body, dict) else None
    except Exception:
        return None


def _ensure_activation(state: dict, shop_hash: str) -> None:
    """POST /v1/activate once, on the first live run.

    Adopts the server's trial_start as the local first_activation. If
    the server is unreachable, local trial rules govern and we retry
    on a later run (throttled to one attempt per CACHE_HOURS) -- a
    license-server outage must never crash or block a command.
    """
    if state.get("activation"):
        return
    last_attempt = _parse(state.get("activation_last_attempt_at"))
    if last_attempt and _now() - last_attempt < timedelta(hours=CACHE_HOURS):
        return
    state["activation_last_attempt_at"] = _now().isoformat()
    _save_state(state)
    body = _post_json(_activate_url(), {
        "product": PRODUCT,
        "install_id": state["install_id"],
        "shop_hash": shop_hash,
        "version": CONNECTOR_VERSION,
    })
    if body and body.get("trial_start"):
        state["activation"] = {
            "trial_start": body["trial_start"],
            "trial_days_left": body.get("trial_days_left"),
            "status": body.get("status"),
            "at": _now().isoformat(),
        }
        try:
            start = datetime.fromisoformat(str(body["trial_start"])[:10])
            state["first_activation"] = start.replace(
                tzinfo=timezone.utc
            ).isoformat()
        except ValueError:
            pass
        _save_state(state)


def get_license_key():
    """Return the license key from env, license.json, or the Muse connection."""
    env_key = os.environ.get("AWEBER_CONNECTOR_LICENSE_KEY", "").strip()
    if env_key:
        return env_key
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as fh:
            key = str(json.load(fh).get("license_key", "")).strip()
        if key:
            return key
    except (OSError, json.JSONDecodeError):
        pass
    # Last resort: the license_key entry on the custom.newssignal-aweber connection.
    # This returns an hsurr: surrogate, never the real key; it only becomes
    # the real key if the validation host is registered for that connection.
    try:
        sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
        from dynamic_credentials import dynamic_credential_entry

        entry = dynamic_credential_entry(CONNECTION_NAME, "license_key")
        surrogate = str(entry.get("surrogate", "")).strip()
        if surrogate:
            return surrogate
    except Exception:
        pass
    return None


def _validate_online(key: str, install_id: str, shop_hash: str = "") -> dict:
    """POST the key to the validation endpoint. Raises on network failure.

    The payload carries install_id and shop_hash (when known) so the
    server can apply its one-account binding and trial records.
    """
    body = json.dumps(
        {"license_key": key, "product": PRODUCT, "install_id": install_id,
         "shop_hash": shop_hash}
    ).encode("utf-8")
    request = urllib.request.Request(
        VALIDATION_ENDPOINT, data=body, method="POST"
    )
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def check(demo: bool = False, shop_identity=None) -> dict:
    """Return the license status dict. Never raises for licensing reasons.

    ``shop_identity`` is the AWeber account id when the caller
    already knows it (the status command does, from its account call);
    it is hashed locally and only the hash is ever sent.
    """
    if demo:
        return {"status": "demo", "active": True,
                "message": "Demo mode. No license check."}

    state = _load_state()
    now = _now()
    if not state.get("install_id"):
        state["install_id"] = str(uuid.uuid4())
    if not state.get("first_activation"):
        state["first_activation"] = now.isoformat()
        _save_state(state)
    shop_hash = shop_hash_for(shop_identity)
    # First live run: register the trial with the license server and
    # adopt its trial_start (may rewrite first_activation above).
    _ensure_activation(state, shop_hash)
    first_activation = _parse(state.get("first_activation")) or now
    trial_ends = first_activation + timedelta(days=TRIAL_DAYS)
    trial_days_left = max(0, (trial_ends - now).days)

    key = get_license_key()
    last_check = _parse(state.get("last_check_at"))
    last_ok = bool(state.get("last_check_valid"))

    if key:
        cache_fresh = (
            last_check is not None
            and last_ok
            and now - last_check < timedelta(hours=CACHE_HOURS)
        )
        if cache_fresh:
            return {"status": "licensed", "active": True,
                    "message": "License valid (cached check).",
                    "checked_at": state.get("last_check_at")}
        try:
            result = _validate_online(key, state["install_id"], shop_hash)
            valid = bool(result.get("valid"))
            state["last_check_at"] = now.isoformat()
            state["last_check_valid"] = valid
            state["last_check_reason"] = result.get("reason")
            _save_state(state)
            if valid:
                return {"status": "licensed", "active": True,
                        "message": "License valid.",
                        "plan": result.get("plan"),
                        "checked_at": state["last_check_at"]}
            if result.get("reason") == "bound_elsewhere":
                # The key belongs to a different account. Say exactly
                # that -- not a generic "key not accepted".
                return {"status": "bound_elsewhere", "active": False,
                        "reason": "bound_elsewhere",
                        "message": BOUND_ELSEWHERE_MESSAGE}
            return {"status": "invalid", "active": False,
                    "message": "That license key was not accepted. "
                               f"Subscribe or check your key: {SUBSCRIBE_URL}"}
        except (urllib.error.URLError, OSError, ValueError):
            # Offline. Grace runs from the last successful check, or from
            # activation when no check has ever succeeded.
            anchor = last_check if (last_check and last_ok) else first_activation
            if now - anchor < timedelta(days=GRACE_DAYS):
                return {"status": "grace", "active": True,
                        "message": "License server unreachable. Running on "
                                   "offline grace."}
            if now < trial_ends:
                return {"status": "trial", "active": True,
                        "trial_days_left": trial_days_left,
                        "message": "License server unreachable. Free trial "
                                   "still active."}
            return {"status": "expired", "active": False,
                    "message": "License server unreachable and the free "
                               "trial has ended. Reconnect to the internet "
                               f"or subscribe for $15/month: {SUBSCRIBE_URL}"}

    if now < trial_ends:
        return {"status": "trial", "active": True,
                "trial_days_left": trial_days_left,
                "trial_ends": trial_ends.date().isoformat(),
                "message": f"Free trial: {trial_days_left} day(s) left. "
                           f"Subscribe any time: {SUBSCRIBE_URL}"}
    return {"status": "expired", "active": False,
            "trial_ends": trial_ends.date().isoformat(),
            "message": "Your 30-day free trial of the AWeber connector "
                       "has ended. Thank you for trying it. To keep using "
                       f"it, subscribe for $15/month here: {SUBSCRIBE_URL}"}


def ensure_active(demo: bool = False, shop_identity=None) -> dict:
    """Return the status dict when active. Print a refusal and exit(3) if not."""
    status = check(demo=demo, shop_identity=shop_identity)
    if not status.get("active"):
        print(json.dumps({
            "error": "license_inactive",
            "license": status,
            "message": status.get("message", "The connector license is not active."),
        }, indent=2))
        raise SystemExit(3)
    return status


if __name__ == "__main__":
    demo_mode = "--demo" in sys.argv
    print(json.dumps(check(demo=demo_mode), indent=2))


def enforce(shop_identity=None) -> dict:
    """Skeleton-compatible alias for ensure_active."""
    return ensure_active(demo=False, shop_identity=shop_identity)
