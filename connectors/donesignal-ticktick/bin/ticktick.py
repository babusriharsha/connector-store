#!/usr/bin/env python3
"""DoneSignal for TickTick connector CLI for Muse (Plugvana, CALL SNAP SYSTEMS LLC).

Reads projects/tasks and adds/completes tasks (approval-gated) via the
TickTick Open API (https://api.ticktick.com/open/v1), OAuth2 bearer
surrogate from Muse's dynamic-credential flow (connection
`custom.ticktick`). The token never appears in this file, arguments, or
output.

FLAGGED: TickTick's own Open API docs describe task completion at
POST /open/v1/project/{projectId}/task/{taskId}/complete. This package
follows its spec's POST /task/{id}/complete; verify on first live use
(see CONNECTOR.md Limits).

Exit codes: 0 success, 1 API/runtime error, 2 confirmation gate, 3 license.
Demo: python3 ticktick.py --demo tasks --project proj_home
"""
from __future__ import annotations
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_PATH = os.path.join(BIN_DIR, "demo_data.json")
CONNECTION_NAME = "custom.ticktick"
API_HOST = "api.ticktick.com"
API_BASE = "https://api.ticktick.com/open/v1"
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
        url = f"{API_BASE}/{path}" if path else API_BASE
        if params: url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
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
                title = payload.get("errorId") or payload.get("title") or ""
                detail = payload.get("errorMessage") or payload.get("detail") or raw[:300]
            else: title, detail = "", raw[:300]
            raise ApiError(exc.code, str(title), str(detail)) from exc
    def get(self, path, params=None): return self.request("GET", path, params=params)
    def post(self, path, body=None): return self.request("POST", path, body=body if body is not None else {})

class DemoClient:
    def __init__(self):
        with open(DEMO_PATH, encoding="utf-8") as fh: self.data = json.load(fh)
    def get(self, path, params=None):
        d = self.data
        if path == "project": return list(d["projects"])
        m = re.fullmatch(r"project/([^/]+)/data", path)
        if m: return json.loads(json.dumps(d["project_data"].get(m.group(1), {"project": None, "tasks": []})))
        m = re.fullmatch(r"project/([^/]+)", path)
        if m:
            for p in d["projects"]:
                if p["id"] == m.group(1): return dict(p)
            raise ApiError(404, "Not in demo", f"No demo project {m.group(1)}")
        raise ApiError(404, "Not in demo", f"No demo fixture for GET {path}")
    def post(self, path, body=None):
        if path == "task":
            created = dict(body or {}); created.update({"id": "demo_new_task", "status": 0, "demo": True, "simulated": True})
            return created
        m = re.fullmatch(r"task/([^/]+)/complete", path)
        if m: return {"id": m.group(1), "status": 2, "demo": True, "simulated": True}
        raise ApiError(404, "Not in demo", f"No demo fixture for POST {path}")

def emit(payload, exit_code=0):
    print(json.dumps(payload, indent=2, default=str)); raise SystemExit(exit_code)

def proposal(action, proposed):
    emit({"ok": False, "approval_required": True, "action": action, "proposed": proposed,
          "message": "Nothing was changed. Show this to the owner; re-run with --yes only after they approve this exact change."}, 2)

def curate_task(t):
    return {"id": t.get("id"), "title": t.get("title"), "project_id": t.get("projectId"),
            "status": t.get("status"), "priority": t.get("priority"), "due_date": t.get("dueDate"),
            "start_date": t.get("startDate"), "completed_time": t.get("completedTime"),
            "content_excerpt": (t.get("content") or "")[:200]}

def project_tasks(client, project_id):
    data = client.get(f"project/{project_id}/data")
    return data if isinstance(data, dict) else {"tasks": []}

def run_command(client, args):
    demo = isinstance(client, DemoClient)
    if args.command == "status":
        projects = client.get("project")
        emit({"ok": True, "connected": True, "project_count": len(projects),
              "projects": [{"id": p.get("id"), "name": p.get("name")} for p in projects], "demo": demo})
    if args.command == "projects":
        projects = client.get("project")
        emit({"ok": True, "projects": [{"id": p.get("id"), "name": p.get("name"), "color": p.get("color"),
              "view_mode": p.get("viewMode"), "kind": p.get("kind"), "closed": p.get("closed")} for p in projects], "total": len(projects)})
    if args.command == "tasks":
        data = project_tasks(client, args.project)
        tasks = [t for t in data.get("tasks", []) if t.get("status") in (0, None)]
        emit({"ok": True, "project": args.project, "tasks": [curate_task(t) for t in tasks], "total": len(tasks)})
    if args.command == "completed":
        data = project_tasks(client, args.project)
        if "completedTasks" in data:
            done, source = data.get("completedTasks") or [], "project_data.completedTasks"
        else:
            done = [t for t in data.get("tasks", []) if t.get("status") == 2]
            source = "filtered project tasks with status == 2 (no completedTasks in payload)"
        emit({"ok": True, "project": args.project, "completed": [curate_task(t) for t in done], "total": len(done), "source": source})
    if args.command == "add-task":
        body = {"title": args.title, "projectId": args.project}
        if args.content: body["content"] = args.content
        if args.due: body["dueDate"] = args.due
        if args.priority is not None: body["priority"] = args.priority
        if not args.yes: proposal("add_task", body)
        created = client.post("task", body)
        if demo: emit({"ok": True, "created": created, "demo": True, "simulated": True})
        data = project_tasks(client, args.project)
        found = [t for t in data.get("tasks", []) if str(t.get("id")) == str(created.get("id"))]
        emit({"ok": True, "created": curate_task(created), "verified_read_back": bool(found)})
    if args.command == "complete-task":
        if not args.yes: proposal("complete_task", {"task_id": args.task_id, "project_id": args.project,
              "endpoint": f"POST /task/{args.task_id}/complete",
              "warning": "Completing is a state change the owner may not expect to be undone from here; confirm this exact task."})
        result = client.post(f"task/{args.task_id}/complete")
        if demo: emit({"ok": True, "completed": result, "demo": True, "simulated": True})
        data = project_tasks(client, args.project)
        done_ids = [str(t.get("id")) for t in (data.get("completedTasks") or [])] + \
                   [str(t.get("id")) for t in data.get("tasks", []) if t.get("status") == 2]
        emit({"ok": True, "completed": result, "verified_read_back": str(args.task_id) in done_ids})
    raise ApiError(400, "unknown_command", str(args.command))

def main(argv=None):
    parser = argparse.ArgumentParser(description="DoneSignal for TickTick for Muse")
    parser.add_argument("--demo", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); sub.add_parser("projects")
    p = sub.add_parser("tasks"); p.add_argument("--project", required=True)
    p = sub.add_parser("completed"); p.add_argument("--project", required=True)
    p = sub.add_parser("add-task"); p.add_argument("--project", required=True); p.add_argument("--title", required=True)
    p.add_argument("--content", default=None); p.add_argument("--due", default=None); p.add_argument("--priority", type=int, default=None); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("complete-task"); p.add_argument("task_id"); p.add_argument("--project", required=True); p.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo: license_check.enforce()
    client = DemoClient() if args.demo else LiveClient()
    try: return run_command(client, args)
    except ApiError as exc: emit({"ok": False, "error": exc.title or "api_error", "status": exc.status, "detail": exc.detail}, 1)

if __name__ == "__main__":
    raise SystemExit(main())
