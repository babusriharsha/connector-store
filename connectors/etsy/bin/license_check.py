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
- On the first live run this module also POSTs /v1/activate to the license
  server with {product, install_id, shop_hash, version} and adopts the
  server's trial_start as the authoritative trial start (activation is
  idempotent per shop server-side, so a trial cannot be restarted for the
  same shop). install_id is a random uuid4 persisted in the local state
  file. shop_hash is a one-way SHA-256 of the resolved shop id, computed
  locally -- the raw shop id is never sent; when the shop is not known
  yet, shop_hash is sent empty rather than blocking the command. If the
  license server is unreachable, the local trial rules below govern and
  activation is retried on a later run.
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
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONNECTOR_ID = "custom.etsy"
CONNECTION_NAME = "custom.etsy"
PRODUCT = "etsy"
CONNECTOR_VERSION = "1.0.0"

# TODO(publisher): replace this placeholder base URL with the real license
# service URL before public launch (deploy time), or set
# ETSY_LICENSE_API_BASE / ETSY_LICENSE_VALIDATION_URL in the environment.
# Both endpoint URLs are built from this one base constant.
# NOTE (deploy time): the host of LICENSE_API_BASE must be registered in
# the custom.etsy connection (its api_hosts / credential registration),
# or Muse will refuse the outbound license requests and never swap in
# the real license_key on egress -- validation would receive the hsurr:
# surrogate string and fail as an unknown key.
LICENSE_API_BASE = os.environ.get(
    "ETSY_LICENSE_API_BASE", "https://plugvana-licenses.vercel.app"
)
VALIDATION_URL = os.environ.get(
    "ETSY_LICENSE_VALIDATION_URL", LICENSE_API_BASE.rstrip("/") + "/v1/check"
)


def _activate_url() -> str:
    return LICENSE_API_BASE.rstrip("/") + "/v1/activate"


TRIAL_DAYS = 30
CACHE_SECONDS = 24 * 60 * 60
OFFLINE_GRACE_SECONDS = 7 * 24 * 60 * 60
BOUND_ELSEWHERE_MESSAGE = (
    "This license key is already bound to a different shop. A license "
    "covers one shop, so it cannot be used for this shop. SellSignal "
    "for Etsy is coming soon and is not yet available for purchase. "
    "Contact support if you believe this is a mistake."
)

# SellSignal for Etsy is not yet available for purchase, so there
# is no checkout link yet. Annual plans are not offered yet.
SUBSCRIBE_URL = ""

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


def _ensure_install_id(state: dict) -> str:
    """Return the persisted random install id, generating it once."""
    install_id = state.get("install_id")
    if not install_id:
        install_id = str(uuid.uuid4())
        state["install_id"] = install_id
        _save_state(state)
    return install_id


def _known_shop_id() -> str:
    """Best-effort shop id from local sources only (no network).

    Mirrors etsy.py's cheap resolution steps: the ETSY_SHOP_ID env var,
    then the cached shop.json the CLI writes after resolving the shop
    against the Etsy API. Returns "" when not known yet -- callers then
    send an empty shop_hash rather than blocking the command.
    """
    env_shop = os.environ.get("ETSY_SHOP_ID", "").strip()
    if env_shop:
        return env_shop
    try:
        saved = json.loads((STATE_DIR / "shop.json").read_text(encoding="utf-8"))
        if saved.get("shop_id"):
            return str(saved["shop_id"])
    except Exception:
        pass
    return ""


def shop_hash_for(shop_id: str | None) -> str:
    """One-way SHA-256 of the shop id ("" when unknown). Hash only --
    the raw shop id never leaves this machine."""
    if not shop_id:
        return ""
    return hashlib.sha256(str(shop_id).strip().encode("utf-8")).hexdigest()


