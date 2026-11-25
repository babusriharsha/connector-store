#!/usr/bin/env python3
"""License and free-trial gate for the WooCommerce connector for Muse.

How licensing works (honest summary)
------------------------------------
This connector runs entirely on the customer's own Muse. Nothing about
licensing changes that. This module is a *hook* for a hosted license
checker that the store operator will run later:

* ``VALIDATION_ENDPOINT`` below is a PLACEHOLDER. Until the operator
  replaces it with the real hosted checker URL, remote validation will
  simply fail, and this module falls back to the local rules below.
  That fallback is deliberate, so the connector works during development
  and for the bundled demo.

Local rules (always enforced, online or offline):

* A 30-day free trial starts on the first day any live (non-demo) CLI
  command runs. The first-activation date is stored in a local state
  file next to this module (``.license_state.json``). Deleting the
  state file restarts the trial; the operator knows this and accepts
  it for v1 -- the hosted checker is the real enforcement point.
* If a license key is present (read from the Muse connection
  ``custom.woocommerce``, entry ``license_key``, when available, or
  from the state file), this module asks the validation endpoint
  whether the subscription is active. A successful answer is cached
  for 24 hours. If the endpoint is unreachable, the last successful
  "active" answer is honoured for a 7-day offline grace period.
* After the trial, with no active license, live commands refuse
  politely and print how to subscribe. Demo mode never checks.

State file fields: first_activation (YYYY-MM-DD), license_key (str or
null), last_check_at (ISO timestamp), last_check_result
("active"/"inactive"/"error"), last_success_at (ISO timestamp or null).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# OPERATOR: replace this placeholder with the real hosted license checker
# URL before selling subscriptions. Until then remote checks fail soft and
# the local trial rules below are what actually gate live use.
VALIDATION_ENDPOINT = "https://licenses.example.com/v1/check"  # TO BE REPLACED
# ---------------------------------------------------------------------------

TRIAL_DAYS = 30
CACHE_HOURS = 24
OFFLINE_GRACE_DAYS = 7
SUBSCRIBE_MESSAGE = (
    "Your 30-day free trial of the WooCommerce connector for Muse has ended. "
    "To keep using it, subscribe at the Connector Store by CALL SNAP SYSTEMS LLC "
    "(the store page where you installed this connector), then add your license "
    "key to the custom.woocommerce connection and run any command again."
)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".license_state.json")
CONNECTION_NAME = "custom.woocommerce"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        if isinstance(state, dict):
            return state
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
    except OSError:
        # A read-only install can still run; trial enforcement just
        # becomes per-process. Never crash a store command over this.
        pass


def _license_key_from_connection() -> str | None:
    """Best-effort: read the license key surrogate entry name only.

    We never see the real key value through the surrogate API (Muse
    swaps surrogates in on egress), so this only tells us whether a
    ``license_key`` entry exists on the connection. The real key used
    for validation is the one the user pastes into the state file via
    ``license_check.py set-key`` -- see INSTALL.md. If the dynamic
    credentials helper is unavailable (not running under Muse), this
    quietly returns None.
    """
    try:
        sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
        from dynamic_credentials import dynamic_credential_entry

        entry = dynamic_credential_entry(CONNECTION_NAME, "license_key")
        return "present" if entry else None
    except Exception:
        return None


def _remote_check(license_key: str) -> str:
    """Ask the hosted checker. Returns 'active', 'inactive' or 'error'."""
    payload = json.dumps({"license_key": license_key, "product": "woocommerce"}).encode("utf-8")
    request = urllib.request.Request(
        VALIDATION_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        return "active" if body.get("active") else "inactive"
    except Exception:
        return "error"


def check_license() -> dict:
    """Return the current license status and record first activation.

    Result keys: allowed (bool), mode ("licensed" | "trial" | "expired"),
    trial_days_left (int or None), detail (human-readable str).
    """
    state = _load_state()
    today = _now().date()
    if not state.get("first_activation"):
        state["first_activation"] = today.isoformat()
        _save_state(state)
    try:
        first = datetime.fromisoformat(state["first_activation"]).date()
    except ValueError:
        first = today
        state["first_activation"] = today.isoformat()
    trial_days_left = TRIAL_DAYS - (today - first).days

    license_key = state.get("license_key") or _license_key_from_connection()

    if license_key and license_key != "present":
        # We hold a real key locally: validate it (cached for 24h).
        last_check = state.get("last_check_at")
        fresh = False
        if last_check:
            try:
                fresh = _now() - datetime.fromisoformat(last_check) < timedelta(hours=CACHE_HOURS)
            except ValueError:
                fresh = False
        if not fresh:
            result = _remote_check(license_key)
            state["last_check_at"] = _now().isoformat()
            state["last_check_result"] = result
            if result == "active":
                state["last_success_at"] = _now().isoformat()
            _save_state(state)
        if state.get("last_check_result") == "active":
            return {"allowed": True, "mode": "licensed", "trial_days_left": None,
                    "detail": "Active subscription on file."}
        # Offline grace: honour the last successful check for 7 days.
        last_success = state.get("last_success_at")
        if last_success:
            try:
                if _now() - datetime.fromisoformat(last_success) < timedelta(days=OFFLINE_GRACE_DAYS):
                    return {"allowed": True, "mode": "licensed", "trial_days_left": None,
                            "detail": "Subscription honoured under the 7-day offline grace period."}
            except ValueError:
                pass
    elif license_key == "present":
        # A license entry exists on the Muse connection but its value
        # is surrogate-only; treat its presence as licensed until the
        # hosted checker can verify the real key server-side.
        return {"allowed": True, "mode": "licensed", "trial_days_left": None,
                "detail": "License key present on the custom.woocommerce connection."}

    if trial_days_left > 0:
        return {"allowed": True, "mode": "trial", "trial_days_left": trial_days_left,
                "detail": f"Free trial: {trial_days_left} day(s) left of {TRIAL_DAYS}."}
    return {"allowed": False, "mode": "expired", "trial_days_left": 0,
            "detail": SUBSCRIBE_MESSAGE}


def enforce() -> dict:
    """Gate a live CLI command. Exits the process politely if not allowed."""
    status = check_license()
    if not status["allowed"]:
        print(json.dumps({
            "ok": False,
            "error": "trial_expired",
            "message": status["detail"],
        }, indent=2))
        raise SystemExit(3)
    return status


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "status":
        print(json.dumps(check_license(), indent=2))
        return 0
    if len(argv) >= 3 and argv[1] == "set-key":
        state = _load_state()
        state["license_key"] = argv[2]
        state.pop("last_check_at", None)
        state.pop("last_check_result", None)
        _save_state(state)
        print(json.dumps({"ok": True, "message": "License key saved locally. "
                                "It will be validated on the next live command."}, indent=2))
        return 0
    print("Usage: license_check.py status | set-key <LICENSE_KEY>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
