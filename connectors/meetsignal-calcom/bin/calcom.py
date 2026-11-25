#!/usr/bin/env python3
"""MeetSignal for Cal.com connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads event types/bookings/schedules and cancels bookings
(approval-gated, explicit) via the Cal.com API v2
(https://api.cal.com/v2), Bearer surrogate from Muse's
dynamic-credential flow (connection `custom.calcom`). Every request
carries the required header cal-api-version: 2024-08-13 — verified
2026-11-24 against Cal.com's official v1-to-v2 migration guide for
bookings and event types. Cal.com versions some endpoints
independently; see CONNECTOR.md Limits. Responses are wrapped as
{status, data}; this CLI unwraps the envelope.

Exit codes: 0 success, 1 API/runtime error, 2 confirmation gate, 3 license.
Demo: python3 calcom.py --demo bookings --status upcoming
"""
from __future__ import annotations
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONNECTION_NAME = "custom.calcom"
API_HOST = "api.cal.com"
API_BASE = "https://api.cal.com/v2"
CAL_API_VERSION = "2024-08-13"
DYNAMIC_CREDENTIALS_DIR = "/opt/muse/skills/custom-connector-setup/bin"
sys.path.insert(0, BIN_DIR)
import license_check  # noqa: E402

class ApiError(RuntimeError):
    def __init__(self, status, title, detail):
        super().__init__(detail or title or f"HTTP {status}")
        self.status, self.title, self.detail = status, title, detail

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")

def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "status" in payload:
        return payload["data"]
    return payload

class LiveClient:
    def __init__(self):
        sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
        from dynamic_credentials import add_surrogate_to_request, read_json_response
        self._add_surrogate = add_surrogate_to_request
        self._read_json = read_json_response
    def request(self, method, path, params=None, body=None):
        url = f"{API_BASE}/{path}" if path else API_BASE
        if params: url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("cal-api-version", CAL_API_VERSION)
        if body is not None: request.add_header("Content-Type", "application/json")
        self._add_surrogate(request, CONNECTION_NAME, allowed_hosts=[API_HOST])
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=60) as response:
                if response.status == 204: return {}
                return self._read_json(response)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try: payload = json.loads(raw)
            except json.JSONDecodeError: payload = {}
            if isinstance(payload, dict):
                title = payload.get("title") or payload.get("message") or ""
                detail = payload.get("detail") or raw[:300]
            else: title, detail = "", raw[:300]
            raise ApiError(exc.code, str(title), str(detail)) from exc
    def get(self, path, params=None): return self.request("GET", path, params=params)
    def post(self, path, body=None): return self.request("POST", path, body=body if body is not None else {})

class DemoClient:
    def __init__(self):
        with open(DEMO_PATH, encoding="utf-8") as fh: self.data = json.load(fh)
    def get(self, path, params=None):
        d = self.data
        if path == "me": return {"status": "success", "data": dict(d["me"])}
        if path == "event-types": return {"status": "success", "data": list(d["event_types"])}
        if path == "bookings": return {"status": "success", "data": list(d["bookings"])}
        if path == "schedules": return {"status": "success", "data": list(d["schedules"])}
        m = re.fullmatch(r"bookings/([^/]+)", path)
        if m:
            for b in d["bookings"]:
                if b["uid"] == m.group(1): return {"status": "success", "data": dict(b)}
            raise ApiError(404, "Not in demo", f"No demo booking {m.group(1)}")
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body=None):
        m = re.fullmatch(r"bookings/([^/]+)/cancel", path)
        if m: return {"status": "success", "data": {"uid": m.group(1), "status": "cancelled", "cancellationReason": (body or {}).get("reason"), "demo": True, "simulated": True}}
        raise ApiError(404, "Not in demo", f"No demo fixture for POST {path}")

def emit(payload, exit_code=0):
    print(json.dumps(payload, indent=2, default=str)); raise SystemExit(exit_code)

def curate_booking(b):
    attendees = b.get("attendees") or []
    return {"uid": b.get("uid"), "title": b.get("title"), "status": b.get("status"),
            "start": b.get("start"), "end": b.get("end"),
            "event_type_id": b.get("eventTypeId"),
            "attendees": [{"name": a.get("name"), "email": a.get("email"), "timeZone": a.get("timeZone")} for a in attendees if isinstance(a, dict)],
            "location": b.get("location"), "description_excerpt": (b.get("description") or "")[:200]}

