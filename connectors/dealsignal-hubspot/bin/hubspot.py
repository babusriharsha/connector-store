#!/usr/bin/env python3
"""DealSignal for HubSpot connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Connects your HubSpot CRM to Muse — contacts, companies, deals and pipelines in plain numbers.

The credential never appears in this file, in arguments, or in output:
helpers fetch an hsurr: surrogate from Muse's dynamic-credential flow
(connection `custom.dealsignal-hubspot`) and Muse swaps in the real credential only
on the request to the registered host api.hubapi.com.

Every command prints clean JSON to stdout. Exit codes:
  0  success
  1  API or runtime error (JSON error object on stdout)
  2  a confirmation gate stopped a write (nothing was changed)
  3  license inactive (free trial over, no valid license)

Run any read command with --demo to use the bundled fictional sample data:
  python3 hubspot.py --demo status
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
CONNECTION_NAME = "custom.dealsignal-hubspot"
API_HOST = "api.hubapi.com"
API_BASE = "https://api.hubapi.com"
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
    """Talks to https://api.hubapi.com with the surrogate credential."""

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
        if path=="crm/v3/objects/contacts":
            lim=int(params.get("limit",20)); return {"results": data["contacts"][:lim], "total": len(data["contacts"])}
        m=re.fullmatch(r"crm/v3/objects/contacts/([^/]+)", path)
        if m:
            for x in data["contacts"]:
                if str(x["id"])==m.group(1): return dict(x)
            raise ApiError(404,"Not Found","No such contact in demo data.")
        if path=="crm/v3/objects/companies":
            lim=int(params.get("limit",20)); return {"results": data["companies"][:lim], "total": len(data["companies"])}
        if path=="crm/v3/objects/deals":
            lim=int(params.get("limit",20)); return {"results": data["deals"][:lim], "total": len(data["deals"])}
        m=re.fullmatch(r"crm/v3/objects/deals/([^/]+)", path)
        if m:
            for x in data["deals"]:
                if str(x["id"])==m.group(1): return dict(x)
            raise ApiError(404,"Not Found","No such deal in demo data.")
        if path=="crm/v3/pipelines/deals": return dict(data["pipelines"])
        raise ApiError(404,"Not in demo",f"No demo fixture for GET {path}")
    def post(self, path, body):
        if path=="crm/v3/objects/deals/search":
            stage=None
            try: stage=body["filterGroups"][0]["filters"][0]["value"]
            except Exception: pass
            res=[d for d in self.data["deals"] if not stage or (d.get("properties") or {}).get("dealstage")==stage]
            return {"results": res, "total": len(res)}
        if path=="crm/v3/objects/contacts":
            created={"id":"demo_new_contact","properties": dict((body or {}).get("properties") or {}),"demo":True,"simulated":True}
            return created
        raise ApiError(404,"Not in demo",f"No demo fixture for POST {path}")

def emit(payload, exit_code: int = 0) -> None:
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(exit_code)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="DealSignal for HubSpot for Muse")
    parser.add_argument("--demo", action="store_true",
                        help="run against bundled fictional demo data")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    p=sub.add_parser("contacts"); p.add_argument("--limit",type=int,default=20)
    p=sub.add_parser("contact"); p.add_argument("id")
    p=sub.add_parser("companies"); p.add_argument("--limit",type=int,default=20)
    p=sub.add_parser("deals"); p.add_argument("--stage",default=None); p.add_argument("--limit",type=int,default=20)
    p=sub.add_parser("deal"); p.add_argument("id")
    sub.add_parser("pipeline")
    p=sub.add_parser("create-contact"); p.add_argument("--email",required=True); p.add_argument("--first-name",default=None); p.add_argument("--last-name",default=None); p.add_argument("--company",default=None); p.add_argument("--yes",action="store_true")
    args = parser.parse_args(argv)

    if not args.demo:
        license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try:
        return run_command(client, args)
    except ApiError as exc:
        emit({"ok": False, "error": exc.title or "api_error",
              "status": exc.status, "detail": exc.detail}, 1)



