#!/usr/bin/env python3
"""PipeSignal for Pipedrive connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Connects your Pipedrive company to Muse — persons, deals, organisations, activities and pipelines.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.pipesignal-pipedrive`) and Muse swaps in the real credential only
on the request to the registered host api.pipedrive.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 pipedrive.py --demo status
"""

from __future__ import annotations

import argparse
import re
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BIN_DIR)
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONNECTION_NAME = "custom.pipesignal-pipedrive"
API_HOST = "api.pipedrive.com"
API_BASE = "https://api.pipedrive.com/v1"
# AUTH_STYLE: "bearer" (Authorization: Bearer <token surrogate>),
# "header:NAME" (custom header), or "query:NAME" (query parameter).
AUTH_STYLE = "query:api_token"
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
    """Talks to https://api.pipedrive.com/v1 with the surrogate credential."""

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
        params=params or {}; data=self.data
        if path=="persons": return {"success":True,"data":data["persons"][:int(params.get("limit",500))]}
        m=re.fullmatch(r"persons/([^/]+)",path)
        if m:
            for x in data["persons"]:
                if str(x["id"])==m.group(1): return {"success":True,"data":dict(x)}
            raise ApiError(404,"Not Found","No such person in demo data.")
        if path=="deals":
            res=list(data["deals"])
            if params.get("status"): res=[d for d in res if d.get("status")==params["status"]]
            return {"success":True,"data":res}
        m=re.fullmatch(r"deals/([^/]+)",path)
        if m:
            for x in data["deals"]:
                if str(x["id"])==m.group(1): return {"success":True,"data":dict(x)}
            raise ApiError(404,"Not Found","No such deal in demo data.")
        if path=="organizations": return {"success":True,"data":data["organizations"]}
        if path=="activities": return {"success":True,"data":data["activities"]}
        if path=="pipelines": return {"success":True,"data":data["pipelines"]}
        raise ApiError(404,"Not in demo",f"No demo fixture for GET {path}")
    def post(self, path, body):
        if path=="activities":
            created=dict(body or {}); created.update({"id":9991,"demo":True,"simulated":True}); return {"success":True,"data":created}
        raise ApiError(404,"Not in demo",f"No demo fixture for POST {path}")

def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PipeSignal for Pipedrive for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    p=sub.add_parser("persons"); p.add_argument("--limit",type=int,default=20)
    p=sub.add_parser("person"); p.add_argument("id")
    p=sub.add_parser("deals"); p.add_argument("--status",default=None,help="open, won, lost, deleted"); p.add_argument("--limit",type=int,default=50)
    p=sub.add_parser("deal"); p.add_argument("id")
    sub.add_parser("orgs")
    p=sub.add_parser("activities"); p.add_argument("--days",type=int,default=None)
    sub.add_parser("pipelines")
    p=sub.add_parser("add-activity"); p.add_argument("--subject",required=True); p.add_argument("--type",default="call"); p.add_argument("--person-id",type=int,default=None); p.add_argument("--deal-id",type=int,default=None); p.add_argument("--due-date",default=None,help="YYYY-MM-DD"); p.add_argument("--yes",action="store_true")
    args = parser.parse_args(argv)

    if not args.demo:
        license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try:
        return run_command(client, args)
    except ApiError as exc:
        emit({"ok": False, "error": exc.title or "api_error",
              "status": exc.status, "detail": exc.detail}, 1)



def cur_person(d): return {"id":d.get("id"),"name":d.get("name"),"email":(d.get("email") or [{}])[0].get("value") if isinstance(d.get("email"),list) and d.get("email") else d.get("email"),"phone":(d.get("phone") or [{}])[0].get("value") if isinstance(d.get("phone"),list) and d.get("phone") else d.get("phone"),"org_id":(d.get("org_id") or {}).get("value") if isinstance(d.get("org_id"),dict) else d.get("org_id"),"add_time":d.get("add_time"),"update_time":d.get("update_time")}
def cur_deal(d): return {"id":d.get("id"),"title":d.get("title"),"value":d.get("value"),"currency":d.get("currency"),"status":d.get("status"),"stage_id":d.get("stage_id"),"pipeline_id":d.get("pipeline_id"),"person_id":(d.get("person_id") or {}).get("value") if isinstance(d.get("person_id"),dict) else d.get("person_id"),"org_id":(d.get("org_id") or {}).get("value") if isinstance(d.get("org_id"),dict) else d.get("org_id"),"add_time":d.get("add_time"),"update_time":d.get("update_time"),"expected_close_date":d.get("expected_close_date")}
def cur_org(d): return {"id":d.get("id"),"name":d.get("name"),"address":d.get("address"),"add_time":d.get("add_time"),"update_time":d.get("update_time")}
def cur_act(d): return {"id":d.get("id"),"subject":d.get("subject"),"type":d.get("type"),"due_date":d.get("due_date"),"due_time":d.get("due_time"),"done":d.get("done"),"person_id":d.get("person_id"),"deal_id":d.get("deal_id"),"org_id":d.get("org_id")}
def _data(r): return r.get("data") or []

def run_command(client, args) -> int:

    cmd=args.command
    if cmd=="status":
        r=client.get("pipelines"); emit({"ok":True,"connected":True,"service":"Pipedrive","demo":isinstance(client,DemoClient),"pipelines":len(_data(r))})
    if cmd=="persons":
        r=client.get("persons",params={"limit":args.limit}); emit({"persons":[cur_person(x) for x in _data(r)[:args.limit]],"total_returned":len(_data(r))})
    if cmd=="person":
        r=client.get(f"persons/{args.id}"); emit({"person":cur_person(r.get("data") or {})})
    if cmd=="deals":
        params={}
        if args.status: params["status"]=args.status
        r=client.get("deals",params=params); emit({"deals":[cur_deal(x) for x in _data(r)[:args.limit]],"total_returned":len(_data(r))})
    if cmd=="deal":
        r=client.get(f"deals/{args.id}"); emit({"deal":cur_deal(r.get("data") or {})})
    if cmd=="orgs":
        r=client.get("organizations"); emit({"organizations":[cur_org(x) for x in _data(r)],"total_returned":len(_data(r))})
    if cmd=="activities":
        r=client.get("activities"); acts=[cur_act(x) for x in _data(r)]
        note=None
        if args.days:
            from datetime import date, timedelta
            lo=date.today().isoformat(); hi=(date.today()+timedelta(days=args.days)).isoformat()
            filtered=[a for a in acts if a.get("due_date") and lo <= a["due_date"] <= hi]
            if filtered: acts=filtered
            else: note=f"No activities fell in the next {args.days} days window in the returned data; showing all returned activities."
        emit({"activities":acts,"total_returned":len(acts),"note":note})
    if cmd=="pipelines":
        r=client.get("pipelines"); emit({"pipelines":_data(r),"total_returned":len(_data(r))})
    if cmd=="add-activity":
        body={"subject":args.subject,"type":args.type,"done":False}
        if args.person_id: body["person_id"]=args.person_id
        if args.deal_id: body["deal_id"]=args.deal_id
        if args.due_date: body["due_date"]=args.due_date
        if not args.yes: emit({"ok":False,"approval_required":True,"action":"add_activity","will_create":body,"message":"Nothing was changed. Show this summary to the owner and re-run with --yes only after they approve this exact activity."},2)
        created=client.post("activities",body); emit({"ok":True,"created":created.get("data",created),"demo":isinstance(client,DemoClient)})
    emit({"ok":False,"error":"unknown_command","detail":cmd},1)


if __name__ == "__main__":
    raise SystemExit(main())
