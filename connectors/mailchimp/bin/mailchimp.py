#!/usr/bin/env python3
"""Mailchimp connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads and approval-gated draft writes against the Mailchimp Marketing API
v3.0, through the registered Muse connection `custom.mailchimp`. The API key
never appears in this file, in arguments, or in output: helpers fetch an
hsurr: surrogate from Muse's dynamic-credential flow and Muse swaps in the
real key only on the request to the registered host <dc>.api.mailchimp.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation or compliance gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 mailchimp.py --demo audiences
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BIN_DIR)
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONFIG_PATH = os.path.join(PKG_DIR, "config.json")
CONNECTION_NAME = "custom.mailchimp"
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
    """Talks to https://<dc>.api.mailchimp.com/3.0 with the surrogate key."""

    def __init__(self, dc: str):
        self.dc = dc
        self.host = f"{dc}.api.mailchimp.com"
        self.base = f"https://{self.host}/3.0"
        sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
        from dynamic_credentials import add_surrogate_to_request, read_json_response

        self._add_surrogate = add_surrogate_to_request
        self._read_json = read_json_response

    def request(self, method: str, path: str, params=None, body=None):
        url = f"{self.base}/{path}" if path else f"{self.base}/"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        # Placement registered for this connection is bearer_header, which
        # Mailchimp accepts for API keys (equivalent to Basic auth).
        self._add_surrogate(
            request, CONNECTION_NAME, allowed_hosts=[self.host]
        )
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
            raise ApiError(
                exc.code,
                payload.get("title", ""),
                payload.get("detail", raw[:300]),
            ) from exc

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
        if path == "ping":
            return dict(data["ping"])
        if path == "":
            return dict(data["account"])
        if path == "lists":
            return {"lists": data["lists"], "total_items": len(data["lists"])}
        match = re.fullmatch(r"lists/([^/]+)", path)
        if match:
            for lst in data["lists"]:
                if lst["id"] == match.group(1):
                    return dict(lst)
            raise ApiError(404, "Resource Not Found", "No such audience in demo data.")
        match = re.fullmatch(r"lists/([^/]+)/growth-history", path)
        if match:
            history = data["growth_history"].get(match.group(1), [])
            return {"history": history, "list_id": match.group(1),
                    "total_items": len(history)}
        match = re.fullmatch(r"lists/([^/]+)/members", path)
        if match:
            members = data["members"].get(match.group(1), [])
            status = params.get("status")
            if status:
                members = [m for m in members if m.get("status") == status]
            return {"members": members, "total_items": len(members)}
        if path == "campaigns":
            campaigns = list(data["campaigns"])
            status = params.get("status")
            if status:
                campaigns = [c for c in campaigns if c.get("status") == status]
            since = params.get("since_send_time")
            if since:
                campaigns = [c for c in campaigns
                             if (c.get("send_time") or "") >= since]
            return {"campaigns": campaigns, "total_items": len(campaigns)}
        match = re.fullmatch(r"campaigns/([^/]+)", path)
        if match:
            for camp in data["campaigns"]:
                if camp["id"] == match.group(1):
                    return dict(camp)
            raise ApiError(404, "Resource Not Found", "No such campaign in demo data.")
        match = re.fullmatch(r"reports/([^/]+)", path)
        if match:
            report = data["reports"].get(match.group(1))
            if report is None:
                raise ApiError(404, "Resource Not Found",
                               "No report for that campaign (drafts have none).")
            return dict(report)
        if path == "search-members":
            query = str(params.get("query", "")).lower()
            list_id = params.get("list_id")
            results = []
            for lid, members in data["members"].items():
                if list_id and lid != list_id:
                    continue
                for member in members:
                    haystack = " ".join([
                        member.get("email_address", ""),
                        member.get("full_name", ""),
                    ]).lower()
                    if query in haystack:
                        results.append(member)
            return {"results": {"members": results,
                                "total_items": len(results)}}
        if path == "ecommerce/stores":
            return {"stores": data.get("stores", []),
                    "total_items": len(data.get("stores", []))}
        raise ApiError(404, "Resource Not Found", f"Demo data has no route: {path}")

    def post(self, path, body):
        if path == "campaigns":
            created = dict(body)
            created.update({
                "id": "demo_new_campaign",
                "status": "save",
                "create_time": datetime.now(timezone.utc).isoformat(),
                "emails_sent": 0,
                "demo": True,
                "simulated": True,
            })
            created.setdefault("settings", {})
            return created
        match = re.fullmatch(r"lists/([^/]+)/members", path)
        if match:
            member = dict(body)
            member.update({"id": "demo_new_member", "list_id": match.group(1),
                           "demo": True, "simulated": True})
            return member
        match = re.fullmatch(r"lists/([^/]+)/members/([^/]+)/tags", path)
        if match:
            return {"demo": True, "simulated": True,
                    "note": "Mailchimp returns 204 No Content for tag updates."}
        raise ApiError(404, "Resource Not Found", f"Demo data has no route: POST {path}")


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def resolve_datacenter(cli_dc=None) -> str:
    """The datacenter (us21, eu1, ...) is routing info, not a secret.

    Resolution order: --dc flag, MAILCHIMP_DC env var, config.json beside
    the package ({"datacenter": "us21"}), written at install time.
    """
    if cli_dc:
        return cli_dc.strip().lower()
    env_dc = os.environ.get("MAILCHIMP_DC", "").strip().lower()
    if env_dc:
        return env_dc
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            dc = str(json.load(fh).get("datacenter", "")).strip().lower()
        if dc:
            return dc
    except (OSError, json.JSONDecodeError):
        pass
    raise RuntimeError(
        "No Mailchimp datacenter configured. The datacenter is the suffix "
        "after the last hyphen of the API key (for example us21) and is also "
        "shown in the Mailchimp web address when signed in. Set it once with "
        "the --dc flag, the MAILCHIMP_DC environment variable, or a "
        "config.json beside the connector: {\"datacenter\": \"us21\"}."
    )


