# StatSignal for SAS Workflows

Scheduled workflows for SAS estates handled through StatSignal for SAS (`custom.statsignal-sas`). Each workflow is a set of `statsignal.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads and reports only — always.** This connector never modifies source files, and no workflow may either. Anything a sweep proposes happens only after the owner approves that exact change in this conversation, and the owner makes it in their own tools.
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run it once; if it still fails, report the failure plainly instead of guessing. Risk flags are heuristics — present them as things to check, never as findings of fact.

## SAS Estate Sweep

**When:** weekly, same weekday (default Monday morning), plus whenever the owner asks.
**Purpose:** the headline use case — the estate watched continuously, so new programs, broken runs and drifting lineage surface in plain English instead of being discovered months later.

1. Run `statsignal.py inventory <estate folder>` and compare with last week's saved summary: report **new programs** (and any that disappeared) by name, with the purpose line from each new program's header comment.
2. Run `statsignal.py logscan` on each `.log` file in the estate folder (new or changed since the last sweep): report an **error digest** — per log, the verdict and each error's text, worst first. Logs with only warnings get one line; clean logs are counted, not listed.
3. Run `statsignal.py datamap <estate folder>` and compare lineage with the last sweep: report **lineage changes** — datasets with a new creator or a new reader, and datasets read by programs but created by none.
4. Run `statsignal.py estate <estate folder>`: report new **orphan flags** and any other new risk flags, each labelled as a heuristic to check.
5. Keep a small local note of the last sweep's summaries (counts, lineage edges, log verdicts) so each report is a diff, not a dump. Never edit a source file to "fix" anything the sweep finds.

## Lineage Pack

**When:** on demand — before a change, a migration, a validation review or a handover.
**Purpose:** a complete, plain-English picture of how the estate hangs together, assembled in one pass.

1. Run `statsignal.py datamap <estate folder>` for the full dataset map: every dataset with its creating program and its reading programs.
2. For each dataset the owner names (or, if none, the five most-read datasets), run `statsignal.py impact <dataset>` and spell out the blast radius in plain English: "changing X affects these programs."
3. Run `statsignal.py macrodoc <estate folder>` and append the macro catalogue: each macro, where it is defined, its parameters and defaults, and where it is called from.
4. Close with the honest caveat from CONNECTOR.md: this is static text parsing — dynamic code (CALL EXECUTE, macro-generated code) can hide lineage, so the pack is a map to verify, not proof.

## Available connectors

- StatSignal for SAS — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.statsignal-sas/CONNECTOR.md`.
