#!/usr/bin/env python3
"""WooCommerce connector CLI for Muse.

Talks to a WooCommerce store through the WooCommerce REST API v3
(``<store>/wp-json/wc/v3/``) and prints clean JSON to stdout.

Credentials NEVER live in files. In live mode the Consumer Key / Secret
pair is obtained through Muse's dynamic-credential surrogate flow
from the registered connection ``custom.woocommerce`` (see
CONNECTOR.md "How the credential flows"). The store's own domain is
read from ``store_config.json`` beside ``connector.yaml`` (or the
``WC_STORE_URL`` environment variable / ``--store-url`` flag); the
installing Muse writes that file and registers the store domain as
an allowed API host on the connection.

Run with ``--demo`` to exercise every read command against the bundled
fictional store in ``demo_data.json`` -- no store, no keys, no license
check. Live (non-demo) commands are gated by ``license_check.py``
(30-day free trial, then an active subscription).

Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check  # noqa: E402  (local module, trial/subscription gate)

CONNECTION_NAME = "custom.woocommerce"
CONNECTOR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(CONNECTOR_ROOT, "store_config.json")
DEMO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_data.json")
DYNAMIC_CREDENTIALS_DIR = "/opt/muse/skills/custom-connector-setup/bin"
PAID_STATUSES = ("completed", "processing")


class CliError(RuntimeError):
    """An error that should be printed as JSON and exit non-zero."""


def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def trim(obj, drop=("_links",)):
    if isinstance(obj, dict):
        return {k: trim(v, drop) for k, v in obj.items() if k not in drop}
    if isinstance(obj, list):
        return [trim(v, drop) for v in obj]
    return obj


def money(value) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# Store configuration (non-secret: just the store's public URL)
# --------------------------------------------------------------------------

def resolve_store_url(cli_value: str | None) -> str:
    url = cli_value or os.environ.get("WC_STORE_URL")
    if not url and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                url = json.load(fh).get("store_url")
        except (OSError, json.JSONDecodeError):
            url = None
    if not url:
        raise CliError(
            "No store URL configured. The installing Muse must write "
            "store_config.json beside connector.yaml (see INSTALL.md), or "
            "pass --store-url https://your-store.example."
        )
    url = url.rstrip("/")
    if not url.startswith("https://"):
        raise CliError("Store URL must start with https:// (WooCommerce API keys "
                       "are only safe over HTTPS).")
    return url


# --------------------------------------------------------------------------
# Live backend: WooCommerce REST API v3 via Muse dynamic credentials
# --------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):  # noqa: D102
        raise CliError("The store redirected an authenticated request; "
                       "check the store URL (www vs non-www) in store_config.json.")


class LiveBackend:
    """WooCommerce REST API v3 client.

    Auth model: the connection ``custom.woocommerce`` holds two API-key
    entries, ``consumer_key`` and ``consumer_secret``, each registered
    with query-parameter placement under its own name. WooCommerce
    accepts the key pair as ``consumer_key`` / ``consumer_secret``
    query parameters over HTTPS. Each value placed in the URL is a
    Muse surrogate (``hsurr:*``); Muse swaps in the real key only
    on an approved request to the registered store host, so the real
    keys never appear in this process, in files, or in logs.
    """

    def __init__(self, store_url: str):
        self.base = store_url + "/wp-json/wc/v3/"
        self.host = urllib.parse.urlparse(store_url).hostname or ""
        try:
            sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
            from dynamic_credentials import (  # noqa: E402
                read_json_response,
                url_with_surrogate_query_param,
            )
        except ImportError as exc:
            raise CliError(
                "Muse's dynamic_credentials helper was not found at "
                f"{DYNAMIC_CREDENTIALS_DIR}. This connector must run inside "
                "Muse; see INSTALL.md."
            ) from exc
        self._read_json = read_json_response
        self._with_param = url_with_surrogate_query_param

    def _url(self, path: str, params: dict | None) -> str:
        url = self.base + path.lstrip("/")
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        for entry in ("consumer_key", "consumer_secret"):
            url = self._with_param(
                url, CONNECTION_NAME, entry_name=entry, allowed_hosts=[self.host]
            )
        return url

    def request(self, method: str, path: str, params: dict | None = None,
                body: dict | None = None):
        url = self._url(path, params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(req, timeout=30) as response:
                return self._read_json(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise CliError(f"WooCommerce returned HTTP {exc.code} for "
                           f"{method} {path}: {detail}") from exc
        except Exception as exc:  # DynamicCredentialError and friends
            if isinstance(exc, CliError):
                raise
            raise CliError(f"Request to the store failed: {exc}") from exc

    def get(self, path, params=None):
        return self.request("GET", path, params)

    def get_all(self, path, params=None, per_page=100, max_pages=5):
        items, page = [], 1
        while page <= max_pages:
            batch = self.get(path, {**(params or {}), "per_page": per_page, "page": page})
            if not isinstance(batch, list) or not batch:
                break
            items.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return items

    # -- operations used by the commands --------------------------------
    def store_status(self):
        currency = self.get("data/currencies/current")
        totals = self.get("reports/orders/totals")
        return {
            "connected": True,
            "store_url": self.base.replace("/wp-json/wc/v3/", ""),
            "currency": currency.get("code") if isinstance(currency, dict) else None,
            "orders_by_status": [
                {"status": t.get("slug"), "count": t.get("total")}
                for t in totals if isinstance(t, dict)
            ] if isinstance(totals, list) else [],
        }

    def sales_totals(self, window):
        report = self.get("reports/sales", {
            "date_min": window["date_min"], "date_max": window["date_max"]})
        row = report[0] if isinstance(report, list) and report else {}
        orders = int(row.get("total_orders") or 0)
        gross = money(row.get("total_sales"))
        return {
            "gross_sales": gross,
            "net_sales": money(row.get("net_sales")),
            "orders": orders,
            "items": int(row.get("total_items") or 0),
            "refunds": money(row.get("total_refunds")),
            "discounts": money(row.get("total_discount")),
            "average_order_value": round(gross / orders, 2) if orders else 0.0,
        }

    def list_orders(self, status=None, days=None, limit=20):
        params = {"per_page": limit, "orderby": "date", "order": "desc"}
        if status and status != "any":
            params["status"] = status
        if days:
            params["after"] = (datetime.now() - timedelta(days=days)).isoformat()
        return self.get("orders", params)

    def get_order(self, order_id):
        return self.get(f"orders/{order_id}")

    def list_refunds(self, days=30):
        after = (datetime.now() - timedelta(days=days)).isoformat()
        refunds = self.get_all("refunds", {"after": after, "orderby": "date",
                                           "order": "desc"})
        return refunds

    def search_products(self, query=None, limit=20):
        params = {"per_page": limit, "status": "publish"}
        if query:
            params["search"] = query
        return self.get("products", params)

    def get_product(self, product_id):
        return self.get(f"products/{product_id}")

    def top_sellers(self, period):
        return self.get("reports/top_sellers", {"period": period})

    def all_products(self):
        return self.get_all("products", {"status": "publish"})

    def list_customers(self, limit=200):
        return self.get_all("customers", {}, per_page=100,
                            max_pages=max(1, limit // 100))

    def list_coupons(self):
        return self.get_all("coupons", {})

    def recent_orders(self, days, cap=1000):
        after = (datetime.now() - timedelta(days=days)).isoformat()
        # No status filter here: the caller filters by status locally,
        # so this does not rely on multi-status query support.
        return self.get_all("orders", {"after": after,
                                       "orderby": "date", "order": "desc"},
                            per_page=100, max_pages=max(1, cap // 100))

    def create_coupon(self, payload):
        return self.request("POST", "coupons", body=payload)

    def update_product(self, product_id, payload):
        return self.request("PUT", f"products/{product_id}", body=payload)


# --------------------------------------------------------------------------
# Demo backend: the same operations against bundled fictional data
# --------------------------------------------------------------------------

class DemoBackend:
    def __init__(self):
        with open(DEMO_PATH, "r", encoding="utf-8") as fh:
            self.data = json.load(fh)

    def _paid_orders(self):
        return [o for o in self.data["orders"] if o["status"] in PAID_STATUSES]

    def store_status(self):
        counts = {}
        for order in self.data["orders"]:
            counts[order["status"]] = counts.get(order["status"], 0) + 1
        store = self.data["store"]
        return {
            "connected": True, "demo": True,
            "store_url": store["url"], "store_name": store["name"],
            "currency": store["currency"],
            "orders_by_status": [{"status": k, "count": v}
                                 for k, v in sorted(counts.items())],
        }

    def sales_totals(self, window):
        lo, hi = window["days_ago_max"], window["days_ago_min"]
        rows = [o for o in self._paid_orders() if lo <= o["days_ago"] <= hi]
        gross = round(sum(money(o["total"]) for o in rows), 2)
        refunded = round(sum(money(r["total"]) for r in self.data["refunds"]
                             if lo <= r["days_ago"] <= hi), 2)
        return {
            "gross_sales": gross,
            "net_sales": round(gross - refunded, 2),
            "orders": len(rows),
            "items": sum(i["quantity"] for o in rows for i in o["line_items"]),
            "refunds": refunded,
            "discounts": 0.0,
            "average_order_value": round(gross / len(rows), 2) if rows else 0.0,
        }

    def list_orders(self, status=None, days=None, limit=20):
        rows = self.data["orders"]
        if status and status != "any":
            rows = [o for o in rows if o["status"] == status]
        if days:
            rows = [o for o in rows if o["days_ago"] <= days]
        return sorted(rows, key=lambda o: o["days_ago"])[:limit]

    def get_order(self, order_id):
        for order in self.data["orders"]:
            if order["id"] == int(order_id):
                return order
        raise CliError(f"Demo store has no order {order_id}.")

    def list_refunds(self, days=30):
        return [r for r in self.data["refunds"] if r["days_ago"] <= days]

    def search_products(self, query=None, limit=20):
        rows = self.data["products"]
        if query:
            q = query.lower()
            rows = [p for p in rows if q in p["name"].lower() or q in p["sku"].lower()]
        return rows[:limit]

    def get_product(self, product_id):
        for product in self.data["products"]:
            if product["id"] == int(product_id):
                return product
        raise CliError(f"Demo store has no product {product_id}.")

    def top_sellers(self, period):
        days = {"week": 7, "month": 30, "last_month": 60, "year": 365}[period]
        tally = {}
        for order in self._paid_orders():
            if order["days_ago"] >= days:
                continue
            for item in order["line_items"]:
                row = tally.setdefault(item["product_id"], {
                    "product_id": item["product_id"], "title": item["name"], "quantity": 0})
                row["quantity"] += item["quantity"]
        return sorted(tally.values(), key=lambda r: -r["quantity"])

    def all_products(self):
        return list(self.data["products"])

    def list_customers(self, limit=200):
        return self.data["customers"][:limit]

    def list_coupons(self):
        return list(self.data["coupons"])

    def recent_orders(self, days, cap=1000):
        return [o for o in self._paid_orders() if o["days_ago"] <= days][:cap]

    def create_coupon(self, payload):
        return {"id": 399, "simulated": True, **payload}

    def update_product(self, product_id, payload):
        product = dict(self.get_product(product_id))
        product.update(payload)
        product["simulated"] = True
        return product


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def window_for(days_ago_min: int, days_ago_max: int) -> dict:
    today = date.today()
    return {
        "date_min": (today - timedelta(days=days_ago_min)).isoformat(),
        "date_max": (today - timedelta(days=days_ago_max)).isoformat(),
        "days_ago_min": days_ago_min,
        "days_ago_max": days_ago_max,
    }


def cmd_status(backend, _args):
    emit({"ok": True, **backend.store_status()})


def cmd_snapshot(backend, _args):
    periods = {
        "today": window_for(0, 0),
        "yesterday": window_for(1, 1),
        "last_7_days": window_for(6, 0),
    }
    emit({"ok": True, "snapshot": {
        name: backend.sales_totals(window) for name, window in periods.items()}})


def order_summary(order):
    return {
        "id": order.get("id"), "number": order.get("number"),
        "status": order.get("status"), "total": order.get("total"),
        "currency": order.get("currency"), "customer_id": order.get("customer_id"),
        "date_created": order.get("date_created"),
        "items": [{"name": i.get("name"), "quantity": i.get("quantity"),
                   "total": i.get("total")} for i in order.get("line_items", [])],
    }


def cmd_orders(backend, args):
    rows = backend.list_orders(status=args.status, days=args.days, limit=args.limit)
    emit({"ok": True, "count": len(rows),
          "orders": [order_summary(o) for o in rows]})


def cmd_order(backend, args):
    emit({"ok": True, "order": trim(backend.get_order(args.id))})


def cmd_refunds(backend, args):
    rows = backend.list_refunds(days=args.days)
    total = round(sum(abs(money(r.get("total"))) for r in rows), 2)
    emit({"ok": True, "period_days": args.days, "refund_count": len(rows),
          "refund_total": total,
          "refunds": [{"id": r.get("id"), "order_id": r.get("order_id"),
                       "total": abs(money(r.get("total"))),
                       "reason": r.get("reason"),
                       "date_created": r.get("date_created")} for r in rows]})


def product_summary(product):
    return {
        "id": product.get("id"), "name": product.get("name"),
        "sku": product.get("sku"), "price": product.get("price"),
        "regular_price": product.get("regular_price"),
        "stock_quantity": product.get("stock_quantity"),
        "low_stock_amount": product.get("low_stock_amount"),
        "stock_status": product.get("stock_status"),
        "status": product.get("status"), "total_sales": product.get("total_sales"),
    }


def cmd_products(backend, args):
    rows = backend.search_products(query=args.search, limit=args.limit)
    emit({"ok": True, "count": len(rows),
          "products": [product_summary(p) for p in rows]})


def cmd_product(backend, args):
    emit({"ok": True, "product": trim(backend.get_product(args.id))})


def cmd_best_sellers(backend, args):
    period = "week" if args.days <= 7 else "month" if args.days <= 31 else "year"
    rows = backend.top_sellers(period)
    emit({"ok": True, "period": period,
          "best_sellers": [{"product_id": r.get("product_id"),
                            "title": r.get("title"),
                            "quantity_sold": r.get("quantity")} for r in rows]})


def cmd_inventory(backend, args):
    low = []
    for product in backend.all_products():
        if not product.get("manage_stock"):
            continue
        qty = product.get("stock_quantity")
        if qty is None:
            continue
        threshold = product.get("low_stock_amount")
        if threshold in (None, "", 0):
            threshold = args.threshold
        if qty <= threshold:
            low.append({**product_summary(product), "threshold_used": threshold})
    low.sort(key=lambda p: p["stock_quantity"])
    emit({"ok": True, "low_stock_count": len(low), "low_stock": low,
          "note": "Threshold is each product's WooCommerce low-stock amount "
                  "when set, otherwise the --threshold value."})


def customer_summary(customer):
    return {
        "id": customer.get("id"),
        "name": " ".join(x for x in [customer.get("first_name"),
                                     customer.get("last_name")] if x),
        "email": customer.get("email"),
        "orders_count": customer.get("orders_count"),
        "total_spent": customer.get("total_spent"),
    }


def cmd_customers(backend, args):
    rows = backend.list_customers()
    key = (lambda c: money(c.get("total_spent"))) if args.sort == "spent" \
        else (lambda c: int(c.get("orders_count") or 0))
    rows = sorted(rows, key=key, reverse=True)[:args.limit]
    emit({"ok": True, "count": len(rows),
          "customers": [customer_summary(c) for c in rows]})


def cmd_lapsed(backend, args):
    orders = [o for o in backend.recent_orders(args.scan_days)
              if o.get("status") in PAID_STATUSES]
    last_order: dict[int, str] = {}
    for order in orders:
        cid = order.get("customer_id") or 0
        created = order.get("date_created") or ""
        if cid and created > last_order.get(cid, ""):
            last_order[cid] = created
    cutoff = (datetime.now() - timedelta(days=args.days)).isoformat()
    lapsed = []
    for customer in backend.list_customers():
        cid = customer.get("id")
        last = last_order.get(cid)
        if last is None or last < cutoff:
            lapsed.append({**customer_summary(customer), "last_order": last})
    emit({
        "ok": True, "approximate": True,
        "method": f"Scanned {len(orders)} paid orders from the last "
                  f"{args.scan_days} days; a customer counts as lapsed when "
                  f"their most recent order in that window is older than "
                  f"{args.days} days or absent from it. Guest checkouts are "
                  "not tracked. Treat this list as approximate.",
        "lapsed_count": len(lapsed), "lapsed_customers": lapsed,
    })


def cmd_coupons(backend, _args):
    rows = backend.list_coupons()
    emit({"ok": True, "count": len(rows), "coupons": [
        {"id": c.get("id"), "code": c.get("code"), "amount": c.get("amount"),
         "discount_type": c.get("discount_type"),
         "usage_count": c.get("usage_count"),
         "date_expires": c.get("date_expires"),
         "description": c.get("description")} for c in rows]})


# -- write commands: approval-gated --------------------------------------
# Every write prints the BEFORE state and the exact proposed change as
# JSON and exits 2 unless --yes is passed. The calling Muse must show
# that summary to the store owner and only re-run with --yes after the
# owner approves. Nothing here writes silently.

def _gate(action, before, after, args, perform):
    if not args.yes:
        emit({"ok": False, "approval_required": True, "action": action,
              "before": before, "proposed_change": after,
              "message": "Write not performed. Show this summary to the store "
                         "owner; re-run the same command with --yes only "
                         "after they approve."}, exit_code=2)
    result = perform()
    emit({"ok": True, "action": action, "before": before,
          "result": trim(result)})


def cmd_create_coupon(backend, args):
    payload = {"code": args.code, "amount": str(args.amount),
               "discount_type": args.type}
    if args.description:
        payload["description"] = args.description
    if args.expiry:
        payload["date_expires"] = args.expiry + "T23:59:59"
    _gate("create_coupon", None, payload, args,
          lambda: backend.create_coupon(payload))


def cmd_set_price(backend, args):
    current = product_summary(backend.get_product(args.id))
    payload = {"regular_price": str(args.price)}
    if args.sale_price is not None:
        payload["sale_price"] = str(args.sale_price)
    _gate("set_price", current, {"id": args.id, **payload}, args,
          lambda: backend.update_product(args.id, payload))


def cmd_set_stock(backend, args):
    current = product_summary(backend.get_product(args.id))
    payload = {"manage_stock": True, "stock_quantity": args.quantity}
    _gate("set_stock", current, {"id": args.id, **payload}, args,
          lambda: backend.update_product(args.id, payload))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    # SUPPRESS defaults: without them, a subparser's defaults would
    # overwrite --demo / --store-url given before the subcommand.
    common.add_argument("--demo", action="store_true", default=argparse.SUPPRESS,
                        help="Run against the bundled fictional demo store.")
    common.add_argument("--store-url", default=argparse.SUPPRESS,
                        help="Store base URL (overrides store_config.json).")
    parser = argparse.ArgumentParser(
        prog="woo.py", parents=[common],
        description="WooCommerce connector CLI for Muse. Prints JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", parents=[common],
                   help="Verify the connection and show store info.")
    sub.add_parser("snapshot", parents=[common],
                   help="Revenue/orders/AOV: today vs yesterday vs last 7 days.")
    p = sub.add_parser("orders", parents=[common], help="List recent orders.")
    p.add_argument("--status", default=None,
                   help="WooCommerce order status, e.g. processing, completed.")
    p.add_argument("--days", type=int, default=None,
                   help="Only orders from the last N days.")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("order", parents=[common], help="Show one order.")
    p.add_argument("id", type=int)
    p = sub.add_parser("refunds", parents=[common], help="Refund totals for a period.")
    p.add_argument("--days", type=int, default=30)
    p = sub.add_parser("products", parents=[common], help="Search products.")
    p.add_argument("--search", default=None)
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("product", parents=[common], help="Show one product.")
    p.add_argument("id", type=int)
    p = sub.add_parser("best-sellers", parents=[common],
                       help="Top sellers from the WooCommerce reports API.")
    p.add_argument("--days", type=int, default=30,
                   help="7 = week report, 30 = month report, more = year report.")
    p = sub.add_parser("inventory", parents=[common],
                       help="Low-stock list.")
    p.add_argument("--threshold", type=int, default=5,
                   help="Fallback low-stock threshold when a product has none set.")
    p = sub.add_parser("customers", parents=[common], help="List/top customers.")
    p.add_argument("--sort", choices=["spent", "orders"], default="spent")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("lapsed", parents=[common],
                       help="Customers with no recent order (approximate).")
    p.add_argument("--days", type=int, default=90,
                   help="No order in this many days counts as lapsed.")
    p.add_argument("--scan-days", type=int, default=180,
                   help="How far back to scan orders.")
    sub.add_parser("coupons", parents=[common], help="List coupons.")
    p = sub.add_parser("create-coupon", parents=[common],
                       help="Create a coupon (approval-gated write).")
    p.add_argument("--code", required=True)
    p.add_argument("--amount", required=True)
    p.add_argument("--type", default="percent",
                   choices=["percent", "fixed_cart", "fixed_product"])
    p.add_argument("--description", default=None)
    p.add_argument("--expiry", default=None, help="YYYY-MM-DD")
    p.add_argument("--yes", action="store_true",
                   help="Confirm the owner approved this write.")
    p = sub.add_parser("set-price", parents=[common],
                       help="Change a product price (approval-gated write).")
    p.add_argument("id", type=int)
    p.add_argument("--price", required=True)
    p.add_argument("--sale-price", default=None)
    p.add_argument("--yes", action="store_true")
    p = sub.add_parser("set-stock", parents=[common],
                       help="Set a product stock quantity (approval-gated write).")
    p.add_argument("id", type=int)
    p.add_argument("--quantity", type=int, required=True)
    p.add_argument("--yes", action="store_true")
    return parser


COMMANDS = {
    "status": cmd_status, "snapshot": cmd_snapshot, "orders": cmd_orders,
    "order": cmd_order, "refunds": cmd_refunds, "products": cmd_products,
    "product": cmd_product, "best-sellers": cmd_best_sellers,
    "inventory": cmd_inventory, "customers": cmd_customers,
    "lapsed": cmd_lapsed, "coupons": cmd_coupons,
    "create-coupon": cmd_create_coupon, "set-price": cmd_set_price,
    "set-stock": cmd_set_stock,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if getattr(args, "demo", False):
            backend = DemoBackend()
        else:
            store_url = resolve_store_url(getattr(args, "store_url", None))
            # Pass the store URL as the shop identity so the license
            # check can hash it locally for server activation/binding.
            # The raw URL never leaves this machine (hash only).
            license_check.enforce(shop_identity=store_url)
            backend = LiveBackend(store_url)
        COMMANDS[args.command](backend, args)
    except CliError as exc:
        emit({"ok": False, "error": str(exc)}, exit_code=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
