#!/usr/bin/env python3
"""LegacySignal for COBOL CLI — read-only COBOL estate analysis, stdlib only.

Commands: inventory, document, callmap, copybooks, impact, db2, jcl,
deadcode, modernize. Every command prints clean JSON to stdout.

READ-ONLY GUARANTEE: no command ever modifies a source file. The only
writes are report files written by `document --out <dir>` and
`modernize --out <dir>`, into the output directory the caller names —
never into the source folder by default. In demo mode there is no
default --out either: a report is written only when --out is given
explicitly.

Parsing is heuristic text parsing (see CONNECTOR.md "Honest status"):
fixed-format basics, free-format partially supported, EXEC SQL
extraction is pattern-based and may miss dynamic SQL. Results are a
documentation aid, not a compiler.
"""
from __future__ import annotations
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check
BIN = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BIN, "samples")
PROG_EXTS = (".cob", ".cbl")
COPY_EXTS = (".cpy",)
JCL_EXTS = (".jcl",)

def emit(p, code=0):
    print(json.dumps(p, indent=2, default=str)); raise SystemExit(code)
def err(msg):
    emit({"ok": False, "error": msg}, 1)

# ---------------------------------------------------------------- parsing
def code_of(line):
    """Strip the fixed-format sequence/indicator area (cols 1-7)."""
    if len(line) > 7 and (line[:6].strip() == "" or line[:6].isdigit()):
        return line[7:]
    return line

def read_file(path):
    return open(path, encoding="utf-8", errors="replace").read()

def list_files(root):
    if not os.path.isdir(root):
        err(f"estate folder not found: {root}")
    out = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isfile(p) and os.path.splitext(name)[1].lower() in PROG_EXTS + COPY_EXTS + JCL_EXTS:
            out.append(p)
    return out

