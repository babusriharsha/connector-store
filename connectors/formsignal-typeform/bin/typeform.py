#!/usr/bin/env python3
"""FormSignal for Typeform connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

READ-ONLY connector: lists forms/workspaces, inspects a form, and
summarises responses via the Typeform API (https://api.typeform.com),
personal access token bearer surrogate from Muse's dynamic-credential
flow (connection `custom.typeform`). There are no write commands and no
--yes flag anywhere in this file, by design.

Exit codes: 0 success, 1 API/runtime error, 3 license (no gate code 2:
nothing here writes).
Demo: python3 typeform.py --demo responses --form form_feedback
"""
from __future__ import annotations
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONNECTION_NAME = "custom.typeform"
API_HOST = "api.typeform.com"
API_BASE = "https://api.typeform.com"
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

class LiveClient:
    def __init__(self):
        sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
        from dynamic_credentials import add_surrogate_to_request, read_json_response
        self._add_surrogate = add_surrogate_to_request
        self._read_json = read_json_response
    def request(self, method, path, params=None, body=None):
        if method != "GET":
            raise ApiError(405, "read_only", "FormSignal for Typeform is read-only; no write methods exist.")
        url = f"{API_BASE}/{path}" if path else API_BASE
        if params: url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, method="GET")
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
                title = payload.get("code") or payload.get("title") or ""
                detail = payload.get("description") or payload.get("detail") or raw[:300]
            else: title, detail = "", raw[:300]
            raise ApiError(exc.code, str(title), str(detail)) from exc
    def get(self, path, params=None): return self.request("GET", path, params=params)
    def post(self, path, body=None): raise ApiError(405, "read_only", "FormSignal for Typeform is read-only; no write methods exist.")

class DemoClient:
    def __init__(self):
        with open(DEMO_PATH, encoding="utf-8") as fh: self.data = json.load(fh)
    def get(self, path, params=None):
        d = self.data
        if path == "me": return dict(d["me"])
        if path == "forms": return {"total_items": len(d["forms"]), "page_count": 1, "items": list(d["forms"])}
        if path == "workspaces": return {"total_items": len(d["workspaces"]), "page_count": 1, "items": list(d["workspaces"])}
        m = re.fullmatch(r"forms/([^/]+)/responses", path)
        if m: return json.loads(json.dumps(d["responses"].get(m.group(1), {"total_items": 0, "items": []})))
        m = re.fullmatch(r"forms/([^/]+)", path)
        if m:
            detail = d["form_detail"].get(m.group(1))
            if detail: return json.loads(json.dumps(detail))
            raise ApiError(404, "Not in demo", f"No demo form {m.group(1)}")
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body=None): raise ApiError(405, "read_only", "FormSignal for Typeform is read-only; no write methods exist.")

def emit(payload, exit_code=0):
    print(json.dumps(payload, indent=2, default=str)); raise SystemExit(exit_code)

def trim_answer(a):
    ans = {"field_id": (a.get("field") or {}).get("id") if isinstance(a.get("field"), dict) else None,
           "type": a.get("type")}
    for key in ("text", "email", "number", "boolean", "date"):
        if a.get(key) is not None:
            v = a[key]
            ans["value_excerpt"] = (str(v)[:120] + "…") if isinstance(v, str) and len(v) > 120 else v
            break
    if a.get("choice"):
        ans["value_excerpt"] = (a["choice"] or {}).get("label")
    if a.get("choices"):
        ans["value_excerpt"] = (a["choices"] or {}).get("labels")
    return ans

def run_command(client, args):
    demo = isinstance(client, DemoClient)
    if args.command == "status":
        me = client.get("me")
        emit({"ok": True, "connected": True, "me": {"user_id": me.get("user_id"), "email": me.get("email"),
              "language": me.get("language")}, "read_only": True, "demo": demo})
    if args.command == "forms":
        page = client.get("forms")
        items = page.get("items", [])
        emit({"ok": True, "forms": [{"id": f.get("id"), "title": f.get("title"), "last_updated_at": f.get("last_updated_at"),
              "theme": (f.get("theme") or {}).get("href") if isinstance(f.get("theme"), dict) else None} for f in items],
              "total": page.get("total_items", len(items))})
    if args.command == "form":
        f = client.get(f"forms/{args.form_id}")
        emit({"ok": True, "form": {"id": f.get("id"), "title": f.get("title"), "type": f.get("type"),
              "fields": [{"id": fld.get("id"), "title": fld.get("title"), "type": fld.get("type")} for fld in (f.get("fields") or []) if isinstance(fld, dict)],
              "settings": f.get("settings"), "last_updated_at": f.get("last_updated_at")}})
    if args.command == "responses":
        form = client.get(f"forms/{args.form}")
        field_count = len(form.get("fields") or [])
        page = client.get(f"forms/{args.form}/responses", params={"page_size": max(args.limit, 1)})
        items = page.get("items", [])
        total = page.get("total_items", len(items))
        submitted = [i for i in items if i.get("submitted_at")]
        # Completion: submitted share of returned responses; answer-depth
        # (answers vs form fields) is reported alongside, labelled.
        completion_rate = round(len(submitted) / len(items), 4) if items else None
        latest = []
        for item in items[: args.limit]:
            answers = item.get("answers") or []
            latest.append({"response_id": item.get("response_id"), "submitted_at": item.get("submitted_at"),
                           "landed_at": item.get("landed_at"), "answers_given": len(answers),
                           "answers": [trim_answer(a) for a in answers if isinstance(a, dict)]})
        emit({"ok": True, "form": args.form, "summary": {"total_responses": total, "returned": len(items),
              "submitted_in_returned": len(submitted), "completion_rate_of_returned": completion_rate,
              "form_field_count": field_count,
              "note": "Summary only: answers are trimmed excerpts; completion rate is over the returned page, not the form's lifetime analytics."},
              "latest": latest})
    if args.command == "workspaces":
        page = client.get("workspaces")
        items = page.get("items", [])
        emit({"ok": True, "workspaces": [{"id": w.get("id"), "name": w.get("name"), "forms_count": (w.get("forms") or {}).get("count") if isinstance(w.get("forms"), dict) else None} for w in items],
              "total": page.get("total_items", len(items))})
    raise ApiError(400, "unknown_command", str(args.command))

def main(argv=None):
    parser = argparse.ArgumentParser(description="FormSignal for Typeform for Muse (read-only)")
    parser.add_argument("--demo", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); sub.add_parser("forms"); sub.add_parser("workspaces")
    p = sub.add_parser("form"); p.add_argument("form_id")
    p = sub.add_parser("responses"); p.add_argument("--form", required=True); p.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    if not args.demo: license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try: return run_command(client, args)
    except ApiError as exc: emit({"ok": False, "error": exc.title or "api_error", "status": exc.status, "detail": exc.detail}, 1)

if __name__ == "__main__":
    raise SystemExit(main())