def _post_json(url: str, payload: dict, timeout: int = 6) -> dict | None:
    """POST JSON and return the parsed body, or None on any failure."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body if isinstance(body, dict) else None
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return body if isinstance(body, dict) else None
        except Exception:
            return None
    except Exception:
        return None


def _ensure_activation(state: dict, shop_hash: str) -> None:
    """POST /v1/activate once, on the first live run.

    Adopts the server's trial_start as the local first_activation
    (epoch seconds, start of that UTC day). If the server is
    unreachable, local trial rules govern and we retry on a later run
    (throttled to one attempt per CACHE_SECONDS) -- a license-server
    outage must never crash or block a command.
    """
    if state.get("activation"):
        return
    last_attempt = int(state.get("activation_last_attempt") or 0)
    if last_attempt and _now() - last_attempt < CACHE_SECONDS:
        return
    state["activation_last_attempt"] = _now()
    _save_state(state)
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
            "at": _now(),
        }
        try:
            start = datetime.fromisoformat(str(body["trial_start"])[:10])
            state["first_activation"] = int(
                start.replace(tzinfo=timezone.utc).timestamp()
            )
        except ValueError:
            pass
        _save_state(state)


def _license_key_material() -> str | None:
    """Return an opaque identifier for the installed license key, or None.

    Prefers the Muse secure connection surrogate. The surrogate is stable
    for a given stored credential, so its hash identifies the key without
    ever exposing it. Falls back to the ETSY_CONNECTOR_LICENSE_KEY
    environment variable for manual testing outside Muse.

    Deploy-time note: the real key only materialises on egress to a
    *registered* validation host, so the host of LICENSE_API_BASE must
    be registered in the custom.etsy connection before launch (see the
    note at LICENSE_API_BASE above). This module never registers
    anything itself.
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


def _remote_check(material: str, install_id: str = "",
                  shop_hash: str = "") -> dict | None:
    """POST the license material to the validation endpoint.

    When the material is a Muse surrogate, Muse replaces it with the real
    key on egress to the registered validation host. The payload also
    carries install_id and shop_hash (when known) so the server can
    apply its one-shop binding and trial records. Returns the parsed
    JSON body on any HTTP response, or None when the endpoint is
    unreachable.
    """
    body = json.dumps(
        {"connector": CONNECTOR_ID, "license_key": material,
         "install_id": install_id, "shop_hash": shop_hash}
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

    install_id = _ensure_install_id(state)
    shop_hash = shop_hash_for(_known_shop_id())
    # First live run: register the trial with the license server and
    # adopt its trial_start (may rewrite first_activation above).
    _ensure_activation(state, shop_hash)

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
        "install_id": install_id,
        "shop_hash": shop_hash,
    }

    last = state.get("last_check") or {}
    if (
        not force
        and last.get("at")
        and now - int(last["at"]) < CACHE_SECONDS
        and last.get("key_fingerprint") == fingerprint
        and last.get("reason") == "bound_elsewhere"
    ):
        # Cached refusal: this key is bound to a different shop. Keep
        # surfacing that exact reason instead of a generic refusal.
        result.update(
            {
                "ok": False,
                "status": "bound_elsewhere",
                "reason": "bound_elsewhere",
                "source": "cache",
            }
        )
        return result
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
        remote = _remote_check(material, install_id, shop_hash)
        if remote is not None:
            valid = bool(remote.get("valid"))
            reason = remote.get("reason")
            state["last_check"] = {
                "at": now,
                "valid": valid,
                "status": remote.get("status", "active" if valid else "invalid"),
                "key_fingerprint": fingerprint,
                "reason": reason,
            }
            if valid:
                state["last_successful_check"] = now
            _save_state(state)
            if reason == "bound_elsewhere":
                # The key belongs to a different shop. Surface that
                # exact reason; do not mask it as a generic invalid
                # key or let the local trial clock override it.
                result.update(
                    {
                        "ok": False,
                        "status": "bound_elsewhere",
                        "reason": "bound_elsewhere",
                        "source": "remote",
                    }
                )
                return result
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
    if result.get("reason") == "bound_elsewhere" or result.get("status") == "bound_elsewhere":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "license_bound_elsewhere",
                    "message": BOUND_ELSEWHERE_MESSAGE,
                    "license": result,
                },
                indent=2,
            )
        )
        raise SystemExit(3)
    print(
        json.dumps(
            {
                "ok": False,
                "error": "license_expired",
                "message": (
                    "The free trial of the Etsy connector for Muse has ended. "
                    "SellSignal for Etsy is coming soon and is not yet available "
                    "for purchase. Your shop data is untouched "
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
