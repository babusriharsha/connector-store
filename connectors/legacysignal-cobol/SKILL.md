# LegacySignal Workflows

Scheduled workflows for COBOL estates handled through LegacySignal for COBOL (`custom.legacysignal-cobol`). Each workflow is a set of `legacysignal.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads and reports first.** This workflow never deletes, moves, renames or modifies the owner's source code on its own. Anything it proposes happens only after the owner approves that exact change in this conversation. LegacySignal itself is read-only by design; reports go only to an output folder the owner names.
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run it once; if it still fails, report the failure plainly instead of guessing. A program that looks dead may run from a scheduler outside the folder — say so, never present a heuristic result as certain.

## Estate Health Sweep

**When:** weekly, same weekday (default Monday morning), plus whenever the owner asks.
**Purpose:** the headline use case — a standing, plain-English picture of the whole estate, so changes and risks surface early instead of at incident time.

1. Run `legacysignal.py inventory` on the estate folder the owner names. Keep a small local note of the previous inventory (file names, line counts, program-ids) to compare against.
2. Run `legacysignal.py deadcode` on the same folder.
3. Build the impact-hotspot summary: run `legacysignal.py callmap` and `legacysignal.py copybooks`, and rank the most-called programs and most-used copybooks — those are the estate's load-bearing pieces, where a change hurts most.
4. Flag, in plain English, only what matters:
   - **New programs or copybooks** that were not in the last inventory, and any with no header-comment purpose (undocumented).
   - **Changed programs** whose line count moved since the last sweep.
   - **New dead-code candidates** (verify-before-alarming applies: phrase them as candidates, with the outside-scheduler caveat).
   - **Hotspot changes** — a program or copybook that newly entered the most-called / most-used list.
5. Never modify, move or delete any source file. The report proposes; the owner disposes.

## Modernisation Brief Pack

**When:** whenever the owner asks, typically before a modernisation planning meeting.
**Purpose:** a shareable brief the owner can hand to a team or a vendor.

1. Run `legacysignal.py modernize <estate-folder> --out <output-folder the owner names>` — the `--out` folder is always the owner's explicit choice, never the source folder.
2. Run `legacysignal.py document <PROGRAM> <estate-folder> --out <same output folder>` for each of the top few highest-complexity programs from the brief.
3. Summarise in plain English: the complexity ranking and its formula, the riskiest programs and why (heavy SQL, CICS, no error handling found), and the suggested phasing from the brief — easiest self-contained programs first.
4. Remind the owner the scores are a heuristic planning aid from pattern parsing, not a compiler-grade measurement.

## Available connectors

- LegacySignal for COBOL — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.legacysignal-cobol/CONNECTOR.md`.
