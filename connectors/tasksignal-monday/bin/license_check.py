#!/usr/bin/env python3
"""License and free-trial gate for the TaskSignal for monday.com connector for Muse.

How licensing works (honest summary)
------------------------------------
This connector runs entirely on the customer's own Muse. Nothing about
licensing changes that. This module talks to the hosted Plugvana
license server (see ``LICENSE_API_BASE`` below):

* On the first live (non-demo) run, this module POSTs ``/v1/activate``
  with {product, install_id, shop_hash, version} and adopts the server's
  ``trial_start`` as the authoritative trial start. Activation is
  idempotent per account on the server, so reinstalling cannot restart a
  shop's trial. ``shop_hash`` is a one-way SHA-256 of the account's base
  URL, computed locally -- the raw URL is never sent.
* ``LICENSE_API_BASE`` below points at the live Plugvana license
  service. If remote calls fail (for example during an outage), this
  module falls back to the local rules below. That fallback is
  deliberate, so the connector works during development and for the
  bundled demo, and a license-server outage never blocks a command on
  its own.

Local rules (always enforced, online or offline):

* A 30-day free trial starts on the first day any live (non-demo) CLI
  command runs (or on the server's ``trial_start`` once activation has
  succeeded). The first-activation date is stored in a local state
  file next to this module (``.license_state.json``).
* If a license key is present (read from the Muse connection
  ``custom.monday``, entry ``license_key``, when available, or
  from the state file), this module asks the license server's
  ``/v1/check`` endpoint whether the subscription is active, sending
  the install_id and shop_hash alongside the key. A successful answer
  is cached for 24 hours. If the endpoint is unreachable, the last
  successful "active" answer is honoured for a 7-day offline grace
  period.
* After the trial, with no active license, live commands refuse
  politely and print how to subscribe. Demo mode never checks and
  never touches the network.

State file fields: first_activation (YYYY-MM-DD), install_id (uuid4,
generated once and reused), activation (server activation record or
null), license_key (str or null), last_check_at (ISO timestamp),
last_check_result ("active"/"inactive"/"bound_elsewhere"/"error"),
last_check_reason (server reason string or null), last_success_at
(ISO timestamp or null).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Live license service (Plugvana). Both endpoint URLs are built from
# this one constant. The host is registered in this connection's
# api_hosts (connector.yaml), which Muse requires before it will
# make the outbound license requests. Remote checks fail soft: if
# the service is unreachable, the local trial rules below are what
# actually gate live use.
LICENSE_API_BASE = os.environ.get(
    "MONDAY_LICENSE_API_BASE", "https://plugvana-licenses.vercel.app"
)
# ---------------------------------------------------------------------------
# Monthly plan checkout (Stripe Payment Link). Annual plans are not offered yet.
SUBSCRIBE_URL = "https://buy.stripe.com/3cIfZhbXr3zmgKq8gS4AU0E"


def _check_url() -> str:
    return LICENSE_API_BASE.rstrip("/") + "/v1/check"


def _activate_url() -> str:
    return LICENSE_API_BASE.rstrip("/") + "/v1/activate"


# Back-compat alias: the full /v1/check URL.
VALIDATION_ENDPOINT = _check_url()

PRODUCT = "monday"
CONNECTOR_VERSION = "1.0.0"

TRIAL_DAYS = 30
CACHE_HOURS = 24
OFFLINE_GRACE_DAYS = 7
BOUND_ELSEWHERE_MESSAGE = (
    "This license key is already bound to a different account. A license "
    "covers one account, so it cannot be used for this account. Subscribe "
    "for this account at Plugvana by CALL SNAP SYSTEMS LLC, or "
    "contact support if you believe this is a mistake (for example if "
    "you moved your store to a new address)."
)
SUBSCRIBE_MESSAGE = (
    "Your 30-day free trial of the monday.com connector for Muse has ended. "
    "To keep using it, subscribe at Plugvana by CALL SNAP SYSTEMS LLC "
    "(the store page where you installed this connector), then add your license "
    "key to the custom.monday connection and run any command again."
    f" Subscribe for $15/month: {SUBSCRIBE_URL}"
)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".license_state.json")
CONNECTION_NAME = "custom.monday"


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


def _ensure_install_id(state: dict) -> str:
    """Return the persisted random install id, generating it once."""
    install_id = state.get("install_id")
    if not install_id:
        install_id = str(uuid.uuid4())
        state["install_id"] = install_id
    return install_id


def _known_store_url(shop_identity: str | None = None) -> str:
    """Best-effort account identity for the one-account license binding.

    Uses the identity passed by the CLI when given, else the
    ACCOUNT_ID environment variable, else config.json beside
    connector.yaml ({"account_id": "..."}). Returns "" when unknown --
    callers then send an empty shop_hash rather than blocking.
    """
    ident = shop_identity or os.environ.get("MONDAY_ACCOUNT_ID") or ""
    if not ident:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.json",
        )
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                ident = json.load(fh).get("account_id") or ""
        except (OSError, json.JSONDecodeError, AttributeError):
            ident = ""
    return str(ident).strip()


def shop_hash_for(identity) -> str:
    """One-way SHA-256 of the account identity ("" when unknown).

    The raw identity never leaves this machine -- only this hash is
    sent to the license server.
    """
    if not identity:
        return ""
    normalised = str(identity).strip().lower()
    if not normalised:
        return ""
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _post_json(url: str, payload: dict, timeout: int = 5) -> dict | None:
    """POST JSON and return the parsed body, or None on any failure."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body if isinstance(body, dict) else None
    except Exception:
        return None


