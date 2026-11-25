#!/usr/bin/env python3
"""Etsy connector CLI for Muse (connection name: custom.etsy).

Reads and approval-gated writes against a seller's Etsy shop through the
Etsy Open API v3. Prints clean JSON to stdout. Runs entirely on the user's
own Muse: no Etsy data is stored or sent anywhere by this helper.

Credentials never live in this file or any file. In live mode the helper
asks Muse's secure connection flow (dynamic_credentials) for surrogates:

- entry `access_token` in connection `custom.etsy`, placed as a bearer
  Authorization header (the seller's OAuth 2.0 token), and
- entry `api_key` in the same connection, placed as the `x-api-key` header
  (the registered Etsy app keystring).

Etsy requires BOTH on every call to a scoped endpoint.

APP_KEYSTRING below is the publisher's Etsy app keystring. An Etsy keystring
is the app's OAuth client_id: it appears in every authorization URL and is
public by design, which is why it may ship inside the connector. The app's
shared secret is never used by this connector (public-client PKCE flow) and
must never be placed here. For testing, --api-key or a filled APP_KEYSTRING
supplies a bring-your-own keystring instead of the connection entry.

Demo mode (--demo anywhere on the command line) runs every read command,
and simulated writes, against bin/demo_data.json, a fictional shop. Demo
mode needs no credentials and skips the license check.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import license_check  # noqa: E402

CONNECTION_NAME = "custom.etsy"
API_BASE = "https://openapi.etsy.com/v3"
API_HOSTS = ["openapi.etsy.com"]

# Publisher: fill in the registered Etsy app keystring before public launch,
# or leave empty and let the registered connection supply the api_key entry.
APP_KEYSTRING = ""

STATE_DIR = Path(
    os.environ.get(
        "ETSY_CONNECTOR_STATE_DIR", Path.home() / ".cache" / "custom-etsy"
    )
)
SHOP_STATE_FILE = STATE_DIR / "shop.json"
DEMO_DATA_FILE = Path(__file__).resolve().parent / "demo_data.json"


class EtsyError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def money_value(money) -> float | None:
    if not isinstance(money, dict):
        return None
    amount = money.get("amount")
    divisor = money.get("divisor") or 100
    if amount is None:
        return None
    return round(amount / divisor, 2)


def norm_money(money):
    if not isinstance(money, dict):
        return None
    return {
        "value": money_value(money),
        "currency_code": money.get("currency_code"),
    }


def local_midnight_ts(days_ago: int = 0) -> int:
    now = datetime.now().astimezone()
    midnight = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    return int(midnight.timestamp()) - days_ago * 86400


def ts_to_local_date(ts: int) -> str:
    return datetime.fromtimestamp(ts).astimezone().date().isoformat()


# --------------------------------------------------------------------------
# Demo client: same return shapes as the live API, from fictional data
# --------------------------------------------------------------------------

class DemoClient:
    mode = "demo"

    def __init__(self):
        raw = json.loads(DEMO_DATA_FILE.read_text(encoding="utf-8"))
        self.shop = raw["shop"]
        self.listings = raw["listings"]
        self.inventories = {
            int(k): v for k, v in raw["inventories"].items()
        }
        self.receipts = [self._materialize(r) for r in raw["receipts"]]
        self.reviews = [self._materialize(r) for r in raw["reviews"]]
        self.ledger = [self._materialize(e) for e in raw["ledger_entries"]]
        self.receipts.sort(key=lambda r: -r["created_timestamp"])
        self.reviews.sort(key=lambda r: -r["created_timestamp"])
        self.ledger.sort(key=lambda e: -e["created_timestamp"])

    @staticmethod
    def _materialize(record):
        record = dict(record)
        days = record.pop("created_days_ago", 0)
        hour = record.pop("created_hour", 10)
        record["created_timestamp"] = local_midnight_ts(days) + hour * 3600
        return record

    def get_shop(self):
        return copy.deepcopy(self.shop)

    def get_receipts(self, min_ts=None, max_ts=None, extra_params=None):
        out = []
        for r in self.receipts:
            if min_ts and r["created_timestamp"] < min_ts:
                continue
            if max_ts and r["created_timestamp"] > max_ts:
                continue
            out.append(copy.deepcopy(r))
        return out, False

    def get_receipt(self, receipt_id):
        for r in self.receipts:
            if r["receipt_id"] == receipt_id:
                return copy.deepcopy(r)
        raise EtsyError("not_found", f"No demo receipt with id {receipt_id}.")

    def get_active_listings(self, keywords=None, limit=25):
        out = []
        for listing in self.listings:
            if listing["state"] != "active":
                continue
            if keywords:
                haystack = (
                    listing["title"] + " " + " ".join(listing.get("tags", []))
                ).lower()
                if keywords.lower() not in haystack:
                    continue
            out.append(copy.deepcopy(listing))
        return out[:limit]

    def get_listing(self, listing_id):
        for listing in self.listings:
            if listing["listing_id"] == listing_id:
                return copy.deepcopy(listing)
        raise EtsyError("not_found", f"No demo listing with id {listing_id}.")

    def get_inventory(self, listing_id):
        inv = self.inventories.get(listing_id)
        if inv is None:
            raise EtsyError(
                "not_found", f"No demo inventory for listing {listing_id}."
            )
        return copy.deepcopy(inv)

    def update_inventory(self, listing_id, payload):
        self.inventories[listing_id] = copy.deepcopy(payload)
        return self.get_inventory(listing_id)

    def get_reviews(self, limit=10):
        return copy.deepcopy(self.reviews[:limit]), self.shop.get(
            "review_count", len(self.reviews)
        )

    def get_ledger(self, min_ts=None, max_ts=None, limit=20):
        out = []
        for entry in self.ledger:
            if min_ts and entry["created_timestamp"] < min_ts:
                continue
            if max_ts and entry["created_timestamp"] > max_ts:
                continue
            out.append(copy.deepcopy(entry))
        return out[:limit]


# --------------------------------------------------------------------------
# Live client: Etsy Open API v3 through Muse's secure connection flow
# --------------------------------------------------------------------------

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


class LiveClient:
    mode = "live"

    def __init__(self, shop_id=None, api_key_override=None):
        self._shop_id = shop_id
        self._api_key_override = api_key_override

    # -- credential and transport ------------------------------------------

    def _request(self, method, path, params=None, body=None):
        url = API_BASE + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url += "?" + urllib.parse.urlencode(clean)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )
        try:
            sys.path.insert(
                0, "/opt/muse/skills/custom-connector-setup/bin"
            )
            from dynamic_credentials import add_surrogate_to_request
        except Exception as exc:
            raise EtsyError(
                "credentials_unavailable",
                "Muse's dynamic credential helper is not available. "
                "Install this connector through Muse so the secure "
                "connection flow can supply credentials.",
            ) from exc
        try:
            add_surrogate_to_request(
                request,
                CONNECTION_NAME,
                entry_name="access_token",
                allowed_hosts=API_HOSTS,
            )
            if self._api_key_override:
                request.add_header("x-api-key", self._api_key_override)
            elif APP_KEYSTRING:
                request.add_header("x-api-key", APP_KEYSTRING)
            else:
                add_surrogate_to_request(
                    request,
                    CONNECTION_NAME,
                    entry_name="api_key",
                    allowed_hosts=API_HOSTS,
                )
        except Exception as exc:
            raise EtsyError(
                "credentials_unavailable",
                "Could not load the Etsy credential from connection "
                f"{CONNECTION_NAME}. Reconnect Etsy in Muse, then retry. "
                f"Detail: {exc}",
            ) from exc
        try:
            opener = urllib.request.build_opener(NoRedirect())
            with opener.open(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except Exception:
                pass
            raise EtsyError(
                "etsy_api_error",
                f"Etsy API returned HTTP {exc.code} for {method} {path}: "
                f"{detail}",
            ) from exc
        except Exception as exc:
            raise EtsyError(
                "request_failed", f"Etsy request failed: {exc}"
            ) from exc

    def _get_paged(self, path, params, want, page_size=100, max_pages=10):
        results = []
        offset = 0
        truncated = False
        for _ in range(max_pages):
            page_params = dict(params or {})
            page_params.update({"limit": page_size, "offset": offset})
            payload = self._request("GET", path, params=page_params)
            batch = payload.get("results", [])
            results.extend(batch)
            offset += len(batch)
            if len(batch) < page_size or len(results) >= want:
                break
        else:
            truncated = True
        return results[:want] if want else results, truncated

    # -- shop resolution ----------------------------------------------------

    def shop_id(self):
        if self._shop_id:
            return self._shop_id
        env_shop = os.environ.get("ETSY_SHOP_ID", "").strip()
        if env_shop:
            self._shop_id = int(env_shop)
            return self._shop_id
        try:
            saved = json.loads(SHOP_STATE_FILE.read_text(encoding="utf-8"))
            if saved.get("shop_id"):
                self._shop_id = int(saved["shop_id"])
                return self._shop_id
        except Exception:
            pass
        me = self._request("GET", "/application/users/me")
        user_id = me.get("user_id")
        if not user_id:
            raise EtsyError(
                "shop_unresolved",
                "Etsy did not return a user id for this connection. Set "
                "the shop once with: etsy.py configure --shop-id <id>",
            )
        shops = self._request(
            "GET", f"/application/users/{user_id}/shops"
        ).get("results", [])
        if not shops:
            raise EtsyError(
                "shop_unresolved",
                "This Etsy account has no shop. Open a shop on Etsy first, "
                "or set the shop with: etsy.py configure --shop-id <id>",
            )
        self._shop_id = int(shops[0]["shop_id"])
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        SHOP_STATE_FILE.write_text(
            json.dumps({"shop_id": self._shop_id, "user_id": user_id}),
            encoding="utf-8",
        )
        return self._shop_id

    # -- endpoints ----------------------------------------------------------

    def get_shop(self):
        return self._request(
            "GET", f"/application/shops/{self.shop_id()}"
        )

    def get_receipts(self, min_ts=None, max_ts=None, extra_params=None):
        params = {
            "min_created": min_ts,
            "max_created": max_ts,
            "sort_on": "created",
            "sort_order": "desc",
        }
        if extra_params:
            params.update(extra_params)
        return self._get_paged(
            f"/application/shops/{self.shop_id()}/receipts",
            params,
            want=1000,
        )

    def get_receipt(self, receipt_id):
        return self._request(
            "GET",
            f"/application/shops/{self.shop_id()}/receipts/{receipt_id}",
        )

    def get_active_listings(self, keywords=None, limit=25):
        results, _ = self._get_paged(
            f"/application/shops/{self.shop_id()}/listings/active",
            {"keywords": keywords, "sort_on": "created", "sort_order": "desc"},
            want=limit,
        )
        return results

    def get_listing(self, listing_id):
        return self._request("GET", f"/application/listings/{listing_id}")

    def get_inventory(self, listing_id):
        return self._request(
            "GET", f"/application/listings/{listing_id}/inventory"
        )

    def update_inventory(self, listing_id, payload):
        return self._request(
            "PUT", f"/application/listings/{listing_id}/inventory", body=payload
        )

    def get_reviews(self, limit=10):
        payload = self._request(
            "GET",
            f"/application/shops/{self.shop_id()}/reviews",
            params={"limit": min(limit, 100), "offset": 0},
        )
        return payload.get("results", []), payload.get("count", 0)

    def get_ledger(self, min_ts=None, max_ts=None, limit=20):
        payload = self._request(
            "GET",
            f"/application/shops/{self.shop_id()}"
            "/payment-account/ledger-entries",
            params={
                "min_created": min_ts,
                "max_created": max_ts,
                "limit": min(limit, 100),
                "offset": 0,
            },
        )
        return payload.get("results", [])


# --------------------------------------------------------------------------
# Output normalizers (accept raw Etsy shapes from either client)
# --------------------------------------------------------------------------

def norm_shop(shop):
    return {
        "shop_id": shop.get("shop_id"),
        "shop_name": shop.get("shop_name"),
        "title": shop.get("title"),
        "url": shop.get("url"),
        "currency_code": shop.get("currency_code"),
        "listing_active_count": shop.get("listing_active_count"),
        "review_average": shop.get("review_average"),
        "review_count": shop.get("review_count"),
        "is_vacation": shop.get("is_vacation"),
        "accepts_custom_requests": shop.get("accepts_custom_requests"),
        "announcement": shop.get("announcement"),
    }


def norm_receipt(receipt):
    transactions = []
    items = 0
    for txn in receipt.get("transactions", []):
        qty = txn.get("quantity") or 0
        items += qty
        transactions.append(
            {
                "transaction_id": txn.get("transaction_id"),
                "listing_id": txn.get("listing_id"),
                "title": txn.get("title"),
                "sku": txn.get("sku"),
                "quantity": qty,
                "price": norm_money(txn.get("price")),
            }
        )
    return {
        "receipt_id": receipt.get("receipt_id"),
        "status": receipt.get("status"),
        "is_paid": receipt.get("is_paid"),
        "is_shipped": receipt.get("is_shipped"),
        "is_delivered": receipt.get("is_delivered"),
        "created_timestamp": receipt.get("created_timestamp"),
        "date": ts_to_local_date(receipt["created_timestamp"])
        if receipt.get("created_timestamp")
        else None,
        "buyer_name": receipt.get("name"),
        "buyer_email": receipt.get("buyer_email"),
        "ship_to": {
            "city": receipt.get("city"),
            "state": receipt.get("state"),
            "country_iso": receipt.get("country_iso"),
            "zip": receipt.get("zip"),
        },
        "items_count": items,
        "subtotal": norm_money(receipt.get("subtotal")),
        "shipping": norm_money(receipt.get("total_shipping_cost")),
        "tax": norm_money(receipt.get("total_tax_cost")),
        "grandtotal": norm_money(receipt.get("grandtotal")),
        "message_from_buyer": receipt.get("message_from_buyer") or None,
        "transactions": transactions,
    }


def norm_listing(listing):
    return {
        "listing_id": listing.get("listing_id"),
        "title": listing.get("title"),
        "state": listing.get("state"),
        "price": norm_money(listing.get("price")),
        "quantity": listing.get("quantity"),
        "sku": listing.get("sku"),
        "url": listing.get("url"),
        "views": listing.get("views"),
        "num_favorers": listing.get("num_favorers"),
        "tags": listing.get("tags"),
        "is_customizable": listing.get("is_customizable"),
    }


def inventory_rows(listing_id, title, inventory):
    rows = []
    for product in inventory.get("products", []):
        if product.get("is_deleted"):
            continue
        variant = None
        prop_values = product.get("property_values") or []
        if prop_values:
            parts = []
            for pv in prop_values:
                values = ", ".join(pv.get("values") or [])
                parts.append(f"{pv.get('property_name')}: {values}")
            variant = "; ".join(parts)
        for offering in product.get("offerings", []):
            if offering.get("is_deleted"):
                continue
            rows.append(
                {
                    "listing_id": listing_id,
                    "listing_title": title,
                    "product_id": product.get("product_id"),
                    "sku": product.get("sku"),
                    "variant": variant,
                    "offering_id": offering.get("offering_id"),
                    "price": norm_money(offering.get("price")),
                    "quantity": offering.get("quantity"),
                    "is_enabled": offering.get("is_enabled"),
                }
            )
    return rows


def norm_review(review):
    return {
        "rating": review.get("rating"),
        "review": review.get("review"),
        "listing_id": review.get("listing_id"),
        "transaction_id": review.get("transaction_id"),
        "buyer_user_id": review.get("buyer_user_id"),
        "created_timestamp": review.get("created_timestamp"),
        "date": ts_to_local_date(review["created_timestamp"])
        if review.get("created_timestamp")
        else None,
    }


def norm_ledger_entry(entry):
    return {
        "entry_id": entry.get("entry_id"),
        "entry_type": entry.get("entry_type"),
        "description": entry.get("description"),
        "amount": norm_money(entry.get("amount")),
        "balance": norm_money(entry.get("balance")),
        "reference_type": entry.get("reference_type"),
        "reference_id": entry.get("reference_id"),
        "created_timestamp": entry.get("created_timestamp"),
        "date": ts_to_local_date(entry["created_timestamp"])
        if entry.get("created_timestamp")
        else None,
    }


def receipt_matches_status(receipt, status):
    if status == "all":
        return True
    if status == "unpaid":
        return not receipt.get("is_paid")
    if status == "paid":
        return bool(receipt.get("is_paid"))
    if status == "shipped":
        return bool(receipt.get("is_shipped"))
    if status == "delivered":
        return bool(receipt.get("is_delivered"))
    if status == "unshipped":
        return bool(receipt.get("is_paid")) and not receipt.get("is_shipped")
    return True


# --------------------------------------------------------------------------
# Read commands
# --------------------------------------------------------------------------

def cmd_status(client, args):
    shop = client.get_shop()
    out = {"ok": True, "mode": client.mode, "shop": norm_shop(shop)}
    if client.mode == "demo":
        out["demo_notice"] = (
            "Fictional demo shop. Connect a real shop to see live data."
        )
    return out


def cmd_snapshot(client, args):
    start_ts = local_midnight_ts(6)
    receipts, truncated = client.get_receipts(min_ts=start_ts)
    today = datetime.now().astimezone().date()
    buckets = {
        "today": today.isoformat(),
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "last_7_days": None,
    }
    totals = {
        key: {"orders": 0, "items": 0, "gross_sales": 0.0}
        for key in buckets
    }
    currency = None
    for receipt in receipts:
        if not receipt.get("is_paid"):
            continue
        grand = receipt.get("grandtotal") or {}
        value = money_value(grand) or 0.0
        currency = currency or grand.get("currency_code")
        items = sum(
            (t.get("quantity") or 0) for t in receipt.get("transactions", [])
        )
        day = ts_to_local_date(receipt["created_timestamp"])
        for key, bucket_day in buckets.items():
            if bucket_day is None or bucket_day == day:
                totals[key]["orders"] += 1
                totals[key]["items"] += items
                totals[key]["gross_sales"] = round(
                    totals[key]["gross_sales"] + value, 2
                )
    for key in totals:
        totals[key]["currency_code"] = currency
    return {
        "ok": True,
        "mode": client.mode,
        "snapshot": totals,
        "method": (
            "Aggregated client-side from shop receipts: every receipt in "
            "the last 7 days with is_paid=true, bucketed by local calendar "
            "date, summing each receipt grandtotal (items and shipping and "
            "tax included, exactly as Etsy charged the buyer). Unpaid "
            "receipts are excluded. Fees and refunds are not netted out; "
            "see the ledger command for Etsy's own accounting."
        ),
        "receipts_scanned": len(receipts),
        "truncated": truncated,
    }


def cmd_orders(client, args):
    min_ts = local_midnight_ts(args.days - 1)
    extra = {}
    if client.mode == "live":
        mapping = {
            "unpaid": {"was_paid": "false"},
            "paid": {"was_paid": "true"},
            "shipped": {"was_shipped": "true"},
            "delivered": {"was_delivered": "true"},
            "unshipped": {"was_paid": "true", "was_shipped": "false"},
        }
        extra = mapping.get(args.status, {})
    receipts, truncated = client.get_receipts(
        min_ts=min_ts, extra_params=extra
    )
    matched = [
        r for r in receipts if receipt_matches_status(r, args.status)
    ]
    return {
        "ok": True,
        "mode": client.mode,
        "status_filter": args.status,
        "days": args.days,
        "count": min(len(matched), args.limit),
        "total_matched": len(matched),
        "truncated": truncated,
        "orders": [norm_receipt(r) for r in matched[: args.limit]],
    }


def cmd_order(client, args):
    receipt = client.get_receipt(args.receipt_id)
    return {"ok": True, "mode": client.mode, "order": norm_receipt(receipt)}


def cmd_listings(client, args):
    listings = client.get_active_listings(
        keywords=args.search, limit=args.limit
    )
    return {
        "ok": True,
        "mode": client.mode,
        "search": args.search,
        "count": len(listings),
        "listings": [norm_listing(l) for l in listings],
    }


def cmd_listing(client, args):
    listing = client.get_listing(args.listing_id)
    out = norm_listing(listing)
    out["description"] = listing.get("description")
    out["materials"] = listing.get("materials")
    return {"ok": True, "mode": client.mode, "listing": out}


def cmd_inventory(client, args):
    rows = []
    if args.listing_id:
        targets = [client.get_listing(args.listing_id)]
    else:
        targets = client.get_active_listings(limit=args.max_listings)
    for listing in targets:
        inv = client.get_inventory(listing["listing_id"])
        rows.extend(
            inventory_rows(
                listing["listing_id"], listing.get("title"), inv
            )
        )
    low_only = args.threshold is not None
    if low_only:
        rows = [
            r for r in rows if (r["quantity"] or 0) <= args.threshold
        ]
    return {
        "ok": True,
        "mode": client.mode,
        "low_stock_only": low_only,
        "threshold": args.threshold,
        "count": len(rows),
        "inventory": rows,
    }


def cmd_reviews(client, args):
    reviews, total = client.get_reviews(limit=args.limit)
    ratings = [r["rating"] for r in reviews if r.get("rating")]
    average = round(sum(ratings) / len(ratings), 2) if ratings else None
    shop_average = None
    try:
        shop_average = client.get_shop().get("review_average")
    except EtsyError:
        pass
    return {
        "ok": True,
        "mode": client.mode,
        "count": len(reviews),
        "total_reviews_on_shop": total,
        "average_of_returned": average,
        "shop_review_average": shop_average,
        "reviews": [norm_review(r) for r in reviews],
    }


def cmd_ledger(client, args):
    min_ts = local_midnight_ts(args.days - 1)
    entries = client.get_ledger(min_ts=min_ts, limit=args.limit)
    return {
        "ok": True,
        "mode": client.mode,
        "days": args.days,
        "count": len(entries),
        "entries": [norm_ledger_entry(e) for e in entries],
    }


# --------------------------------------------------------------------------
# Write commands: approval-gated, BEFORE summary first, --yes to apply
# --------------------------------------------------------------------------

def _select_offerings(inventory, product_id, offering_id):
    """Return (targets, all_rows) where targets are (product, offering)."""
    targets = []
    total = 0
    for product in inventory.get("products", []):
        if product.get("is_deleted"):
            continue
        for offering in product.get("offerings", []):
            if offering.get("is_deleted"):
                continue
            total += 1
            if product_id and product.get("product_id") != product_id:
                continue
            if offering_id and offering.get("offering_id") != offering_id:
                continue
            targets.append((product, offering))
    return targets, total


def _require_unambiguous(targets, total, selector_given, listing_id, noun):
    if targets:
        return
    raise EtsyError(
        "target_not_found",
        f"No offering matched the given product or offering id on "
        f"listing {listing_id}. Run the inventory command to see the "
        "product_id and offering_id values.",
    )


def _guard_multiple(targets, total, selector_given, listing_id):
    if len(targets) > 1 and not selector_given:
        ids = [o.get("offering_id") for _, o in targets]
        raise EtsyError(
            "ambiguous_target",
            f"Listing {listing_id} has {total} offerings. Changing all of "
            "them at once is refused. Re-run with --offering-id choosing "
            f"one of {ids}, or --product-id for one variant.",
        )


def _write_gate(args, action, listing_id, before_rows, changes):
    plan = {
        "ok": True,
        "mode": args._client.mode,
        "action": action,
        "listing_id": listing_id,
        "before": before_rows,
        "planned_changes": changes,
    }
    if not args.yes:
        plan["approval_required"] = True
        plan["instruction"] = (
            "Nothing was changed. Show this BEFORE summary and the planned "
            "change to the shop owner. Only when the owner approves, re-run "
            "the same command with --yes."
        )
        return plan
    return None


def cmd_set_price(client, args):
    args._client = client
    listing = client.get_listing(args.listing_id)
    inventory = client.get_inventory(args.listing_id)
    try:
        new_price = Decimal(args.price)
    except InvalidOperation:
        raise EtsyError(
            "bad_price", f"Price '{args.price}' is not a number like 24.50."
        )
    selector = args.product_id is not None or args.offering_id is not None
    targets, total = _select_offerings(
        inventory, args.product_id, args.offering_id
    )
    _require_unambiguous(targets, total, selector, args.listing_id, "price")
    _guard_multiple(targets, total, selector, args.listing_id)
    rows = inventory_rows(args.listing_id, listing.get("title"), inventory)
    before = [
        r
        for r in rows
        if any(o.get("offering_id") == r["offering_id"] for _, o in targets)
    ]
    changes = []
    for product, offering in targets:
        changes.append(
            {
                "product_id": product.get("product_id"),
                "sku": product.get("sku"),
                "offering_id": offering.get("offering_id"),
                "old_price": norm_money(offering.get("price")),
                "new_price": {
                    "value": float(new_price),
                    "currency_code": (offering.get("price") or {}).get(
                        "currency_code"
                    ),
                },
            }
        )
    gate = _write_gate(args, "set-price", args.listing_id, before, changes)
    if gate is not None:
        return gate
    updated = copy.deepcopy(inventory)
    for product in updated.get("products", []):
        for offering in product.get("offerings", []):
            if any(
                o.get("offering_id") == offering.get("offering_id")
                for _, o in targets
            ):
                old = offering.get("price") or {}
                divisor = old.get("divisor") or 100
                amount = int(
                    (new_price * divisor).to_integral_value(
                        rounding=ROUND_HALF_UP
                    )
                )
                offering["price"] = {
                    "amount": amount,
                    "divisor": divisor,
                    "currency_code": old.get("currency_code"),
                }
    payload = {
        "products": updated.get("products", []),
        "price_on_property": updated.get("price_on_property", []),
        "quantity_on_property": updated.get("quantity_on_property", []),
        "sku_on_property": updated.get("sku_on_property", []),
    }
    result = client.update_inventory(args.listing_id, payload)
    after = inventory_rows(args.listing_id, listing.get("title"), result)
    return {
        "ok": True,
        "mode": client.mode,
        "action": "set-price",
        "listing_id": args.listing_id,
        "applied": True,
        "simulated": client.mode == "demo",
        "before": before,
        "after": [
            r
            for r in after
            if any(
                o.get("offering_id") == r["offering_id"] for _, o in targets
            )
        ],
    }


def cmd_set_quantity(client, args):
    args._client = client
    if args.quantity < 0:
        raise EtsyError("bad_quantity", "Quantity cannot be negative.")
    listing = client.get_listing(args.listing_id)
    inventory = client.get_inventory(args.listing_id)
    selector = args.product_id is not None or args.offering_id is not None
    targets, total = _select_offerings(
        inventory, args.product_id, args.offering_id
    )
    _require_unambiguous(targets, total, selector, args.listing_id, "qty")
    _guard_multiple(targets, total, selector, args.listing_id)
    rows = inventory_rows(args.listing_id, listing.get("title"), inventory)
    before = [
        r
        for r in rows
        if any(o.get("offering_id") == r["offering_id"] for _, o in targets)
    ]
    changes = [
        {
            "product_id": product.get("product_id"),
            "sku": product.get("sku"),
            "offering_id": offering.get("offering_id"),
            "old_quantity": offering.get("quantity"),
            "new_quantity": args.quantity,
        }
        for product, offering in targets
    ]
    gate = _write_gate(
        args, "set-quantity", args.listing_id, before, changes
    )
    if gate is not None:
        return gate
    updated = copy.deepcopy(inventory)
    for product in updated.get("products", []):
        for offering in product.get("offerings", []):
            if any(
                o.get("offering_id") == offering.get("offering_id")
                for _, o in targets
            ):
                offering["quantity"] = args.quantity
    payload = {
        "products": updated.get("products", []),
        "price_on_property": updated.get("price_on_property", []),
        "quantity_on_property": updated.get("quantity_on_property", []),
        "sku_on_property": updated.get("sku_on_property", []),
    }
    result = client.update_inventory(args.listing_id, payload)
    after = inventory_rows(args.listing_id, listing.get("title"), result)
    return {
        "ok": True,
        "mode": client.mode,
        "action": "set-quantity",
        "listing_id": args.listing_id,
        "applied": True,
        "simulated": client.mode == "demo",
        "before": before,
        "after": [
            r
            for r in after
            if any(
                o.get("offering_id") == r["offering_id"] for _, o in targets
            )
        ],
    }


def cmd_configure(client, args):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SHOP_STATE_FILE.write_text(
        json.dumps({"shop_id": args.shop_id}), encoding="utf-8"
    )
    return {
        "ok": True,
        "shop_id_saved": args.shop_id,
        "state_file": str(SHOP_STATE_FILE),
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--shop-id",
        type=int,
        default=None,
        help="Shop id override. Defaults to the connected account's shop.",
    )
    common.add_argument(
        "--api-key",
        default=None,
        help="Bring-your-own Etsy app keystring for testing. In normal use "
        "the registered connection supplies the keystring.",
    )
    parser = argparse.ArgumentParser(
        prog="etsy.py",
        description="Etsy connector for Muse. Add --demo anywhere to "
        "run against the fictional demo shop.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", parents=[common], help="Connected shop info.")
    sub.add_parser(
        "snapshot",
        parents=[common],
        help="Sales totals for today, yesterday and the last 7 days.",
    )
    p = sub.add_parser("orders", parents=[common], help="List receipts.")
    p.add_argument(
        "--status",
        default="all",
        choices=[
            "all",
            "unpaid",
            "paid",
            "unshipped",
            "shipped",
            "delivered",
        ],
    )
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--days", type=int, default=30)
    p = sub.add_parser("order", parents=[common], help="One receipt.")
    p.add_argument("receipt_id", type=int)
    p = sub.add_parser(
        "listings", parents=[common], help="Active listings."
    )
    p.add_argument("--search", default=None, help="Keyword filter.")
    p.add_argument("--limit", type=int, default=25)
    p = sub.add_parser("listing", parents=[common], help="One listing.")
    p.add_argument("listing_id", type=int)
    p = sub.add_parser(
        "inventory", parents=[common], help="Listing inventory levels."
    )
    p.add_argument("listing_id", type=int, nargs="?", default=None)
    p.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="Only show offerings at or below this quantity.",
    )
    p.add_argument("--max-listings", type=int, default=25)
    p = sub.add_parser("reviews", parents=[common], help="Recent reviews.")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser(
        "ledger", parents=[common], help="Payment account ledger entries."
    )
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--days", type=int, default=30)
    p = sub.add_parser(
        "set-price",
        parents=[common],
        help="Change an offering price. Approval-gated.",
    )
    p.add_argument("listing_id", type=int)
    p.add_argument("--price", required=True, help="New price, e.g. 24.50")
    p.add_argument("--product-id", type=int, default=None)
    p.add_argument("--offering-id", type=int, default=None)
    p.add_argument(
        "--yes",
        action="store_true",
        help="Apply the change. Without it, only the plan is printed.",
    )
    p = sub.add_parser(
        "set-quantity",
        parents=[common],
        help="Change an offering quantity. Approval-gated.",
    )
    p.add_argument("listing_id", type=int)
    p.add_argument("--quantity", type=int, required=True)
    p.add_argument("--product-id", type=int, default=None)
    p.add_argument("--offering-id", type=int, default=None)
    p.add_argument(
        "--yes",
        action="store_true",
        help="Apply the change. Without it, only the plan is printed.",
    )
    p = sub.add_parser("configure", help="Save the shop id locally.")
    p.add_argument("--shop-id", type=int, required=True)
    return parser


COMMANDS = {
    "status": cmd_status,
    "snapshot": cmd_snapshot,
    "orders": cmd_orders,
    "order": cmd_order,
    "listings": cmd_listings,
    "listing": cmd_listing,
    "inventory": cmd_inventory,
    "reviews": cmd_reviews,
    "ledger": cmd_ledger,
    "set-price": cmd_set_price,
    "set-quantity": cmd_set_quantity,
    "configure": cmd_configure,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    demo = "--demo" in argv
    if demo:
        argv = [a for a in argv if a != "--demo"]
    args = build_parser().parse_args(argv)
    try:
        if demo:
            client = DemoClient()
        else:
            license_check.enforce()
            client = LiveClient(
                shop_id=getattr(args, "shop_id", None),
                api_key_override=getattr(args, "api_key", None),
            )
        result = COMMANDS[args.command](client, args)
        print(json.dumps(result, indent=2))
        return 0
    except EtsyError as exc:
        print(
            json.dumps(
                {"ok": False, "error": exc.code, "message": exc.message},
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
