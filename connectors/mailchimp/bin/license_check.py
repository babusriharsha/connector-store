#!/usr/bin/env python3
"""License check for the Mailchimp connector (Connector Store, CALL SNAP SYSTEMS LLC).

How licensing works
-------------------
- The connector runs a 30-day free trial from its first activation (the first
  live command ever run on this install). Trial state is kept locally in
  ``license_state.json`` beside this package. Nothing about the user's
  Mailchimp account is ever read or stored here.
- A paid license key activates the connector past the trial. The key is read,
  in order, from:
    1. the ``MAILCHIMP_CONNECTOR_LICENSE_KEY`` environment variable,
    2. a ``license.json`` file beside this package: {"license_key": "..."},
    3. the Muse connection entry ``license_key`` on ``custom.mailchimp``
       (a surrogate is fetched through Muse's dynamic-credential flow; the
       real key is swapped in only on the request to the validation host,
       which the installing Muse must register for that connection).
- Validation is a single POST to VALIDATION_ENDPOINT (below). Results are
  cached locally for 24 hours. If the endpoint cannot be reached, a 7-day
  offline grace applies from the last successful check (or from activation
  when no check has succeeded yet).
- After the trial with no valid license, live commands stop with a polite
  refusal and a subscribe message. Demo mode (--demo) never checks a license.

Zero-cost note: this runs entirely on the customer's own Muse. The store
stores nothing about the customer; the only network call is the license
validation POST above, and only when a key is present.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

# TODO(store-owner): replace this placeholder with the production license
# endpoint before distributing the connector. Until then, validation calls
# fail as "unreachable" and the trial / offline-grace rules below govern.
VALIDATION_ENDPOINT = os.environ.get(
    "MAILCHIMP_LICENSE_ENDPOINT", "https://licenses.example.com/v1/check"
)

PRODUCT = "mailchimp"
TRIAL_DAYS = 30
CACHE_HOURS = 24
GRACE_DAYS = 7
SUBSCRIBE_URL = "https://connector-store.example.com/mailchimp"  # TODO: real store URL

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PKG_DIR, "license_state.json")
LICENSE_FILE = os.path.join(PKG_DIR, "license.json")
CONNECTION_NAME = "custom.mailchimp"


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


def get_license_key():
    """Return the license key from env, license.json, or the Muse connection."""
    env_key = os.environ.get("MAILCHIMP_CONNECTOR_LICENSE_KEY", "").strip()
    if env_key:
        return env_key
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as fh:
            key = str(json.load(fh).get("license_key", "")).strip()
        if key:
            return key
    except (OSError, json.JSONDecodeError):
        pass
    # Last resort: the license_key entry on the custom.mailchimp connection.
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


def _validate_online(key: str, install_id: str) -> dict:
    """POST the key to the validation endpoint. Raises on network failure."""
    body = json.dumps(
        {"license_key": key, "product": PRODUCT, "install_id": install_id}
    ).encode("utf-8")
    request = urllib.request.Request(
        VALIDATION_ENDPOINT, data=body, method="POST"
    )
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def check(demo: bool = False) -> dict:
    """Return the license status dict. Never raises for licensing reasons."""
    if demo:
        return {"status": "demo", "active": True,
                "message": "Demo mode. No license check."}

    state = _load_state()
    now = _now()
    if not state.get("install_id"):
        state["install_id"] = uuid.uuid4().hex
    if not state.get("first_activation"):
        state["first_activation"] = now.isoformat()
        _save_state(state)
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
            result = _validate_online(key, state["install_id"])
            valid = bool(result.get("valid"))
            state["last_check_at"] = now.isoformat()
            state["last_check_valid"] = valid
            _save_state(state)
            if valid:
                return {"status": "licensed", "active": True,
                        "message": "License valid.",
                        "plan": result.get("plan"),
                        "checked_at": state["last_check_at"]}
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
                               f"or subscribe: {SUBSCRIBE_URL}"}

    if now < trial_ends:
        return {"status": "trial", "active": True,
                "trial_days_left": trial_days_left,
                "trial_ends": trial_ends.date().isoformat(),
                "message": f"Free trial: {trial_days_left} day(s) left. "
                           f"Subscribe any time: {SUBSCRIBE_URL}"}
    return {"status": "expired", "active": False,
            "trial_ends": trial_ends.date().isoformat(),
            "message": "Your 30-day free trial of the Mailchimp connector "
                       "has ended. Thank you for trying it. To keep using "
                       f"it, subscribe here: {SUBSCRIBE_URL}"}


def ensure_active(demo: bool = False) -> dict:
    """Return the status dict when active. Print a refusal and exit(3) if not."""
    status = check(demo=demo)
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