def make_client(args) -> object:
    if args.demo:
        return DemoClient()
    return LiveClient(resolve_datacenter(args.dc))


def fetch_all(client, path, key, params=None, page_size=100, cap=1000):
    """Page through a Mailchimp collection endpoint."""
    params = dict(params or {})
    items = []
    offset = 0
    while len(items) < cap:
        params["count"] = page_size
        params["offset"] = offset
        page = client.get(path, params=params)
        batch = page.get(key, [])
        items.extend(batch)
        total = page.get("total_items", len(items))
        offset += len(batch)
        if not batch or offset >= total:
            break
    return items[:cap]


# ---------------------------------------------------------------------------
# Output shaping (defensive .get throughout: Mailchimp omits empty objects)
# ---------------------------------------------------------------------------

def curate_list(lst: dict) -> dict:
    stats = lst.get("stats") or {}
    return {
        "id": lst.get("id"),
        "name": lst.get("name"),
        "member_count": stats.get("member_count"),
        "total_contacts": stats.get("total_contacts"),
        "unsubscribe_count": stats.get("unsubscribe_count"),
        "cleaned_count": stats.get("cleaned_count"),
        "campaign_count": stats.get("campaign_count"),
        "avg_sub_rate_per_day": stats.get("avg_sub_rate"),
        "avg_unsub_rate_per_day": stats.get("avg_unsub_rate"),
        "open_rate": stats.get("open_rate"),
        "click_rate": stats.get("click_rate"),
        "list_rating": lst.get("list_rating"),
        "date_created": lst.get("date_created"),
        "double_optin": (lst.get("campaign_defaults") is not None
                         and lst.get("email_type_option")),
    }


def curate_growth_row(row: dict) -> dict:
    existing = row.get("existing")
    subscribed = row.get("subscribed")
    if isinstance(existing, int) and isinstance(subscribed, int):
        net = subscribed - existing
    else:
        net = ((row.get("optins") or 0) + (row.get("imports") or 0)
               - (row.get("unsubscribed") or 0) - (row.get("cleaned") or 0)
               - (row.get("deleted") or 0))
    return {
        "month": row.get("month"),
        "existing_at_month_start": existing,
        "imports": row.get("imports"),
        "optins": row.get("optins"),
        "unsubscribed": row.get("unsubscribed"),
        "cleaned": row.get("cleaned"),
        "deleted": row.get("deleted"),
        "subscribed_at_month_end": subscribed,
        "net_change": net,
    }