def run_command(client, args):
    demo = isinstance(client, DemoClient)
    if args.command == "status":
        me = unwrap(client.get("me"))
        emit({"ok": True, "connected": True, "me": me, "cal_api_version": CAL_API_VERSION, "demo": demo})
    if args.command == "event-types":
        data = unwrap(client.get("event-types"))
        types = data if isinstance(data, list) else (data.get("eventTypes") or data.get("eventTypeGroups") or [])
        emit({"ok": True, "event_types": [{"id": t.get("id"), "title": t.get("title"), "slug": t.get("slug"),
              "length_in_minutes": t.get("lengthInMinutes") or t.get("length"), "hidden": t.get("hidden")} for t in types if isinstance(t, dict)], "total": len(types)})
    if args.command == "bookings":
        data = unwrap(client.get("bookings"))
        bookings = data if isinstance(data, list) else data.get("bookings", [])
        curated = [curate_booking(b) for b in bookings]
        if args.status:
            if args.status == "upcoming":
                now = datetime.now(timezone.utc).isoformat()
                curated = [b for b in curated if b["status"] not in ("cancelled", "rejected") and (b["start"] or "") >= now]
            elif args.status in ("past", "unconfirmed"):
                # Cal.com accepts these as API-side filters live; in demo,
                # approximate: past = already ended, unconfirmed = pending.
                if args.status == "past":
                    now = datetime.now(timezone.utc).isoformat()
                    curated = [b for b in curated if (b["end"] or "") < now]
                else:
                    curated = [b for b in curated if b["status"] == "pending"]
            else:
                curated = [b for b in curated if b["status"] == args.status]
        emit({"ok": True, "bookings": curated, "total": len(curated), "filter": args.status})
    if args.command == "booking":
        b = unwrap(client.get(f"bookings/{args.booking_id}"))
        emit({"ok": True, "booking": curate_booking(b) if isinstance(b, dict) else b})
    if args.command == "schedules":
        data = unwrap(client.get("schedules"))
        schedules = data if isinstance(data, list) else data.get("schedules", [])
        emit({"ok": True, "schedules": [{"id": s.get("id"), "name": s.get("name"), "time_zone": s.get("timeZone"), "is_default": s.get("isDefault")} for s in schedules if isinstance(s, dict)], "total": len(schedules)})
    if args.command == "cancel-booking":
        # Destructive: cancellation notifies attendees on Cal.com's side.
        if not args.yes:
            emit({"ok": False, "approval_required": True, "action": "cancel_booking",
                  "proposed": {"booking_uid": args.booking_id, "reason": args.reason,
                               "endpoint": f"POST /bookings/{args.booking_id}/cancel"},
                  "warning": "DESTRUCTIVE: cancelling notifies the attendees and frees the slot. This cannot be undone from this connector.",
                  "message": "Nothing was changed. Show this exact proposal to the owner; re-run with --yes only after they approve cancelling THIS booking."}, 2)
        result = unwrap(client.post(f"bookings/{args.booking_id}/cancel", {"reason": args.reason}))
        if demo: emit({"ok": True, "cancelled": result, "demo": True, "simulated": True})
        back = unwrap(client.get(f"bookings/{args.booking_id}"))
        emit({"ok": True, "cancelled": curate_booking(back) if isinstance(back, dict) else result, "verified_read_back": True})
    raise ApiError(400, "unknown_command", str(args.command))

def main(argv=None):
    parser = argparse.ArgumentParser(description="MeetSignal for Cal.com for Muse")
    parser.add_argument("--demo", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); sub.add_parser("event-types"); sub.add_parser("schedules")
    p = sub.add_parser("bookings"); p.add_argument("--status", default=None, help="upcoming (default filter in briefs), past, cancelled, unconfirmed, or a raw status")
    p = sub.add_parser("booking"); p.add_argument("booking_id")
    p = sub.add_parser("cancel-booking"); p.add_argument("booking_id"); p.add_argument("--reason", required=True); p.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo: license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try: return run_command(client, args)
    except ApiError as exc: emit({"ok": False, "error": exc.title or "api_error", "status": exc.status, "detail": exc.detail}, 1)

if __name__ == "__main__":
    raise SystemExit(main())