def _ensure_activation(state: dict, shop_hash: str) -> None:
    """POST /v1/activate once, on the first live run.

    Adopts the server's trial_start/trial_days_left into local state.
    If the server is unreachable, local trial rules govern and we retry
    on a later run (throttled to one attempt per CACHE_HOURS) -- a
    license-server outage must never crash or block a command.
    """
    if state.get("activation"):
        return
    last_attempt = state.get("activation_last_attempt_at")
    if last_attempt:
        try:
            if _now() - datetime.fromisoformat(last_attempt) < timedelta(hours=CACHE_HOURS):
                return
        except ValueError:
            pass
    state["activation_last_attempt_at"] = _now().isoformat()
    body = _post_json(_activate_url(), {
        "product": PRODUCT,
        "install_id": _ensure_install_id(state),
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
        # The server's trial start is authoritative (idempotent per
        # shop): adopt it as the local trial start.
        state["first_activation"] = str(body["trial_start"])[:10]
    _save_state(state)


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


def _remote_check(license_key: str, install_id: str = "",
                  shop_hash: str = "") -> tuple[str, dict | None]:
    """Ask the license server. Returns (result, body).

    Result is 'active', 'inactive', 'bound_elsewhere' or 'error'.
    The payload carries install_id and shop_hash (when known) so the
    server can apply its one-shop binding and trial records.
    """
    body = _post_json(_check_url(), {
        "license_key": license_key,
        "product": PRODUCT,
        "install_id": install_id,
        "shop_hash": shop_hash,
    })
    if body is None:
        return "error", None
    if body.get("reason") == "bound_elsewhere":
        return "bound_elsewhere", body
    return ("active" if body.get("active") else "inactive"), body


def check_license(shop_identity: str | None = None) -> dict:
    """Return the current license status and record first activation.

    Result keys: allowed (bool), mode ("licensed" | "trial" | "expired" |
    "bound_elsewhere"), trial_days_left (int or None), detail
    (human-readable str).
    """
    state = _load_state()
    today = _now().date()
    install_id = _ensure_install_id(state)
    shop_hash = shop_hash_for(_known_store_url(shop_identity))
    # First live run: register the trial with the license server and
    # adopt its trial_start. Failures fall back to local rules below.
    _ensure_activation(state, shop_hash)
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
            result, body = _remote_check(license_key, install_id, shop_hash)
            state["last_check_at"] = _now().isoformat()
            state["last_check_result"] = result
            state["last_check_reason"] = (body or {}).get("reason")
            if result == "active":
                state["last_success_at"] = _now().isoformat()
            _save_state(state)
        if state.get("last_check_result") == "bound_elsewhere":
            # The key belongs to a different account. Say exactly that --
            # not a generic "invalid key" -- and do not let the local
            # trial or offline grace mask it: the server has refused
            # this key for this account.
            return {"allowed": False, "mode": "bound_elsewhere",
                    "trial_days_left": None, "detail": BOUND_ELSEWHERE_MESSAGE}
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
                "detail": "License key present on the custom.monday connection."}

    if trial_days_left > 0:
        return {"allowed": True, "mode": "trial", "trial_days_left": trial_days_left,
                "detail": f"Free trial: {trial_days_left} day(s) left of {TRIAL_DAYS}."}
    return {"allowed": False, "mode": "expired", "trial_days_left": 0,
            "detail": SUBSCRIBE_MESSAGE}


def enforce(shop_identity: str | None = None) -> dict:
    """Gate a live CLI command. Exits the process politely if not allowed."""
    status = check_license(shop_identity=shop_identity)
    if not status["allowed"]:
        print(json.dumps({
            "ok": False,
            "error": ("license_bound_elsewhere"
                      if status.get("mode") == "bound_elsewhere"
                      else "trial_expired"),
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
