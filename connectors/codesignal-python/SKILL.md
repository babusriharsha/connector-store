# CodeSignal for Python Workflows

Scheduled workflows for codebases handled through CodeSignal for Python (`custom.codesignal-python`). Each workflow is a set of `codesignal.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads and reports first.** These workflows never edit, delete, move, rename or overwrite the owner's source files. Generated documentation goes only to a separate output folder the owner names. Anything a report proposes (for example, removing flagged dead code) happens only after the owner approves that exact change in this conversation.
- **Tests are never executed.** Workflows use the `tests` command for discovery only. Running a project's tests executes arbitrary code, so it stays approval-gated and off by default.
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run it once; if it still fails, report the failure plainly instead of guessing.
- **Dead code is a heuristic.** Always carry the caveat into the report: dynamic dispatch, reflection and entry points can hide real usage.

## Repo Health Sweep

**When:** weekly, same weekday (default Monday morning), plus whenever the owner asks.
**Purpose:** the headline use case — a short, plain-English read on whether the codebase is getting healthier or messier, week over week.

1. Run against the project root the owner names: `codesignal.py complexity`, `codesignal.py deadcode`, `codesignal.py document` (no `--out` — report only), and `codesignal.py todos`. Keep a small local note of last week's numbers so trends can be reported.
2. Report only the movement, in plain English:
   - **Complexity growth:** the top functions by complexity, calling out any function that newly entered the top list or grew since last week ("top movers").
   - **New dead code:** definitions or imports flagged this week that were not flagged last week — with the heuristic caveat attached, as review candidates, never as deletions.
   - **Docstring coverage drift:** this week's coverage % against last week's, up or down.
   - **TODO trend:** the TODO/FIXME/HACK/XXX count against last week, listing any newly added markers with file:line.
3. Never modify source. The report proposes; the owner disposes.

## Documentation Pack

**When:** whenever the owner asks, or on the schedule they set.
**Purpose:** a fresh, generated documentation file for the project, kept separate from the source.

1. Ask the owner for (or reuse) the output folder they want the docs in — a folder separate from the source tree.
2. Run `codesignal.py document <project-root> --out <that folder>`. It writes one `DOCUMENTATION.md` there and nothing anywhere else.
3. Report the docstring coverage % and the modules with the most undocumented functions, so the owner can see where a little documenting effort pays off most.

## Available connectors

- CodeSignal for Python — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.codesignal-python/CONNECTOR.md`.
