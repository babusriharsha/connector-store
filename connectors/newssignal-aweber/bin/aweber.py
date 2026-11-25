#!/usr/bin/env python3
"""NewsSignal for AWeber connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads and approval-gated writes against the AWeber API (https://api.aweber.com/1.0), through the registered Muse connection `custom.newssignal-aweber`.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.newssignal-aweber`) and Muse swaps in the real credential only
on the request to the registered host api.aweber.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 aweber.py --demo status
"""

from __future__ import annotations

import argparse
import json
import re
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BIN_DIR)
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
DEMO_ACCOUNT = None
CONNECTION_NAME = "custom.newssignal-aweber"
API_HOST = "api.aweber.com"
API_BASE = "https://api.aweber.com/1.0"
# AUTH_STYLE: "bearer" (Authorization: Bearer <token surrogate>),
# "header:NAME" (custom header), or "query:NAME" (query parameter).
AUTH_STYLE = "bearer"
DYNAMIC_CREDENTIALS_DIR = "/opt/muse/skills/custom-connector-setup/bin"

sys.path.insert(0, BIN_DIR)
import license_check  # noqa: E402


class ApiError(RuntimeError):
    def __init__(self, status, title, detail):
        super().__init__(detail or title or f"HTTP {status}")
        self.status = status
        self.title = title
        self.detail = detail


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

class LiveClient:
    """Talks to https://api.aweber.com/1.0 with the surrogate credential."""

    def __init__(self):
        sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
        from dynamic_credentials import add_surrogate_to_request, read_json_response

        self._add_surrogate = add_surrogate_to_request
        self._read_json = read_json_response

    def request(self, method: str, path: str, params=None, body=None):
        url = f"{API_BASE}/{path}" if path else API_BASE
        params = dict(params or {})
        if AUTH_STYLE.startswith("query:"):
            # Placeholder value; Muse's surrogate flow replaces the
            # registered entry on egress. We still need the parameter
            # present, so use the entry name with a surrogate marker the
            # helper recognises is NOT possible generically -- instead
            # the helper is applied below like other styles.
            pass
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        self._add_surrogate(request, CONNECTION_NAME, allowed_hosts=[API_HOST])
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=60) as response:
                if response.status == 204:
                    return {}
                return self._read_json(response)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                title = payload.get("title") or payload.get("message") or ""
                detail = payload.get("detail") or payload.get("error") or raw[:300]
            else:
                title, detail = "", raw[:300]
            raise ApiError(exc.code, str(title), str(detail)) from exc

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def post(self, path, body):
        return self.request("POST", path, body=body)



CONFIG_PATH = os.path.join(PKG_DIR, "config.json")

def resolve_account_id(cli_account=None) -> str:
    """Account id is routing info, not a secret. Order: --account flag,
    AWEBER_ACCOUNT_ID env var, config.json beside the package."""
    if cli_account:
        return str(cli_account).strip()
    env_id = os.environ.get("AWEBER_ACCOUNT_ID", "").strip()
    if env_id:
        return env_id
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            aid = str(json.load(fh).get("account_id", "")).strip()
        if aid:
            return aid
    except (OSError, json.JSONDecodeError):
        pass
    return ""

class DemoClient:
    """Serves the bundled fictional data in demo_data.json. No network."""
    def __init__(self):
        with open(DEMO_PATH, "r", encoding="utf-8") as fh:
            self.data = json.load(fh)
    def get(self, path, params=None):
        d = self.data
        if path == "accounts":
            return {"entries": d["accounts"], "total_size": len(d["accounts"])}
        if re.fullmatch(r"accounts/[^/]+/lists", path):
            return {"entries": d["lists"], "total_size": len(d["lists"])}
        if re.fullmatch(r"accounts/[^/]+/lists/[^/]+/subscribers", path):
            return {"entries": d["subscribers"], "total_size": len(d["subscribers"])}
        if re.fullmatch(r"accounts/[^/]+/lists/[^/]+/broadcasts", path):
            return {"entries": d["broadcasts"], "total_size": len(d["broadcasts"])}
        if re.fullmatch(r"accounts/[^/]+/lists/[^/]+/campaigns", path):
            return {"entries": d["campaigns"], "total_size": len(d["campaigns"])}
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body):
        if re.fullmatch(r"accounts/[^/]+/lists/[^/]+/subscribers", path):
            out = dict(body); out.update({"id": "asub_demo_new", "demo": True, "simulated": True})
            return out
        raise ApiError(404, "Not in demo", f"No demo fixture for POST {path}")