def curate_campaign(camp: dict) -> dict:
    settings = camp.get("settings") or {}
    recipients = camp.get("recipients") or {}
    summary = camp.get("report_summary") or {}
    out = {
        "id": camp.get("id"),
        "title": settings.get("title"),
        "subject_line": settings.get("subject_line"),
        "type": camp.get("type"),
        "status": camp.get("status"),
        "audience_id": recipients.get("list_id"),
        "audience_name": recipients.get("list_name"),
        "emails_sent": camp.get("emails_sent"),
        "create_time": camp.get("create_time"),
        "send_time": camp.get("send_time"),
        "from_name": settings.get("from_name"),
        "reply_to": settings.get("reply_to"),
    }
    if camp.get("status") == "sent" and summary:
        out["report_summary"] = {
            "opens_total": summary.get("opens"),
            "unique_opens": summary.get("unique_opens"),
            "open_rate": summary.get("open_rate"),
            "clicks_total": summary.get("clicks"),
            "unique_clicks": summary.get("unique_clicks"),
            "click_rate": summary.get("click_rate"),
        }
    return out


def curate_report(rep: dict) -> dict:
    opens = rep.get("opens") or {}
    clicks = rep.get("clicks") or {}
    bounces = rep.get("bounces") or {}
    forwards = rep.get("forwards") or {}
    industry = rep.get("industry_stats") or {}
    ecommerce = rep.get("ecommerce") or {}
    emails_sent = rep.get("emails_sent")
    unsubs = rep.get("unsubscribed")
    hard = bounces.get("hard_bounces")
    soft = bounces.get("soft_bounces")
    return {
        "campaign_id": rep.get("id"),
        "campaign_title": rep.get("campaign_title"),
        "subject_line": rep.get("subject_line"),
        "audience_name": rep.get("list_name"),
        "send_time": rep.get("send_time"),
        "emails_sent": emails_sent,
        "opens_total": opens.get("opens_total"),
        "unique_opens": opens.get("unique_opens"),
        "open_rate": opens.get("open_rate"),
        "clicks_total": clicks.get("clicks_total"),
        "unique_clicks": clicks.get("unique_clicks"),
        "click_rate": clicks.get("click_rate"),
        "hard_bounces": hard,
        "soft_bounces": soft,
        "bounces_total": (hard or 0) + (soft or 0)
        if hard is not None or soft is not None else None,
        "unsubscribes": unsubs,
        "unsub_rate": round(unsubs / emails_sent, 4)
        if isinstance(unsubs, int) and emails_sent else None,
        "abuse_reports": rep.get("abuse_reports"),
        "forwards": forwards.get("forwards_count"),
        "total_orders": ecommerce.get("total_orders"),
        "total_revenue": ecommerce.get("total_revenue"),
        "industry_open_rate": industry.get("open_rate"),
        "industry_click_rate": industry.get("click_rate"),
    }


def curate_member(member: dict) -> dict:
    merge = member.get("merge_fields") or {}
    tags = member.get("tags") or []
    return {
        "email_address": member.get("email_address"),
        "first_name": merge.get("FNAME"),
        "last_name": merge.get("LNAME"),
        "status": member.get("status"),
        "audience_id": member.get("list_id"),
        "tags": [t.get("name") for t in tags if isinstance(t, dict)],
        "vip": member.get("vip"),
        "member_rating": member.get("member_rating"),
        "timestamp_opt": member.get("timestamp_opt"),
        "last_changed": member.get("last_changed"),
    }


# ---------------------------------------------------------------------------
# Read commands
# ---------------------------------------------------------------------------

