#!/usr/bin/env python3
"""License and trial enforcement for the Etsy Muse connector (custom.etsy).

Design rules (publisher: CALL SNAP SYSTEMS LLC):

- The connector runs entirely on the customer's own Muse. This module stores
  only a small local state file (activation date, last check result). It never
  sees Etsy data and never sends any.
- A 30-day free trial runs from the first activation recorded locally.
- A license key, when present, lives in the registered Muse connection
  `custom.etsy` as the `license_key` entry. This module only ever handles the
  `hsurr:` surrogate for that entry. Muse swaps in the real key on the
  approved outbound request to the validation host, so the real key never
  appears in this process, in a file, or in a log.
- Validation results are cached for 24 hours. If the validation endpoint is
  unreachable, a 7-day offline grace applies from the last successful check,
  and the free trial still applies on its own clock.
- The validation endpoint below is a PLACEHOLDER. The publisher replaces it
  (or sets ETSY_LICENSE_VALIDATION_URL) before public launch.

Exit codes when run by bin/etsy.py through enforce(): 0 means allowed. On
refusal it prints a JSON object to stdout and raises SystemExit(3).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONNECTOR_ID = "custom.etsy"
CONNECTION_NAME = "custom.etsy"

# TODO(publisher): replace this placeholder with the real license service URL
# before public launch, or set ETSY_LICENSE_VALIDATION_URL in the environment.
VALIDATION_URL = os.environ.get(
    "ETSY_LICENSE_VALIDATION_URL", "https://licenses.example.com/v1/check"
)

TRIAL_DAYS = 30
CACHE_SECONDS = 24 * 60 * 60
OFFLINE_GRACE_SECONDS = 7 * 24 * 60 * 60

SUBSCRIBE_URL = "https://licenses.example.com/subscribe/etsy"  # TODO(publisher)

STATE_DIR = Path(
    os.environ.get(
        "ETSY_CONNECTOR_STATE_DIR", Path.home() / ".cache" / "custom-etsy"
    )
)
STATE_FILE = STATE_DIR / "license.json"


def _now() -> int:
    return int(time.time())


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _license_key_material() -> str | None:
    """Return an opaque identifier for the installed license key, or None.

    Prefers the Muse secure connection surrogate. The surrogate is stable
    for a given stored credential, so its hash identifies the key without
    ever exposing it. Falls back to the ETSY_CONNECTOR_LICENSE_KEY
    environment variable for manual testing outside Muse.
    """
    try:
        sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
        from dynamic_credentials import dynamic_credential_entry

        entry = dynamic_credential_entry(CONNECTION_NAME, "license_key")
        surrogate = str(entry.get("surrogate", "")).strip()
        if surrogate:
            return surrogate
    except Exception:
        pass
    env_key = os.environ.get("ETSY_CONNECTOR_LICENSE_KEY", "").strip()
    return env_key or None


def _key_fingerprint(material: str | None) -> str | None:
    if not material:
        return None
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _remote_check(material: str) -> dict | None:
    """POST the license material to the validation endpoint.

    When the material is a Muse surrogate, Muse replaces it with the real
    key on egress to the registered validation host. Returns the parsed JSON
    body on any HTTP response, or None when the endpoint is unreachable.
    """
    body = json.dumps(
        {"connector": CONNECTOR_ID, "license_key": material}
    ).encode("utf-8")
    request = urllib.request.Request(
        VALIDATION_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"valid": False, "status": "rejected"}
    except Exception:
        return None


def check(force: bool = False) -> dict:
    """Evaluate license and trial state. Returns a status dict."""
    state = _load_state()
    now = _now()
    if not state.get("first_activation"):
        state["first_activation"] = now
        _save_state(state)

    material = _license_key_material()
    fingerprint = _key_fingerprint(material)
    if fingerprint and state.get("key_fingerprint") != fingerprint:
        state["key_fingerprint"] = fingerprint
        state.pop("last_check", None)
        _save_state(state)

    trial_elapsed = now - int(state["first_activation"])
    trial_days_left = max(0, TRIAL_DAYS - trial_elapsed // 86400)
    in_trial = trial_elapsed < TRIAL_DAYS * 86400

    result = {
        "connector": CONNECTOR_ID,
        "first_activation": state["first_activation"],
        "trial_days_left": trial_days_left,
        "has_license_key": bool(material),
    }

    last = state.get("last_check") or {}
    if (
        not force
        and last.get("at")
        and now - int(last["at"]) < CACHE_SECONDS
        and last.get("key_fingerprint") == fingerprint
    ):
        result.update(
            {
                "ok": bool(last.get("valid")),
                "status": last.get("status", "unknown"),
                "source": "cache",
            }
        )
        if result["ok"] or in_trial:
            result["ok"] = True
            if not last.get("valid"):
                result["status"] = "trial"
            return result
        return result

    if material:
        remote = _remote_check(material)
        if remote is not None:
            valid = bool(remote.get("valid"))
            state["last_check"] = {
                "at": now,
                "valid": valid,
                "status": remote.get("status", "active" if valid else "invalid"),
                "key_fingerprint": fingerprint,
            }
            if valid:
                state["last_successful_check"] = now
            _save_state(state)
            result.update(
                {
                    "ok": valid or in_trial,
                    "status": state["last_check"]["status"]
                    if valid
                    else ("trial" if in_trial else "invalid"),
                    "source": "remote",
                }
            )
            return result

    last_success = int(state.get("last_successful_check") or 0)
    if material and last_success and now - last_success < OFFLINE_GRACE_SECONDS:
        result.update({"ok": True, "status": "active_grace", "source": "grace"})
        return result

    if in_trial:
        result.update({"ok": True, "status": "trial", "source": "trial"})
        return result

    result.update({"ok": False, "status": "expired", "source": "trial"})
    return result


def enforce() -> dict:
    """Allow the caller to proceed, or print a refusal and exit with code 3."""
    result = check()
    if result["ok"]:
        return result
    print(
        json.dumps(
            {
                "ok": False,
                "error": "license_expired",
                "message": (
                    "The free trial of the Etsy connector for Muse has ended. "
                    "To keep checking your Etsy shop with Muse, subscribe at "
                    f"{SUBSCRIBE_URL} and reconnect. Your shop data is untouched "
                    "and nothing was sent anywhere."
                ),
                "license": result,
            },
            indent=2,
        )
    )
    raise SystemExit(3)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "status"
    if command == "status":
        print(json.dumps(check(), indent=2))
        return 0
    if command == "check":
        print(json.dumps(check(force=True), indent=2))
        return 0
    print(
        json.dumps(
            {
                "ok": False,
                "error": "unknown_command",
                "message": "Use: license_check.py [status|check]",
            }
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
