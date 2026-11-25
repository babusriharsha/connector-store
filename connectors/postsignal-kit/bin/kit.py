#!/usr/bin/env python3
"""PostSignal for Kit connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads and approval-gated writes against the Kit API (https://api.kit.com/v4), through the registered Muse connection `custom.postsignal-kit`.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.postsignal-kit`) and Muse swaps in the real credential only
on the request to the registered host api.kit.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 kit.py --demo status
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
DEMO_ACCOUNT = {'id': 'acc_9001', 'name': 'Trailhead Letters', 'email': 'hello@trailheadletters.example', 'total_subscribers': 9214, 'plan': 'Creator Pro'}
CONNECTION_NAME = "custom.postsignal-kit"
API_HOST = "api.kit.com"
API_BASE = "https://api.kit.com/v4"
# AUTH_STYLE: "bearer" (Authorization: Bearer <token surrogate>),
# "header:NAME" (custom header), or "query:NAME" (query parameter).
AUTH_STYLE = "header:X-Kit-Api-Key"
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
    """Talks to https://api.kit.com/v4 with the surrogate credential."""

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
        # Kit placement is the custom header X-Kit-Api-Key (AUTH_STYLE
        # "header:X-Kit-Api-Key"); the connection is registered with that
        # header placement, so the surrogate flow puts the key there.
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
        d = self.data
        if path == "account":
            return dict(d["account"])
        if path == "subscribers":
            return {"subscribers": d["subscribers"], "total": len(d["subscribers"])}
        if path == "tags":
            return {"tags": d["tags"], "total": len(d["tags"])}
        if path == "forms":
            return {"forms": d["forms"], "total": len(d["forms"])}
        if path == "sequences":
            return {"sequences": d["sequences"], "total": len(d["sequences"])}
        if path == "broadcasts":
            return {"broadcasts": d["broadcasts"], "total": len(d["broadcasts"])}
        m = re.fullmatch(r"broadcasts/([^/]+)", path)
        if m:
            for b in d["broadcasts"]:
                if str(b["id"]) == m.group(1):
                    return dict(b)
            raise ApiError(404, "Not Found", "No such broadcast in demo data.")
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body):
        m = re.fullmatch(r"tags/([^/]+)/subscribers", path)
        if m:
            return {"demo": True, "simulated": True, "tag_id": m.group(1), "subscriber": body}
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
        account = client.get("account")
        emit({"account": account,
              "license": license_check.check(demo=demo, shop_identity=str(account.get("id", "")) if isinstance(account, dict) else ""),
              "demo": demo})
    if args.command == "subscribers":
        payload = client.get("subscribers"); items = _items(payload, "subscribers")
        emit({"subscribers": items, "total": len(items)})
    if args.command == "tags":
        payload = client.get("tags"); items = _items(payload, "tags")
        emit({"tags": items, "total": len(items)})
    if args.command == "forms":
        payload = client.get("forms"); items = _items(payload, "forms")
        emit({"forms": items, "total": len(items)})
    if args.command == "sequences":
        payload = client.get("sequences"); items = _items(payload, "sequences")
        emit({"sequences": items, "total": len(items)})
    if args.command == "broadcasts":
        payload = client.get("broadcasts"); items = _items(payload, "broadcasts")
        emit({"broadcasts": items, "total": len(items)})
    if args.command == "broadcast":
        emit({"broadcast": client.get(f"broadcasts/{args.broadcast_id}")})
    if args.command == "add-tag":
        body = {"subscriber_id": args.subscriber_id}
        gate_write({"action": "add_tag", "tag_id": args.tag_id, "will_tag": body,
                    "endpoint": f"tags/{args.tag_id}/subscribers"}, args.yes)
        created = client.post(f"tags/{args.tag_id}/subscribers", body)
        result = {"tagged": True, "tag_id": args.tag_id, "subscriber_id": args.subscriber_id, "result": created}
        if demo:
            result["demo"] = True
        emit(result)
    raise ApiError(400, "Unknown command", str(args.command))

def add_subparsers(sub):
    sub.add_parser("status", help="Account info plus license state.")
    sub.add_parser("subscribers", help="List subscribers.")
    sub.add_parser("tags", help="List tags with counts.")
    sub.add_parser("forms", help="List forms.")
    sub.add_parser("sequences", help="List sequences.")
    sub.add_parser("broadcasts", help="List broadcasts.")
    p = sub.add_parser("broadcast", help="One broadcast in detail.")
    p.add_argument("broadcast_id")
    p = sub.add_parser("add-tag", help="Tag an existing subscriber.")
    p.add_argument("--subscriber-id", required=True)
    p.add_argument("--tag-id", required=True)
    p.add_argument("--yes", action="store_true")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PostSignal for Kit for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)
    add_subparsers(sub)
    args = parser.parse_args(argv)
    args.demo = args.demo or os.environ.get("KIT_DEMO") == "1"
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