def cmd_status(client, args):
    ping = client.get("ping")
    account = client.get("")
    stores = client.get("ecommerce/stores")
    account_view = {
        "account_id": account.get("account_id"),
        "account_name": account.get("account_name"),
        "industry": account.get("account_ind"),
        "timezone": account.get("account_timezone"),
        "total_subscribers": account.get("total_subscribers"),
    }
    return {
        "health_status": ping.get("health_status"),
        "account": account_view,
        "ecommerce_stores_connected": stores.get("total_items", 0),
        # Pass the account id as the shop identity: the license check
        # hashes it locally; the raw id never leaves this machine.
        "license": license_check.check(demo=args.demo,
                                       shop_identity=account.get("account_id")),
        "demo": bool(args.demo),
    }


def cmd_audiences(client, args):
    lists = fetch_all(client, "lists", "lists")
    return {"audiences": [curate_list(lst) for lst in lists],
            "total": len(lists)}


def cmd_audience(client, args):
    lst = client.get(f"lists/{args.audience_id}")
    growth = client.get(f"lists/{args.audience_id}/growth-history")
    history = [curate_growth_row(r) for r in growth.get("history", [])]
    return {"audience": curate_list(lst),
            "growth_recent_months": history[-args.months:]}


def cmd_campaigns(client, args):
    params = {"sort_field": "send_time", "sort_dir": "DESC"}
    if args.status:
        params["status"] = args.status
    if args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["since_send_time"] = since.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    campaigns = fetch_all(client, "campaigns", "campaigns", params=params)
    return {"campaigns": [curate_campaign(c) for c in campaigns],
            "total": len(campaigns)}


def cmd_campaign(client, args):
    camp = client.get(f"campaigns/{args.campaign_id}")
    return {"campaign": curate_campaign(camp)}


def cmd_report(client, args):
    rep = client.get(f"reports/{args.campaign_id}")
    return {"report": curate_report(rep)}


def cmd_top_campaigns(client, args):
    params = {"status": "sent", "sort_field": "send_time", "sort_dir": "DESC"}
    if args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["since_send_time"] = since.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    campaigns = fetch_all(client, "campaigns", "campaigns", params=params)
    rate_key = "open_rate" if args.by == "open" else "click_rate"
    ranked = []
    for camp in campaigns:
        summary = camp.get("report_summary") or {}
        rate = summary.get(rate_key)
        if rate is None:
            continue
        ranked.append({
            "id": camp.get("id"),
            "title": (camp.get("settings") or {}).get("title"),
            "subject_line": (camp.get("settings") or {}).get("subject_line"),
            "send_time": camp.get("send_time"),
            "emails_sent": camp.get("emails_sent"),
            "open_rate": summary.get("open_rate"),
            "click_rate": summary.get("click_rate"),
            "unique_opens": summary.get("unique_opens"),
            "unique_clicks": summary.get("unique_clicks"),
        })
    ranked.sort(key=lambda item: item[rate_key], reverse=True)
    return {"ranked_by": rate_key, "period_days": args.days,
            "campaigns": ranked[:args.limit], "considered": len(ranked)}


def cmd_members(client, args):
    if args.query:
        page = client.get("search-members", params={
            "query": args.query, "list_id": args.audience_id})
        members = (page.get("results") or {}).get("members", [])
    else:
        params = {}
        if args.status:
            params["status"] = args.status
        members = fetch_all(client, f"lists/{args.audience_id}/members",
                            "members", params=params)
    return {"members": [curate_member(m) for m in members[:args.count]],
            "total": len(members)}


def cmd_growth(client, args):
    if args.audience_id:
        targets = [client.get(f"lists/{args.audience_id}")]
    else:
        targets = fetch_all(client, "lists", "lists")
    out = []
    for lst in targets:
        growth = client.get(f"lists/{lst['id']}/growth-history")
        history = [curate_growth_row(r) for r in growth.get("history", [])]
        recent = history[-args.months:]
        out.append({
            "audience_id": lst.get("id"),
            "audience_name": lst.get("name"),
            "current_member_count": (lst.get("stats") or {}).get("member_count"),
            "months": recent,
            "net_change_recent_months": sum(r["net_change"] for r in recent),
            "optins_recent_months": sum(r["optins"] or 0 for r in recent),
            "unsubscribes_recent_months": sum(r["unsubscribed"] or 0 for r in recent),
            "cleaned_recent_months": sum(r["cleaned"] or 0 for r in recent),
        })
    return {"audiences": out}