def _p(d): return d.get("properties") or {}
def cur_contact(d): p=_p(d); return {"id": d.get("id"), "email": p.get("email"), "first_name": p.get("firstname"), "last_name": p.get("lastname"), "company": p.get("company"), "phone": p.get("phone"), "lifecycle_stage": p.get("lifecyclestage"), "created": p.get("createdate"), "updated": p.get("lastmodifieddate")}
def cur_company(d): p=_p(d); return {"id": d.get("id"), "name": p.get("name"), "domain": p.get("domain"), "industry": p.get("industry"), "city": p.get("city"), "created": p.get("createdate")}
def cur_deal(d): p=_p(d); return {"id": d.get("id"), "name": p.get("dealname"), "amount": p.get("amount"), "stage": p.get("dealstage"), "pipeline": p.get("pipeline"), "close_date": p.get("closedate"), "created": p.get("createdate")}

def run_command(client, args) -> int:

    cmd=args.command
    if cmd=="status":
        c=client.get("crm/v3/objects/contacts",params={"limit":1}); d=client.get("crm/v3/objects/deals",params={"limit":1}); co=client.get("crm/v3/objects/companies",params={"limit":1})
        emit({"ok":True,"connected":True,"service":"HubSpot","demo":isinstance(client,DemoClient),"contacts_sampled":len(c.get("results",[])),"deals_sampled":len(d.get("results",[])),"companies_sampled":len(co.get("results",[]))})
    if cmd=="contacts":
        r=client.get("crm/v3/objects/contacts",params={"limit":args.limit,"properties":"firstname,lastname,email,company,phone,lifecyclestage,createdate,lastmodifieddate"})
        emit({"contacts":[cur_contact(x) for x in r.get("results",[])],"total_returned":len(r.get("results",[]))})
    if cmd=="contact":
        r=client.get(f"crm/v3/objects/contacts/{args.id}",params={"properties":"firstname,lastname,email,company,phone,lifecyclestage,createdate,lastmodifieddate"}); emit({"contact":cur_contact(r)})
    if cmd=="companies":
        r=client.get("crm/v3/objects/companies",params={"limit":args.limit,"properties":"name,domain,industry,city,createdate"})
        emit({"companies":[cur_company(x) for x in r.get("results",[])],"total_returned":len(r.get("results",[]))})
    if cmd=="deals":
        if args.stage:
            body={"filterGroups":[{"filters":[{"propertyName":"dealstage","operator":"EQ","value":args.stage}]}],"properties":["dealname","amount","dealstage","pipeline","closedate","createdate"],"limit":args.limit}
            r=client.post("crm/v3/objects/deals/search",body)
        else:
            r=client.get("crm/v3/objects/deals",params={"limit":args.limit,"properties":"dealname,amount,dealstage,pipeline,closedate,createdate"})
        emit({"deals":[cur_deal(x) for x in r.get("results",[])],"total_returned":len(r.get("results",[]))})
    if cmd=="deal":
        r=client.get(f"crm/v3/objects/deals/{args.id}",params={"properties":"dealname,amount,dealstage,pipeline,closedate,createdate"}); emit({"deal":cur_deal(r)})
    if cmd=="pipeline":
        r=client.get("crm/v3/pipelines/deals"); emit({"pipelines":r.get("results",r)})
    if cmd=="create-contact":
        props={"email":args.email}
        if args.first_name: props["firstname"]=args.first_name
        if args.last_name: props["lastname"]=args.last_name
        if args.company: props["company"]=args.company
        if not args.yes: emit({"ok":False,"approval_required":True,"action":"create_contact","will_create":{"properties":props},"message":"Nothing was changed. Show this summary to the owner and re-run with --yes only after they approve this exact contact."},2)
        created=client.post("crm/v3/objects/contacts",{"properties":props})
        cid=created.get("id")
        back=None
        if cid and not created.get("simulated"):
            try: back=cur_contact(client.get(f"crm/v3/objects/contacts/{cid}"))
            except Exception: back=None
        emit({"ok":True,"created":back or created,"demo":isinstance(client,DemoClient)})
    emit({"ok":False,"error":"unknown_command","detail":cmd},1)


if __name__ == "__main__":
    raise SystemExit(main())