def _entries(payload):
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return payload["entries"]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    return []

def gate_write(summary, yes):
    print(json.dumps(summary, indent=2))
    if not yes:
        print(json.dumps({"confirmed": False, "message": "Nothing was changed. Review the summary above, then re-run the same command with --yes to apply it."}, indent=2))
        raise SystemExit(2)

def _account_id(args, client):
    aid = resolve_account_id(getattr(args, "account", None))
    if aid:
        return aid
    accounts = _entries(client.get("accounts"))
    if accounts:
        return str(accounts[0].get("id"))
    raise ApiError(404, "No account", "No AWeber account found for this credential.")



def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def run_command(client, args) -> int:
    demo = bool(args.demo)
    if args.command == "status":
        accounts = _entries(client.get("accounts"))
        account = accounts[0] if accounts else {}
        emit({"account": account,
              "license": license_check.check(demo=demo, shop_identity=str(account.get("id", ""))),
              "demo": demo})
    if args.command == "lists":
        aid = _account_id(args, client)
        payload = client.get(f"accounts/{aid}/lists"); items = _entries(payload)
        emit({"account_id": aid, "lists": items, "total": len(items)})
    if args.command in ("subscribers", "broadcasts", "campaigns"):
        aid = _account_id(args, client)
        payload = client.get(f"accounts/{aid}/lists/{args.list}/{args.command}")
        items = _entries(payload)
        emit({"account_id": aid, "list_id": args.list, args.command: items, "total": len(items)})
    if args.command == "add-subscriber":
        if not args.consent:
            emit({"ok": False, "error": "consent_required",
                  "message": "Refused. Adding a subscriber requires --consent, your explicit confirmation that this person opted in to receive email. Never add people who have not opted in: it breaks anti-spam law (CAN-SPAM, GDPR, CASL) and the provider's terms, and damages sending reputation."}, 2)
        aid = _account_id(args, client)
        body = {"email": args.email, "name": args.name or "", "ad_tracking": "connector"}
        gate_write({"action": "add_subscriber", "account_id": aid, "list_id": args.list,
                    "will_add": body, "consent_confirmed": True}, args.yes)
        created = client.post(f"accounts/{aid}/lists/{args.list}/subscribers", body)
        result = {"added": created}
        if demo:
            result["demo"] = True
        emit(result)
    raise ApiError(400, "Unknown command", str(args.command))

def add_subparsers(sub):
    for name, helptext in [("status", "Account info plus license state."),
                           ("lists", "List the account's lists.")]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--account", default=None, help="AWeber account id override.")
    for name in ("subscribers", "broadcasts", "campaigns"):
        p = sub.add_parser(name, help=f"List {name} of one list.")
        p.add_argument("--list", required=True, help="List id.")
        p.add_argument("--account", default=None)
    p = sub.add_parser("add-subscriber", help="Add a subscriber who has opted in.")
    p.add_argument("--list", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--account", default=None)
    p.add_argument("--consent", action="store_true", help="Required. Confirms this person opted in.")
    p.add_argument("--yes", action="store_true")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NewsSignal for AWeber for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)
    add_subparsers(sub)
    args = parser.parse_args(argv)
    args.demo = args.demo or os.environ.get("AWEBER_DEMO") == "1"
    if not args.demo:
        try:
            license_check.ensure_active(demo=False)
        except SystemExit:
            raise
        except Exception:
            pass
    client = DemoClient() if args.demo else LiveClient()
    try:
        return run_command(client, args)
    except SystemExit:
        raise
    except ApiError as exc:
        emit({"ok": False, "error": exc.title or "api_error",
              "status": exc.status, "detail": exc.detail}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