# ---------------------------------------------------------------------------
# Write commands. Every write prints a BEFORE summary first and changes
# nothing unless --yes is passed. Exit code 2 means a gate stopped the write.
# ---------------------------------------------------------------------------

def gate_write(summary: dict, yes: bool) -> bool:
    """Print the BEFORE summary. Return True only when confirmed with --yes."""
    print(json.dumps(summary, indent=2))
    if not yes:
        print(json.dumps({
            "confirmed": False,
            "message": "Nothing was changed. Review the summary above, then "
                       "re-run the same command with --yes to apply it.",
        }, indent=2))
        raise SystemExit(2)
    return True


def cmd_create_campaign(client, args):
    body = {
        "type": args.type,
        "recipients": {"list_id": args.audience_id},
        "settings": {
            "subject_line": args.subject,
            "title": args.title or args.subject,
            "from_name": args.from_name,
            "reply_to": args.reply_to,
        },
    }
    summary = {
        "action": "create_campaign_draft",
        "will_create": body,
        "note": "This creates a DRAFT only. This connector cannot send "
                "campaigns. The owner reviews and sends from Mailchimp.",
    }
    gate_write(summary, args.yes)
    created = client.post("campaigns", body)
    result = {"created": curate_campaign(created) if created.get("id") else created,
              "note": "Draft created. Review and send it from Mailchimp. "
                      "Sending is not supported by this connector."}
    if args.demo:
        result["demo"] = True
    print(json.dumps(result, indent=2))


def cmd_add_tag(client, args):
    subscriber_hash = hashlib.md5(
        args.email.strip().lower().encode("utf-8")).hexdigest()
    body = {"tags": [{"name": tag, "status": "active"} for tag in args.tag]}
    summary = {
        "action": "add_tag",
        "audience_id": args.audience_id,
        "member_email": args.email,
        "will_add_tags": args.tag,
        "endpoint": f"lists/{args.audience_id}/members/{subscriber_hash}/tags",
    }
    gate_write(summary, args.yes)
    client.post(f"lists/{args.audience_id}/members/{subscriber_hash}/tags", body)
    result = {"tagged": True, "member_email": args.email, "tags": args.tag,
              "audience_id": args.audience_id}
    if args.demo:
        result["demo"] = True
    print(json.dumps(result, indent=2))