def ftype(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in PROG_EXTS: return "program"
    if ext in COPY_EXTS: return "copybook"
    return "jcl"

def comments_of(text):
    out = []
    for raw in text.splitlines():
        c = code_of(raw)
        s = raw.strip()
        if s.startswith("*") or (len(raw) > 6 and raw[6] == "*"):
            txt = s.lstrip("*").strip()
            if txt: out.append(txt)
        elif c.strip().startswith("*"):
            txt = c.strip().lstrip("*").strip()
            if txt: out.append(txt)
    return out

def parse_sql(text):
    """EXEC SQL blocks -> list of {verb, table}."""
    found = []
    up = text.upper()
    for m in re.finditer(r"EXEC\s+SQL(.*?)END-EXEC", up, re.S):
        block = m.group(1)
        verb = None; table = None
        mv = re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", block)
        if mv: verb = mv.group(1)
        if verb == "INSERT":
            mt = re.search(r"INSERT\s+INTO\s+([A-Z0-9_]+)", block)
            table = mt.group(1) if mt else None
        elif verb == "UPDATE":
            mt = re.search(r"UPDATE\s+([A-Z0-9_]+)", block)
            table = mt.group(1) if mt else None
        elif verb == "DELETE":
            mt = re.search(r"DELETE\s+FROM\s+([A-Z0-9_]+)", block)
            table = mt.group(1) if mt else None
        elif verb == "SELECT":
            mt = re.search(r"\bFROM\s+([A-Z0-9_]+)", block)
            table = mt.group(1) if mt else None
        if verb and table:
            found.append({"verb": verb, "table": table})
    return found

def parse_program(path):
    text = read_file(path)
    up = text.upper()
    lines = text.splitlines()
    mp = re.search(r"PROGRAM-ID\.\s*([A-Z0-9_-]+)", up)
    pid = mp.group(1) if mp else os.path.splitext(os.path.basename(path))[0].upper()
    copies = sorted(set(re.findall(r"\bCOPY\s+([A-Z0-9_-]+)", up)))
    calls = sorted(set(re.findall(r"\bCALL\s+['\"]([A-Z0-9_-]+)['\"]", up)))
    selects = re.findall(r"\bSELECT\s+([A-Z0-9_-]+)\s+ASSIGN", up)
    fds = re.findall(r"(?m)^\s*FD\s+([A-Z0-9_-]+)", up)
    cics = [c for c in re.findall(r"EXEC\s+CICS\s+([A-Z]+)", up)]
    sql = parse_sql(text)
    paragraphs = []
    in_proc = False
    for raw in lines:
        c = code_of(raw).rstrip()
        if "PROCEDURE DIVISION" in c.upper(): in_proc = True; continue
        if not in_proc: continue
        m = re.match(r"^\s{0,4}([A-Z][A-Z0-9-]{2,})\.\s*$", c.upper())
        if m and m.group(1) not in ("PROCEDURE", "END-EXEC", "END-IF", "END-PERFORM", "END-EVALUATE", "GOBACK", "STOP", "EXIT"):
            paragraphs.append(m.group(1))
    return {
        "file": os.path.basename(path), "path": path, "type": "program",
        "program_id": pid, "lines": len(lines), "comments": comments_of(text),
        "copybooks": copies, "calls": calls, "selects": selects, "fds": fds,
        "paragraphs": paragraphs, "sql": sql,
        "cics": sorted(set(cics)), "cics_count": len(cics),
        "has_error_handling": any(k in up for k in ("HANDLE-ERROR", "ERROR", "SQLCODE", "ON EXCEPTION", "INVALID KEY")),
    }

def parse_copybook(path):
    text = read_file(path)
    lines = text.splitlines()
    fields = []
    for raw in lines:
        c = code_of(raw)
        m = re.match(r"^\s*(01|03|05|07|10|15|20|49)\s+([A-Z0-9_-]+)(.*)$", c.upper())
        if not m: continue
        rest = m.group(3)
        mp = re.search(r"\bPIC\s+(\S+)", rest)
        pic = mp.group(1).rstrip(".") if mp else None
        fields.append({"level": m.group(1), "name": m.group(2), "pic": pic})
    return {"file": os.path.basename(path), "path": path, "type": "copybook",
            "name": os.path.splitext(os.path.basename(path))[0].upper(),
            "lines": len(lines), "comments": comments_of(text), "fields": fields}

def parse_jcl(path):
    text = read_file(path)
    lines = text.splitlines()
    steps = []
    cur = None
    for raw in lines:
        up = raw.upper()
        m = re.match(r"^//([A-Z0-9_-]+)\s+EXEC\s+PGM=([A-Z0-9_-]+)", up)
        if m:
            cur = {"step": m.group(1), "program": m.group(2), "datasets": []}
            steps.append(cur); continue
        m = re.match(r"^//([A-Z0-9_-]+)\s+DD\s+.*DSN=([A-Z0-9_.\(\)]+)", up)
        if m and cur is not None:
            cur["datasets"].append({"dd": m.group(1), "dsn": m.group(2)})
    mj = re.match(r"//([A-Z0-9_-]+)\s+JOB", text.upper())
    return {"file": os.path.basename(path), "path": path, "type": "jcl",
            "job": mj.group(1) if mj else os.path.splitext(os.path.basename(path))[0].upper(),
            "lines": len(lines), "comments": comments_of(text), "steps": steps}

def load_estate(root):
    progs, copies, jcls = [], [], []
    for p in list_files(root):
        t = ftype(p)
        if t == "program": progs.append(parse_program(p))
        elif t == "copybook": copies.append(parse_copybook(p))
        else: jcls.append(parse_jcl(p))
    return progs, copies, jcls

def summary_of(item):
    if item["comments"]:
        return item["comments"][0]
    if item["type"] == "program":
        return f"COBOL program {item['program_id']}."
    return f"{item['type']} {item.get('name') or item.get('job')}."

# ---------------------------------------------------------------- commands
def cmd_inventory(root):
    progs, copies, jcls = load_estate(root)
    items = []
    for it in progs + copies + jcls:
        items.append({"file": it["file"], "type": it["type"], "lines": it["lines"],
                      "program_id": it.get("program_id") or it.get("name") or it.get("job"),
                      "summary": summary_of(it)})
    items.sort(key=lambda x: x["file"])
    emit({"ok": True, "estate": root, "count": len(items), "files": items})

def doc_dict(p):
    tables = {}
    for s in p["sql"]:
        tables.setdefault(s["table"], []).append(s["verb"])
    return {"program_id": p["program_id"], "file": p["file"],
            "purpose": p["comments"], "lines": p["lines"],
            "files": [{"select": s} for s in p["selects"]] + [{"fd": f} for f in p["fds"]],
            "select_names": p["selects"], "fd_names": p["fds"],
            "copybooks": p["copybooks"], "called_programs": p["calls"],
            "paragraphs": p["paragraphs"],
            "db2": [{"table": t, "verbs": sorted(set(v))} for t, v in sorted(tables.items())],
            "cics_commands": p["cics"]}

def write_md(out_dir, name, title, body_lines):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# {title}\n\n" + "\n".join(body_lines) + "\n")
    return path

def cmd_document(root, name, out_dir):
    progs, _, _ = load_estate(root)
    name = name.upper()
    p = next((x for x in progs if x["program_id"] == name or
              os.path.splitext(x["file"])[0].upper() == name), None)
    if not p: err(f"program not found in estate: {name}")
    d = doc_dict(p)
    written = None
    if out_dir:
        body = [f"**Purpose:** {' '.join(d['purpose']) or 'No header comments found.'}", "",
                f"**Lines:** {d['lines']}", "",
                "## Files", *[f"- {k}" for k in d["select_names"] + d["fd_names"]], "",
                "## Copybooks", *[f"- {c}" for c in d["copybooks"]], "",
                "## Called programs", *[f"- {c}" for c in d["called_programs"]], "",
                "## Paragraphs", *[f"- {x}" for x in d["paragraphs"]], "",
                "## DB2 tables", *[f"- {t['table']}: {', '.join(t['verbs'])}" for t in d["db2"]], "",
                "## CICS commands", *[f"- {c}" for c in d["cics_commands"]]]
        written = write_md(out_dir, f"{d['program_id']}.md", f"{d['program_id']} — generated documentation", body)
    emit({"ok": True, "document": d, "report_written": written})

def cmd_callmap(root):
    progs, _, _ = load_estate(root)
    graph = {p["program_id"]: p["calls"] for p in progs}
    called = set(c for v in graph.values() for c in v)
    roots = [pid for pid in graph if pid not in called] or list(graph)
    tree_lines = []
    def walk(pid, depth, seen):
        tree_lines.append("  " * depth + ("-> " if depth else "") + pid)
        if pid in seen: return
        for nxt in graph.get(pid, []):
            walk(nxt, depth + 1, seen | {pid})
    for r in sorted(roots): walk(r, 0, set())
    mermaid = ["graph TD"] + [f"    {a} --> {b}" for a, cs in sorted(graph.items()) for b in cs]
    emit({"ok": True, "graph": graph, "tree": "\n".join(tree_lines),
          "mermaid": "\n".join(mermaid)})

def cmd_copybooks(root):
    progs, copies, _ = load_estate(root)
    out = []
    for c in copies:
        used_by = sorted(p["program_id"] for p in progs if c["name"] in p["copybooks"])
        out.append({"copybook": c["name"], "file": c["file"], "used_by": used_by,
                    "fields": c["fields"]})
    emit({"ok": True, "copybooks": out})

def cmd_impact(root, name):
    progs, copies, jcls = load_estate(root)
    name = name.upper()
    graph = {p["program_id"]: p["calls"] for p in progs}
    direct_callers = sorted(pid for pid, cs in graph.items() if name in cs)
    # transitive callers via reverse BFS
    trans, stack = set(direct_callers), list(direct_callers)
    while stack:
        cur = stack.pop()
        for pid, cs in graph.items():
            if cur in cs and pid not in trans:
                trans.add(pid); stack.append(pid)
    used_by = sorted(p["program_id"] for p in progs if name in p["copybooks"])
    field_in = sorted(c["name"] for c in copies
                      if any(f["name"] == name for f in c["fields"]))
    mentioned_in = []
    for it in progs + copies:
        txt = read_file(it["path"]).upper()
        if re.search(r"(?<![A-Z0-9-])" + re.escape(name) + r"(?![A-Z0-9-])", txt):
            mentioned_in.append(it["file"])
    jcl_jobs = sorted(j["job"] for j in jcls
                      if any(s["program"] == name for s in j["steps"]))
    emit({"ok": True, "name": name,
          "direct_callers": direct_callers,
          "transitive_callers": sorted(trans),
          "copybook_used_by": used_by if any(c["name"] == name for c in copies) else [],
          "defined_as_field_in": field_in,
          "jcl_jobs": jcl_jobs,
          "referenced_in_files": sorted(set(mentioned_in))})

def cmd_db2(root):
    progs, _, _ = load_estate(root)
    matrix = {}
    for p in progs:
        for s in p["sql"]:
            e = matrix.setdefault(s["table"], {"verbs": set(), "programs": set()})
            e["verbs"].add(s["verb"]); e["programs"].add(p["program_id"])
    emit({"ok": True, "tables": {t: {"verbs": sorted(v["verbs"]),
          "programs": sorted(v["programs"])} for t, v in sorted(matrix.items())}})

def cmd_jcl(root):
    _, _, jcls = load_estate(root)
    emit({"ok": True, "jobs": [{"job": j["job"], "file": j["file"], "steps": j["steps"]} for j in jcls]})

def cmd_deadcode(root):
    progs, copies, jcls = load_estate(root)
    called = set(c for p in progs for c in p["calls"])
    in_jcl = set(s["program"] for j in jcls for s in j["steps"])
    used_copies = set(c for p in progs for c in p["copybooks"])
    dead_p = sorted(p["program_id"] for p in progs
                    if p["program_id"] not in called and p["program_id"] not in in_jcl)
    dead_c = sorted(c["name"] for c in copies if c["name"] not in used_copies)
    emit({"ok": True, "dead_programs": dead_p, "dead_copybooks": dead_c,
          "note": "A program run only from outside this estate (e.g. a scheduler not in the folder) can look dead here — verify before deleting anything. This tool never deletes."})

FORMULA = "complexity = lines + 2*paragraphs + 5*SQL statements + 5*CICS commands + 3*CALL statements"

def modernize_rows(root):
    progs, _, _ = load_estate(root)
    rows = []
    for p in progs:
        score = p["lines"] + 2 * len(p["paragraphs"]) + 5 * len(p["sql"]) + 5 * p["cics_count"] + 3 * len(p["calls"])
        risks = []
        if len(p["sql"]) >= 3: risks.append("heavy SQL use — plan data-access migration carefully")
        if p["cics_count"]: risks.append("CICS commands present — online behaviour needs a replacement path")
        if not p["has_error_handling"]: risks.append("no error-handling keywords found (no SQLCODE/ON EXCEPTION/HANDLE-ERROR) — add error handling in migration")
        if not p["calls"] and not p["sql"] and not p["cics_count"]: risks.append("self-contained calculation — usually the easiest kind to migrate first")
        if not risks: risks.append("no standout risks from the heuristic scan")
        rows.append({"program_id": p["program_id"], "file": p["file"], "lines": p["lines"],
                     "paragraphs": len(p["paragraphs"]), "sql_statements": len(p["sql"]),
                     "cics_commands": p["cics_count"], "calls": len(p["calls"]),
                     "complexity_score": score, "risk_notes": risks})
    rows.sort(key=lambda r: -r["complexity_score"])
    return rows

def cmd_modernize(root, out_dir):
    rows = modernize_rows(root)
    written = None
    total = sum(r["complexity_score"] for r in rows)
    brief = (f"{len(rows)} program(s) assessed. Highest complexity: "
             f"{rows[0]['program_id']} (score {rows[0]['complexity_score']}). "
             f"Estate total complexity {total}. Start with the lowest-score, "
             "self-contained programs; treat heavy-SQL and CICS programs as later phases.") if rows else "No programs found."
    if out_dir:
        body = [f"**Formula:** {FORMULA}", "", f"**Brief:** {brief}", ""]
        for r in rows:
            body += [f"## {r['program_id']} — score {r['complexity_score']}",
                     f"- Lines: {r['lines']}, paragraphs: {r['paragraphs']}, SQL: {r['sql_statements']}, CICS: {r['cics_commands']}, calls: {r['calls']}",
                     *[f"- Risk: {x}" for x in r["risk_notes"]], ""]
        written = write_md(out_dir, "modernisation-brief.md", "Modernisation brief", body)
    emit({"ok": True, "formula": FORMULA, "programs": rows,
          "migration_brief": brief, "report_written": written})

# ---------------------------------------------------------------- main
def main(argv):
    demo = "--demo" in argv
    argv = [a for a in argv if a != "--demo"]
    out_dir = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv): err("--out needs a directory")
        out_dir = argv[i + 1]; del argv[i:i + 2]
    if not demo: license_check.enforce()
    if len(argv) < 2:
        err("usage: legacysignal.py [--demo] inventory|document|callmap|copybooks|impact|db2|jcl|deadcode|modernize [name] [estate-folder] [--out dir]")
    cmd = argv[1]
    rest = argv[2:]
    def root_for(idx=0):
        if demo:
            return rest[idx] if len(rest) > idx else SAMPLES
        if len(rest) > idx: return rest[idx]
        err(f"{cmd} needs an estate folder path in live mode")
    if cmd == "inventory": cmd_inventory(root_for(0))
    elif cmd == "document":
        if not rest: err("document needs a program name")
        cmd_document(root_for(1), rest[0], out_dir)
    elif cmd == "callmap": cmd_callmap(root_for(0))
    elif cmd == "copybooks": cmd_copybooks(root_for(0))
    elif cmd == "impact":
        if not rest: err("impact needs a program, copybook or field name")
        cmd_impact(root_for(1), rest[0])
    elif cmd == "db2": cmd_db2(root_for(0))
    elif cmd == "jcl": cmd_jcl(root_for(0))
    elif cmd == "deadcode": cmd_deadcode(root_for(0))
    elif cmd == "modernize": cmd_modernize(root_for(0), out_dir)
    else: err(f"unknown command: {cmd}")

if __name__ == "__main__":
    main(sys.argv)
