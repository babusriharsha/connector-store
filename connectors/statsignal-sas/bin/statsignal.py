#!/usr/bin/env python3
"""StatSignal for SAS CLI — read-only SAS estate analysis, stdlib only.

READ-ONLY BY DESIGN: this tool only ever READS .sas source files and
.log files and prints JSON reports to stdout. It never writes to,
moves, renames or deletes a source file, and it never runs SAS code.
That is deliberate: estates in validated / regulated environments can
be inventoried and documented without touching the programs under
validation.

Parsing is text-based heuristics, stated plainly (see CONNECTOR.md):
macro resolution is name-based, and dynamic code (CALL EXECUTE,
macro-generated code, %INCLUDE of generated files) can hide lineage
from a static scan. Treat reports as a map to verify, not proof.

Commands: inventory, logscan, datamap, macrodoc, impact, estate.
Add --demo to run against the bundled fictional sample estate in
bin/samples/ (Northgate Clinical Analytics). Live mode takes a folder
path: `statsignal.py inventory /path/to/estate`.
"""
from __future__ import annotations
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check
BIN = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BIN, "samples")

def emit(p, code=0):
    print(json.dumps(p, indent=2, default=str)); raise SystemExit(code)
def err(msg):
    emit({"ok": False, "error": msg}, 1)

# ---------------------------------------------------------------- parsing