def cmd_add_member(client, args):
    if not args.consent:
        print(json.dumps({
            "error": "consent_required",
            "message": "Refused. Adding a member requires --consent, your "
                       "explicit confirmation that this person opted in to "
                       "receive email from this audience. Never add people "
                       "who have not opted in: it breaks anti-spam law "
                       "(CAN-SPAM, GDPR, CASL) and Mailchimp's terms, and it "
                       "damages the account's sending reputation.",
        }, indent=2))
        raise SystemExit(2)
    body = {
        "email_address": args.email,
        "status": args.status,
        "merge_fields": {},
    }
    if args.first_name:
        body["merge_fields"]["FNAME"] = args.first_name
    if args.last_name:
        body["merge_fields"]["LNAME"] = args.last_name
    if args.tag:
        body["tags"] = args.tag
    summary = {
        "action": "add_member",
        "audience_id": args.audience_id,
        "will_add": body,
        "consent_confirmed": True,
        "note": "Status 'subscribed' adds the person immediately. Status "
                "'pending' sends them a double opt-in confirmation first.",
    }
    gate_write(summary, args.yes)
    created = client.post(f"lists/{args.audience_id}/members", body)
    result = {"added": curate_member(created) if created.get("email_address") else created}
    if args.demo:
        result["demo"] = True
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mailchimp.py",
        description="Mailchimp connector for Muse. All output is JSON.")
    parser.add_argument("--demo", action="store_true",
                        help="Use the bundled fictional demo data. No network, "
                             "no credential, no license check.")
    parser.add_argument("--dc", default=None,
                        help="Mailchimp datacenter override, for example us21.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Ping plus account info and license state.")

    sub.add_parser("audiences", help="All audiences with counts and stats.")

    p = sub.add_parser("audience", help="One audience plus recent growth.")
    p.add_argument("audience_id")
    p.add_argument("--months", type=int, default=6)

    p = sub.add_parser("campaigns", help="Recent campaigns.")
    p.add_argument("--status", default=None,
                   help="Filter by status: sent, save, sending, schedule, paused.")
    p.add_argument("--days", type=int, default=None,
                   help="Only campaigns sent in the last N days.")

    p = sub.add_parser("campaign", help="One campaign in detail.")
    p.add_argument("campaign_id")

    p = sub.add_parser("report", help="Full report for a sent campaign.")
    p.add_argument("campaign_id")

    p = sub.add_parser("top-campaigns", help="Rank sent campaigns by rate.")
    p.add_argument("--by", choices=["open", "click"], default="open")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("members", help="Search or list members of an audience.")
    p.add_argument("audience_id")
    p.add_argument("query", nargs="?", default=None,
                   help="Optional search text (name or email).")
    p.add_argument("--status", default=None,
                   help="When listing without a query: subscribed, "
                        "unsubscribed, cleaned, pending, archived.")
    p.add_argument("--count", type=int, default=25)

    p = sub.add_parser("growth", help="Audience growth summary by month.")
    p.add_argument("--audience-id", default=None)
    p.add_argument("--months", type=int, default=6)

    p = sub.add_parser("create-campaign",
                       help="Create a DRAFT campaign. Never sends.")
    p.add_argument("--audience-id", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--from-name", required=True)
    p.add_argument("--reply-to", required=True)
    p.add_argument("--title", default=None)
    p.add_argument("--type", default="regular",
                   choices=["regular", "plaintext"])
    p.add_argument("--yes", action="store_true",
                   help="Confirm the write after reviewing the summary.")

    p = sub.add_parser("add-tag", help="Add tag(s) to a member.")
    p.add_argument("--audience-id", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--tag", action="append", required=True,
                   help="Tag name. Repeat for several tags.")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("add-member", help="Add a member who has opted in.")
    p.add_argument("--audience-id", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--first-name", default=None)
    p.add_argument("--last-name", default=None)
    p.add_argument("--tag", action="append", default=None)
    p.add_argument("--status", default="subscribed",
                   choices=["subscribed", "pending"])
    p.add_argument("--consent", action="store_true",
                   help="Required. Confirms this person opted in.")
    p.add_argument("--yes", action="store_true")
    return parser


READ_COMMANDS = {
    "status": cmd_status,
    "audiences": cmd_audiences,
    "audience": cmd_audience,
    "campaigns": cmd_campaigns,
    "campaign": cmd_campaign,
    "report": cmd_report,
    "top-campaigns": cmd_top_campaigns,
    "members": cmd_members,
    "growth": cmd_growth,
}

WRITE_COMMANDS = {
    "create-campaign": cmd_create_campaign,
    "add-tag": cmd_add_tag,
    "add-member": cmd_add_member,
}


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.demo = args.demo or os.environ.get("MAILCHIMP_DEMO") == "1"
    try:
        client = make_client(args)
        if args.command in READ_COMMANDS:
            if args.command != "status":
                license_check.ensure_active(demo=args.demo)
            result = READ_COMMANDS[args.command](client, args)
            if result is not None:
                print(json.dumps(result, indent=2))
            return 0
        license_check.ensure_active(demo=args.demo)
        WRITE_COMMANDS[args.command](client, args)
        return 0
    except SystemExit:
        raise
    except ApiError as exc:
        print(json.dumps({"error": "mailchimp_api_error",
                          "status": exc.status, "title": exc.title,
                          "detail": exc.detail}, indent=2))
        return 1
    except Exception as exc:  # keep stdout parseable for the calling Muse
        print(json.dumps({"error": "connector_error",
                          "detail": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
