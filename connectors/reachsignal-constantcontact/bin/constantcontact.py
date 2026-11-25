#!/usr/bin/env python3
"""ReachSignal for Constant Contact connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads and approval-gated writes against the Constant Contact API (https://api.cc.email/v3), through the registered Muse connection `custom.reachsignal-constantcontact`.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.reachsignal-constantcontact`) and Muse swaps in the real credential only
on the request to the registered host api.cc.email.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 constantcontact.py --demo status
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
DEMO_ACCOUNT = {'name': 'Bayview Fitness Studio', 'total_contacts': 4380, 'plan': 'Email Plus'}
CONNECTION_NAME = "custom.reachsignal-constantcontact"
API_HOST = "api.cc.email"
API_BASE = "https://api.cc.email/v3"
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
    """Talks to https://api.cc.email/v3 with the surrogate credential."""

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



class DemoClient:
    """Serves the bundled fictional data in demo_data.json. No network."""
    def __init__(self):
        with open(DEMO_PATH, "r", encoding="utf-8") as fh:
            self.data = json.load(fh)
    def get(self, path, params=None):
        params = params or {}
        d = self.data
        if path == "contacts":
            items = list(d["contacts"])
            st = params.get("status")
            if st:
                items = [c for c in items if c.get("status") == st]
            return {"contacts": items, "total": len(items)}
        if path == "contact_lists":
            return {"lists": d["lists"], "total": len(d["lists"])}
        if path == "email_campaigns":
            return {"campaigns": d["campaigns"], "total": len(d["campaigns"])}
        m = re.fullmatch(r"email_campaigns/([^/]+)", path)
        if m:
            for c in d["campaigns"]:
                if str(c["id"]) == m.group(1):
                    return dict(c)
            raise ApiError(404, "Not Found", "No such campaign in demo data.")
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body):
        if path == "contacts":
            out = dict(body); out.update({"id": "con_demo_new", "demo": True, "simulated": True})
            return out
        raise ApiError(404, "Not in demo", f"No demo fixture for POST {path}")

def _items(payload, key):
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    return []

def gate_write(summary, yes):
    print(json.dumps(summary, indent=2))
    if not yes:
        print(json.dumps({"confirmed": False, "message": "Nothing was changed. Review the summary above, then re-run the same command with --yes to apply it."}, indent=2))
        raise SystemExit(2)



def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def run_command(client, args) -> int:
    demo = bool(args.demo)
    if args.command == "status":
        contacts = client.get("contacts"); lists = client.get("contact_lists")
        c_items, l_items = _items(contacts, "contacts"), _items(lists, "lists")
        emit({"account": DEMO_ACCOUNT if demo else {"name": None},
              "total_contacts": (DEMO_ACCOUNT or {}).get("total_contacts") if demo else len(c_items), "lists": len(l_items),
              "license": license_check.check(demo=demo, shop_identity=""),
              "demo": demo})
    if args.command == "contacts":
        params = {}
        if args.status:
            params["status"] = args.status
        payload = client.get("contacts", params=params); items = _items(payload, "contacts")
        emit({"contacts": items, "total": len(items)})
    if args.command == "lists":
        payload = client.get("contact_lists"); items = _items(payload, "lists")
        emit({"lists": items, "total": len(items)})
    if args.command == "campaigns":
        payload = client.get("email_campaigns"); items = _items(payload, "campaigns")
        emit({"campaigns": items, "total": len(items)})
    if args.command == "campaign":
        emit({"campaign": client.get(f"email_campaigns/{args.campaign_id}")})
    if args.command == "add-contact":
        if not args.consent:
            emit({"ok": False, "error": "consent_required",
                  "message": "Refused. Adding a contact requires --consent, your explicit confirmation that this person opted in to receive email. Never add people who have not opted in: it breaks anti-spam law (CAN-SPAM, GDPR, CASL) and the provider's terms, and damages sending reputation."}, 2)
        body = {"email_address": {"address": args.email, "permission_to_send": "explicit"},
                "create_source": "Account"}
        if args.first_name:
            body["first_name"] = args.first_name
        if args.last_name:
            body["last_name"] = args.last_name
        if args.list:
            body["list_memberships"] = args.list
        gate_write({"action": "add_contact", "will_add": body, "consent_confirmed": True}, args.yes)
        created = client.post("contacts", body)
        result = {"added": created}
        if demo:
            result["demo"] = True
        emit(result)
    raise ApiError(400, "Unknown command", str(args.command))

def add_subparsers(sub):
    sub.add_parser("status", help="Account summary plus license state.")
    p = sub.add_parser("contacts", help="List contacts.")
    p.add_argument("--status", default=None, help="Filter by contact status")
    sub.add_parser("lists", help="List contact lists with counts.")
    sub.add_parser("campaigns", help="List email campaigns.")
    p = sub.add_parser("campaign", help="One campaign in detail.")
    p.add_argument("campaign_id")
    p = sub.add_parser("add-contact", help="Add a contact who has opted in.")
    p.add_argument("--email", required=True)
    p.add_argument("--first-name", default=None)
    p.add_argument("--last-name", default=None)
    p.add_argument("--list", action="append", default=None, help="List id. Repeat for several.")
    p.add_argument("--consent", action="store_true", help="Required. Confirms this person opted in.")
    p.add_argument("--yes", action="store_true")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ReachSignal for Constant Contact for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)
    add_subparsers(sub)
    args = parser.parse_args(argv)
    args.demo = args.demo or os.environ.get("CONSTANT_CONTACT_DEMO") == "1"
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
