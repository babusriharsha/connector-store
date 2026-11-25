#!/usr/bin/env python3
"""CodeSignal for Python CLI — local Python codebase analysis, stdlib only.

Commands: repomap, document, deps, deadcode, complexity, todos,
syntax, tests. Analysis uses the ``ast`` module on source text.
Source files are NEVER modified: the only write is ``document --out
<dir>``, which writes one generated Markdown file into the directory
the caller names. Tests are DISCOVERED, never executed (see the
``tests`` command) — running tests executes arbitrary code, so it is
approval-gated and off by default.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check

BIN = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BIN, "samples")
COMPLEXITY_FORMULA = (
    "cyclomatic approximation = 1 + count of If / For / AsyncFor / While / "
    "ExceptHandler / BoolOp / IfExp nodes + comprehension if-clauses (via AST)"
)
HEURISTIC_CAVEAT = (
    "AST heuristics only: dynamic dispatch, reflection, string-based lookups, "
    "entry points and framework callbacks can hide real usage, so a flagged "
    "name may still be used at runtime. Verify before deleting anything."
)

STDLIB = getattr(sys, "stdlib_module_names", set())


def emit(payload, code=0):
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(code)


def err(msg):
    emit({"ok": False, "error": msg}, 1)


def find_py_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ("__pycache__", ".git", ".venv", "venv"))
        for name in sorted(filenames):
            if name.endswith(".py"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def module_name(root, path):
    rel = os.path.relpath(path, root)
    parts = rel[:-3].split(os.sep)  # strip .py
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else "__init__"


def read_source(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def parse_file(path):
    source = read_source(path)
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return source, None, exc
    return source, tree, None


def signature(node):
    try:
        args = ast.unparse(node.args)
    except Exception:
        args = "..."
    returns = ""
    if node.returns is not None:
        try:
            returns = " -> " + ast.unparse(node.returns)
        except Exception:
            returns = ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args}){returns}"


def iter_functions(tree):
    """Yield (qualified_name, node) for every function/method."""
    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield prefix + child.name, child
                yield from walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, prefix + child.name + ".")
            else:
                yield from walk(child, prefix)
    yield from walk(tree, "")


def collect(root):
    files = find_py_files(root)
    modules = []
    for path in files:
        source, tree, exc = parse_file(path)
        rel = os.path.relpath(path, root)
        modules.append({
            "path": path, "rel": rel, "name": module_name(root, path),
            "source": source, "tree": tree, "syntax_error": exc,
            "lines": len(source.splitlines()),
        })
    return modules


def resolve_root(argv, demo):
    if demo:
        return SAMPLES
    positional = [a for a in argv if not a.startswith("--")]
    if positional:
        root = os.path.abspath(positional[0])
        if not os.path.isdir(root):
            err(f"project root not found: {root}")
        return root
    err("a project root path is required in live mode (or use --demo)")


# ---------------------------------------------------------------- commands

def cmd_repomap(root):
    modules = []
    for m in collect(root):
        classes, functions = [], []
        if m["tree"] is not None:
            for node in m["tree"].body:
                if isinstance(node, ast.ClassDef):
                    methods = [c.name for c in node.body
                               if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    classes.append({"name": node.name, "methods": methods,
                                    "line": node.lineno})
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({"name": node.name, "line": node.lineno})
        modules.append({"module": m["name"], "file": m["rel"], "lines": m["lines"],
                        "classes": classes, "functions": functions})
    emit({"ok": True, "root": root, "modules": modules,
          "totals": {"files": len(modules),
                     "lines": sum(m["lines"] for m in modules)}})


def gather_docs(root):
    per_module = []
    total_entities = 0
    covered_entities = 0
    for m in collect(root):
        entries = []
        mod_doc = None
        if m["tree"] is not None:
            mod_doc = ast.get_docstring(m["tree"])
        entities = [{"kind": "module", "name": m["name"], "docstring": mod_doc}]
        if m["tree"] is not None:
            def walk(node, prefix):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.ClassDef):
                        entities.append({"kind": "class", "name": prefix + child.name,
                                         "docstring": ast.get_docstring(child)})
                        walk(child, prefix + child.name + ".")
                    elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        entities.append({"kind": "function", "name": prefix + child.name,
                                         "signature": signature(child),
                                         "docstring": ast.get_docstring(child)})
                        walk(child, prefix + child.name + ".")
                    else:
                        walk(child, prefix)
            walk(m["tree"], "")
        for e in entities:
            e["documented"] = bool(e.get("docstring"))
            total_entities += 1
            covered_entities += 1 if e["documented"] else 0
            entries.append(e)
        per_module.append({"module": m["name"], "file": m["rel"],
                           "module_docstring": mod_doc, "entries": entries})
    coverage = round(100.0 * covered_entities / total_entities, 2) if total_entities else 100.0
    return per_module, {"entities": total_entities, "documented": covered_entities,
                        "coverage_percent": coverage}


def cmd_document(root, out_dir):
    per_module, stats = gather_docs(root)
    result = {"ok": True, "root": root, "modules": per_module,
              "docstring_coverage": stats}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        lines = ["# Project Documentation", "",
                 f"Docstring coverage: {stats['coverage_percent']}% "
                 f"({stats['documented']}/{stats['entities']} entities)", ""]
        for mod in per_module:
            lines.append(f"## {mod['module']} (`{mod['file']}`)")
            lines.append("")
            if mod["module_docstring"]:
                lines.append(mod["module_docstring"])
                lines.append("")
            for e in mod["entries"]:
                if e["kind"] == "module":
                    continue
                title = e.get("signature") or e["name"]
                lines.append(f"### {e['kind']}: `{title}`")
                lines.append("")
                lines.append(e["docstring"] or "_No docstring._")
                lines.append("")
        out_path = os.path.join(out_dir, "DOCUMENTATION.md")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        result["written_to"] = out_path
        result["note"] = "Generated docs were written only into the --out directory named; no source file was modified."
    emit(result)


def parse_requirements(root):
    listed = []
    req = os.path.join(root, "requirements.txt")
    if os.path.isfile(req):
        for raw in read_source(req).splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~;\[]", line)[0].strip().lower().replace("_", "-")
            if name:
                listed.append(name)
    pyproject = os.path.join(root, "pyproject.toml")
    if os.path.isfile(pyproject):
        text = read_source(pyproject)
        for m in re.finditer(r'"([A-Za-z0-9_.\-]+)\s*(?:[<>=!~;]|")', text):
            name = m.group(1).lower().replace("_", "-")
            if name not in listed:
                listed.append(name)
    return listed


def cmd_deps(root):
    modules = collect(root)
    local_roots = {m["name"].split(".")[0] for m in modules}
    graph = {}
    third_party = set()
    all_imports = {}
    for m in modules:
        imports = []
        if m["tree"] is not None:
            for node in ast.walk(m["tree"]):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        base = m["name"].rsplit(".", node.level - 1)[0] if node.level > 1 else m["name"].split(".")[0]
                        full = (base + "." + node.module) if node.module else base
                        imports.append(full)
                    elif node.module:
                        imports.append(node.module)
        imports = sorted(set(imports))
        graph[m["name"]] = imports
        all_imports[m["name"]] = imports
        for imp in imports:
            top = imp.split(".")[0]
            if top not in STDLIB and top not in local_roots:
                third_party.add(top)
    listed = parse_requirements(root)
    listed_norm = {n.replace("-", "_") for n in listed}
    tp_norm = {n.replace("-", "_") for n in third_party}
    result = {"ok": True, "root": root, "import_graph": graph,
              "third_party_dependencies": sorted(third_party),
              "requirements_listed": listed,
              "listed_but_unused": sorted(n for n in listed if n.replace("-", "_") not in tp_norm),
              "used_but_unlisted": sorted(n for n in third_party if n.replace("-", "_") not in listed_norm)}
    if not listed:
        result["cross_check_note"] = "No requirements.txt or pyproject.toml found, so used_but_unlisted lists every third-party import."
    emit(result)


def cmd_deadcode(root):
    modules = collect(root)
    # Every name referenced anywhere (Name ids and Attribute attrs).
    referenced = {}
    for m in modules:
        if m["tree"] is None:
            continue
        for node in ast.walk(m["tree"]):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            if name:
                referenced.setdefault(name, set()).add(m["rel"])
    dead = []
    unused_imports = []
    for m in modules:
        if m["tree"] is None:
            continue
        is_test_file = os.path.basename(m["rel"]).startswith("test_")
        for node in m["tree"].body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("__"):
                    continue
                if is_test_file and node.name.startswith("test_"):
                    # Test functions are entry points discovered by the
                    # test runner, not dead code.
                    continue
                refs = referenced.get(node.name, set())
                # A reference in its own module via attribute/self-call still counts
                # only if the name actually appears used; definitions alone do not
                # add to `referenced` (they are not Name/Attribute nodes).
                if node.name not in referenced:
                    dead.append({"name": node.name, "file": m["rel"], "line": node.lineno,
                                 "kind": "class" if isinstance(node, ast.ClassDef) else "function"})
                _ = refs
        # Unused imports in this file.
        used_names = set()
        if m["tree"] is not None:
            for node in ast.walk(m["tree"]):
                if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                    for elt in ast.walk(node.value):
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            used_names.add(elt.value)
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    cur = node
                    while isinstance(cur, ast.Attribute):
                        cur = cur.value
                    if isinstance(cur, ast.Name):
                        used_names.add(cur.id)
            for node in ast.walk(m["tree"]):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        bound = alias.asname or alias.name.split(".")[0]
                        if bound not in used_names:
                            unused_imports.append({"name": bound, "imported": alias.name,
                                                   "file": m["rel"], "line": node.lineno})
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        bound = alias.asname or alias.name
                        if bound not in used_names:
                            unused_imports.append({"name": bound, "imported": alias.name,
                                                   "file": m["rel"], "line": node.lineno})
    emit({"ok": True, "root": root, "dead_definitions": dead,
          "unused_imports": unused_imports, "heuristic": HEURISTIC_CAVEAT,
          "caveat": HEURISTIC_CAVEAT})


def complexity_of(node):
    score = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.BoolOp, ast.IfExp)):
            score += 1
        elif isinstance(child, ast.comprehension):
            score += len(child.ifs)
    return score


def cmd_complexity(root):
    rows = []
    for m in collect(root):
        if m["tree"] is None:
            continue
        for qual, node in iter_functions(m["tree"]):
            lines = (node.end_lineno or node.lineno) - node.lineno + 1
            rows.append({"function": qual, "module": m["name"], "file": m["rel"],
                         "line": node.lineno, "lines": lines,
                         "complexity": complexity_of(node)})
    rows.sort(key=lambda r: (-r["complexity"], -r["lines"], r["function"]))
    emit({"ok": True, "root": root, "formula": COMPLEXITY_FORMULA, "functions": rows})


def cmd_todos(root):
    markers = ("TODO", "FIXME", "HACK", "XXX")
    found = []
    for m in collect(root):
        for i, line in enumerate(m["source"].splitlines(), start=1):
            for marker in markers:
                if re.search(rf"\b{marker}\b", line):
                    found.append({"marker": marker, "file": m["rel"], "line": i,
                                  "location": f"{m['rel']}:{i}", "text": line.strip()})
                    break
    emit({"ok": True, "root": root, "count": len(found), "todos": found})


def cmd_syntax(root):
    results = []
    for m in collect(root):
        error = None
        try:
            compile(m["source"], m["rel"], "exec")
        except SyntaxError as exc:
            error = {"message": exc.msg, "line": exc.lineno, "offset": exc.offset}
        results.append({"file": m["rel"], "ok": error is None, "error": error})
    emit({"ok": True, "root": root,
          "note": "Checked with the compile() builtin on source text; nothing was executed and no .pyc files were written.",
          "all_ok": all(r["ok"] for r in results), "files": results})


def cmd_tests(root):
    modules = collect(root)
    test_files = []
    source_stems = {}
    for m in modules:
        stem = os.path.splitext(os.path.basename(m["rel"]))[0]
        is_test = stem.startswith("test_") or stem.endswith("_test")
        if is_test:
            funcs = []
            if m["tree"] is not None:
                for qual, node in iter_functions(m["tree"]):
                    if node.name.startswith("test_"):
                        funcs.append({"name": qual, "line": node.lineno})
            test_files.append({"file": m["rel"], "module": m["name"], "test_functions": funcs})
        else:
            source_stems[stem] = m
    coverage_map = {}
    test_stems = {os.path.splitext(os.path.basename(t["file"]))[0][5:] for t in test_files}
    for stem, m in sorted(source_stems.items()):
        coverage_map[m["name"]] = {
            "file": m["rel"],
            "test_file": f"test_{stem}.py" if stem in test_stems else None,
            "has_same_stem_test_file": stem in test_stems,
        }
    emit({"ok": True, "root": root, "discovery_only": True, "executed": False,
          "note": ("DISCOVERY ONLY — tests were not executed. Running tests executes "
                   "arbitrary code from the project, so test execution is approval-gated "
                   "and off by default in this connector."),
          "test_files": test_files, "source_test_coverage": coverage_map})


def main(argv):
    demo = "--demo" in argv
    argv = [a for a in argv if a != "--demo"]
    if len(argv) < 2:
        err("usage: codesignal.py [--demo] repomap|document|deps|deadcode|complexity|todos|syntax|tests [project-root] [--out <dir>]")
    cmd = argv[1]
    rest = argv[2:]
    out_dir = None
    cleaned = []
    i = 0
    while i < len(rest):
        if rest[i] == "--out" and i + 1 < len(rest):
            out_dir = rest[i + 1]
            i += 2
        else:
            cleaned.append(rest[i])
            i += 1
    if out_dir and cmd != "document":
        err("--out is only supported for the document command")
    root = resolve_root(cleaned, demo)
    if not demo:
        license_check.enforce()
    if cmd == "repomap":
        cmd_repomap(root)
    elif cmd == "document":
        cmd_document(root, out_dir)
    elif cmd == "deps":
        cmd_deps(root)
    elif cmd == "deadcode":
        cmd_deadcode(root)
    elif cmd == "complexity":
        cmd_complexity(root)
    elif cmd == "todos":
        cmd_todos(root)
    elif cmd == "syntax":
        cmd_syntax(root)
    elif cmd == "tests":
        cmd_tests(root)
    else:
        err(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv)