def strip_comments(text):
    """Remove /* */ blocks and full-line * ... ; comments for parsing."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    lines = []
    for ln in text.splitlines():
        if re.match(r"\s*\*[^%]", ln) and ln.rstrip().endswith(";"):
            continue
        lines.append(ln)
    return "\n".join(lines)

def norm_ds(name):
    name = name.strip().strip(";").lower()
    if not name or name.startswith("_") or name in ("_null_", "_data_"):
        return None
    if "." not in name:
        name = "work." + name
    return name

DS = r"([A-Za-z_][\w]*\.?[A-Za-z_][\w]*|[A-Za-z_][\w]*)"

def parse_program(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    code = strip_comments(raw)
    libnames = {}
    for m in re.finditer(r"\bLIBNAME\s+([A-Za-z_]\w*)\s+(?:'([^']+)'|\"([^\"]+)\")", code, re.I):
        libnames[m.group(1).lower()] = m.group(2) or m.group(3)
    macros_defined = [m.group(1).lower() for m in
                      re.finditer(r"%macro\s+([A-Za-z_]\w*)", code, re.I)]
    # Datasets created: DATA <ds>; statements.
    created = set()
    for m in re.finditer(r"\bDATA\s+" + DS + r"\s*;", code, re.I):
        d = norm_ds(m.group(1))
        if d: created.add(d)
    # Datasets read: SET / MERGE / UPDATE lists (up to the semicolon).
    reads = set()
    for m in re.finditer(r"\b(?:SET|MERGE|UPDATE)\s+([^;]+);", code, re.I):
        for tok in re.findall(r"[A-Za-z_][\w.]*", m.group(1)):
            if "(" in tok: continue
            d = norm_ds(tok)
            if d: reads.add(d)
    # PROC input/output: DATA= reads, OUT= creates.
    for m in re.finditer(r"\bDATA\s*=\s*" + DS, code, re.I):
        d = norm_ds(m.group(1))
        if d: reads.add(d)
    for m in re.finditer(r"\bOUT\s*=\s*" + DS, code, re.I):
        d = norm_ds(m.group(1))
        if d: created.add(d)
    librefs = sorted({d.split(".")[0] for d in reads | created} |
                     set(libnames) |
                     {m.group(1).lower() for m in
                      re.finditer(r"\bLIBNAME\s+([A-Za-z_]\w*)", code, re.I)})
    # Macro calls: %name occurrences that are not definitions/keywords.
    keywords = {"macro", "mend", "put", "if", "do", "end", "let", "sysfunc",
                "str", "nrstr", "eval", "include", "global", "local"}
    calls = {}
    for i, ln in enumerate(code.splitlines(), 1):
        for m in re.finditer(r"%([A-Za-z_]\w*)", ln):
            name = m.group(1).lower()
            if name in keywords: continue
            if re.search(r"%macro\s+$", ln[:m.start()], re.I): continue
            calls.setdefault(name, []).append(i)
    return {"file": os.path.basename(path), "path": path, "raw": raw,
            "code": code, "libnames": libnames, "librefs": librefs,
            "macros_defined": macros_defined, "macro_calls": calls,
            "reads": sorted(reads), "creates": sorted(created)}

def list_programs(folder):
    if not os.path.isdir(folder): err(f"folder not found: {folder}")
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(".sas")]

def purpose_of(raw):
    """Purpose text from the leading header comment block.

    Handles both one big /* ... */ block and the common SAS style of
    one /* ... */ comment per header line: the Purpose line plus its
    unlabelled continuation comment lines, borders stripped.
    """
    collecting, started = [], False
    for ln in raw.splitlines()[:60]:
        stripped = ln.strip()
        if started and not (stripped.startswith("/*") or stripped.startswith("*")):
            break
        clean = stripped.strip("/").strip("*").strip()
        m = re.match(r"Purpose\s*:\s*(.*)", clean, re.I)
        if m and not started:
            started = True; collecting.append(m.group(1)); continue
        if started:
            if re.match(r"(Program|Owner|Author|Date|Programmer)\s*:", clean, re.I):
                break
            if not clean: break
            collecting.append(clean)
    if not started: return None
    return " ".join(" ".join(collecting).split()) or None

def load_estate(folder):
    return [parse_program(p) for p in list_programs(folder)]

def lineage(programs):
    edges = {}
    for p in programs:
        for d in p["creates"]:
            edges.setdefault(d, {"created_by": [], "read_by": []})["created_by"].append(p["file"])
        for d in p["reads"]:
            edges.setdefault(d, {"created_by": [], "read_by": []})["read_by"].append(p["file"])
    return {k: edges[k] for k in sorted(edges)}

# ---------------------------------------------------------------- commands

def cmd_inventory(folder):
    out = []
    for p in load_estate(folder):
        out.append({"file": p["file"], "size_bytes": len(p["raw"].encode("utf-8")),
                    "lines": p["raw"].count("\n") + (0 if p["raw"].endswith("\n") else 1),
                    "purpose": purpose_of(p["raw"]),
                    "macros_defined": p["macros_defined"],
                    "macros_called": sorted(p["macro_calls"]),
                    "librefs_used": p["librefs"],
                    "libnames": p["libnames"]})
    emit({"ok": True, "folder": folder, "programs": out, "count": len(out)})

def cmd_logscan(logfile):
    if not os.path.isfile(logfile): err(f"log file not found: {logfile}")
    lines = open(logfile, encoding="utf-8", errors="replace").read().splitlines()
    def collect(prefix):
        items = []
        for i, ln in enumerate(lines):
            if ln.startswith(prefix):
                ctx = lines[i + 1].strip() if i + 1 < len(lines) else None
                items.append({"line": i + 1, "text": ln.strip(), "context": ctx})
        return items
    errors, warnings = collect("ERROR"), collect("WARNING:")
    notes = sum(1 for ln in lines if ln.startswith("NOTE:"))
    rt = re.search(r"real time\s+([\d:.]+\s*seconds?)", "\n".join(lines), re.I)
    ut = re.search(r"user cpu time\s+([\d:.]+\s*seconds?)", "\n".join(lines), re.I)
    verdict = "errors" if errors else ("warnings" if warnings else "clean")
    emit({"ok": True, "file": logfile,
          "counts": {"errors": len(errors), "warnings": len(warnings), "notes": notes},
          "errors": errors, "warnings": warnings,
          "real_time": rt.group(1) if rt else None,
          "user_cpu_time": ut.group(1) if ut else None,
          "verdict": verdict})

def cmd_datamap(folder):
    programs = load_estate(folder)
    libmap = {}
    for p in programs: libmap.update(p["libnames"])
    emit({"ok": True, "folder": folder,
          "libname_map": libmap,
          "programs": [{"file": p["file"], "reads": p["reads"],
                        "creates": p["creates"]} for p in programs],
          "lineage": lineage(programs)})

def macro_defs(programs):
    defs = {}
    for p in programs:
        for m in re.finditer(r"%macro\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*;",
                             p["code"], re.I):
            params = []
            if m.group(2):
                for part in m.group(2).split(","):
                    part = part.strip()
                    if not part: continue
                    if "=" in part:
                        nm, dv = part.split("=", 1)
                        params.append({"name": nm.strip(), "default": dv.strip()})
                    else:
                        params.append({"name": part, "default": None})
            defs[m.group(1).lower()] = {"defined_in": p["file"], "parameters": params}
    return defs

def cmd_macrodoc(folder):
    programs = load_estate(folder)
    defs = macro_defs(programs)
    out = []
    for name, d in sorted(defs.items()):
        sites = []
        for p in programs:
            for ln in p["macro_calls"].get(name, []):
                sites.append(f"{p['file']}:{ln}")
        out.append({"macro": name, "defined_in": d["defined_in"],
                    "parameters": d["parameters"], "call_sites": sites})
    emit({"ok": True, "folder": folder, "macros": out, "count": len(out)})

def cmd_impact(folder, name):
    programs = load_estate(folder)
    key = name.strip().lower().lstrip("%")
    hits = []
    is_ds = "." in key or any(key == d or key == norm_ds(d) for p in programs
                              for d in p["reads"] + p["creates"])
    for p in programs:
        roles = []
        if is_ds:
            target = norm_ds(key)
            if target in p["creates"]: roles.append("creates")
            if target in p["reads"]: roles.append("reads")
        if key in p["macro_calls"]: roles.append("calls_macro")
        if key in p["macros_defined"]: roles.append("defines_macro")
        if roles: hits.append({"file": p["file"], "roles": roles})
    emit({"ok": True, "folder": folder, "target": key,
          "kind": "dataset" if is_ds else "macro", "programs": hits})

def cmd_estate(folder):
    programs = load_estate(folder)
    lin = lineage(programs)
    flags = []
    # Heuristic 1: dataset libref used with no LIBNAME in the same program
    # (WORK is implicit in SAS and never needs one).
    for p in programs:
        for d in sorted(set(p["reads"]) | set(p["creates"])):
            ref = d.split(".")[0]
            if ref != "work" and ref not in p["libnames"]:
                flags.append({"type": "missing_libname", "program": p["file"],
                              "detail": f"dataset {d} uses libref '{ref}' with no LIBNAME for it in this program",
                              "basis": "heuristic"})
    # Heuristic 2: no %PUT / error-check patterns anywhere in the program.
    for p in programs:
        if not re.search(r"%put|syserr|sqlobs|errorcheck", p["code"], re.I):
            flags.append({"type": "no_error_check_pattern", "program": p["file"],
                          "detail": "no %PUT, &SYSERR or similar error-check pattern found",
                          "basis": "heuristic"})
    # Heuristic 3: orphan programs — no lineage or macro connection to
    # any other program in the estate.
    for p in programs:
        connected = False
        for d, e in lin.items():
            if p["file"] in e["created_by"] and any(f != p["file"] for f in e["read_by"]):
                connected = True
            if p["file"] in e["read_by"] and any(f != p["file"] for f in e["created_by"]):
                connected = True
        if any(name in macro_defs(programs) for name in p["macro_calls"]):
            connected = True
        if p["macros_defined"] and any(p["file"] != q["file"] and
                                       set(p["macros_defined"]) & set(q["macro_calls"])
                                       for q in programs):
            connected = True
        if not connected:
            flags.append({"type": "orphan_program", "program": p["file"],
                          "detail": "no shared datasets or macros connect this program to the rest of the estate",
                          "basis": "heuristic"})
    emit({"ok": True, "folder": folder,
          "summary": {"programs": len(programs),
                      "total_lines": sum(p["raw"].count("\n") + 1 for p in programs),
                      "datasets_tracked": len(lin),
                      "macros_defined": sum(len(p["macros_defined"]) for p in programs)},
          "inventory": [{"file": p["file"], "purpose": purpose_of(p["raw"]),
                         "macros_defined": p["macros_defined"]} for p in programs],
          "lineage": lin,
          "risk_flags": flags,
          "note": "Risk flags are text-parsing heuristics, not findings of fact — verify each one in the source."})

# ---------------------------------------------------------------- main

def main(argv):
    demo = "--demo" in argv; argv = [a for a in argv if a != "--demo"]
    if not demo: license_check.enforce()
    if len(argv) < 2:
        err("usage: statsignal.py [--demo] inventory|datamap|macrodoc|estate [folder] | logscan [logfile] | impact <name> [folder]")
    cmd = argv[1]
    rest = argv[2:]
    folder = SAMPLES if demo else (rest[-1] if rest and cmd not in ("logscan", "impact") else ".")
    if cmd == "inventory": cmd_inventory(folder)
    elif cmd == "datamap": cmd_datamap(folder)
    elif cmd == "macrodoc": cmd_macrodoc(folder)
    elif cmd == "estate": cmd_estate(folder)
    elif cmd == "logscan":
        logfile = rest[0] if rest else (os.path.join(SAMPLES, "analysis.log") if demo else err("logscan needs a log file"))
        cmd_logscan(logfile)
    elif cmd == "impact":
        if not rest: err("impact needs a dataset or macro name")
        f = SAMPLES if demo else (rest[1] if len(rest) > 1 else ".")
        cmd_impact(f, rest[0])
    else: err(f"unknown command: {cmd}")

if __name__ == "__main__":
    main(sys.argv)
