#!/usr/bin/env python3
"""LedgerSignal for Sage connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads and one approval-gated draft write against the Sage Business Cloud Accounting API v3.1, through Muse's secure flow (connection custom.ledgersignal-sage). Placement registered for this connection is bearer_header: Muse's surrogate helper applies the OAuth2 access token as an Authorization: Bearer header on requests to api.accounting.sage.com.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.ledgersignal-sage`) and Muse swaps in the real credential only
on the request to the registered host api.accounting.sage.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 sage.py --demo status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import re
from datetime import date, timedelta

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BIN_DIR)
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONNECTION_NAME = "custom.ledgersignal-sage"
API_HOST = "api.accounting.sage.com"
API_BASE = "https://api.accounting.sage.com/v3.1"
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
    """Talks to https://api.accounting.sage.com/v3.1 with the surrogate credential."""

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
        data = self.data
        if path == "businesses":
            return {"business": data["business"]}
        if path == "contacts":
            return {"$items": data["contacts"], "total": len(data["contacts"])}
        if path == "sales_invoices":
            items = list(data["sales_invoices"])
            if params.get("status"):
                items = [i for i in items if i.get("status") == params["status"]]
            return {"$items": items, "total": len(items)}
        m = re.fullmatch(r"sales_invoices/([^/]+)", path)
        if m:
            for inv in data["sales_invoices"]:
                if str(inv["id"]) == m.group(1):
                    return dict(inv)
            raise ApiError(404, "Not Found", "No such sales invoice in demo data.")
        if path == "purchase_invoices":
            return {"$items": data["purchase_invoices"], "total": len(data["purchase_invoices"])}
        if path == "bank_accounts":
            return {"$items": data["bank_accounts"], "total": len(data["bank_accounts"])}
        if path == "ledger_accounts":
            return {"$items": data["ledger_accounts"], "total": len(data["ledger_accounts"])}
        if path == "journals":
            return {"$items": data["journals"], "total": len(data["journals"])}
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")

    def post(self, path, body):
        if path == "sales_invoices":
            created = {"id": "demo-new-invoice", "status": "draft"}
            if isinstance(body, dict) and isinstance(body.get("sales_invoice"), dict):
                created.update(body["sales_invoice"])
            created["status"] = "draft"
            return created
        raise ApiError(404, "Not in demo", f"No demo fixture for POST {path}")



# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _today():
    from datetime import date
    return date.today().isoformat()


def _is_overdue(inv, due_key="due_date", status_key="status", paid_statuses=("PAID", "paid", "Paid")):
    due = inv.get(due_key) or ""
    status = str(inv.get(status_key) or "")
    return bool(due) and due < _today() and status not in paid_statuses


def gate(summary, yes):
    """Approval gate for writes: no --yes -> print proposal, exit 2."""
    if not yes:
        emit({"ok": False, "approval_required": True, "proposal": summary,
              "message": "Nothing was changed. Show this proposal to the owner and re-run with --yes only after they approve this specific change."}, 2)


def demo_write_result(summary, created):
    emit({"ok": True, "demo": True, "simulated": True,
          "message": "Demo mode: this write was simulated only; nothing was created in the real account.",
          "proposal": summary, "created": created}, 0)

def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LedgerSignal for Sage for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    p = sub.add_parser("invoices"); p.add_argument("--status", default=None)
    p = sub.add_parser("invoice"); p.add_argument("id")
    sub.add_parser("contacts")
    sub.add_parser("overdue")
    sub.add_parser("bank-accounts")
    sub.add_parser("chart")
    p = sub.add_parser("create-invoice")
    p.add_argument("--contact-id", required=True); p.add_argument("--description", required=True)
    p.add_argument("--amount", required=True, type=float); p.add_argument("--due-date", default=None)
    p.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)

    if not args.demo:
        license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try:
        return run_command(client, args)
    except ApiError as exc:
        emit({"ok": False, "error": exc.title or "api_error",
              "status": exc.status, "detail": exc.detail}, 1)


def run_command(client, args) -> int:
    cmd = args.command
    if cmd == "status":
        biz = client.get("businesses")
        inv = client.get("sales_invoices")
        emit({"ok": True, "connected": True, "demo": isinstance(client, DemoClient),
              "business": biz.get("business") or biz, "sales_invoice_count": inv.get("total")})
    if cmd == "invoices":
        params = {"status": args.status} if args.status else None
        page = client.get("sales_invoices", params=params)
        emit({"ok": True, "invoices": page.get("$items", []), "total": page.get("total")})
    if cmd == "invoice":
        emit({"ok": True, "invoice": client.get(f"sales_invoices/{args.id}")})
    if cmd == "contacts":
        page = client.get("contacts")
        emit({"ok": True, "contacts": page.get("$items", []), "total": page.get("total")})
    if cmd == "overdue":
        page = client.get("sales_invoices")
        items = [i for i in page.get("$items", []) if _is_overdue(i)]
        emit({"ok": True, "overdue": items, "total": len(items),
              "total_outstanding": round(sum(float(i.get("outstanding_amount") or i.get("total_amount") or 0) for i in items), 2)})
    if cmd == "bank-accounts":
        page = client.get("bank_accounts")
        emit({"ok": True, "bank_accounts": page.get("$items", []), "total": page.get("total")})
    if cmd == "chart":
        page = client.get("ledger_accounts")
        emit({"ok": True, "ledger_accounts": page.get("$items", []), "total": page.get("total")})
    if cmd == "create-invoice":
        body = {"sales_invoice": {"contact_id": args.contact_id, "date": _today(),
                "due_date": args.due_date, "status": "draft",
                "invoice_lines": [{"description": args.description, "quantity": 1, "unit_price": args.amount}]}}
        summary = {"action": "create_sales_invoice_draft", "will_create": body["sales_invoice"],
                   "note": "Creates a DRAFT sales invoice only; it is not sent."}
        gate(summary, args.yes)
        if isinstance(client, DemoClient):
            demo_write_result(summary, client.post("sales_invoices", body))
        created = client.post("sales_invoices", body)
        new_id = created.get("id") if isinstance(created, dict) else None
        readback = client.get(f"sales_invoices/{new_id}") if new_id else created
        emit({"ok": True, "created": readback})
    emit({"ok": False, "error": "unknown_command", "detail": cmd}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
