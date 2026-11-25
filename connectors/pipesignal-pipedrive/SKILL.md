# PipeSignal for Pipedrive Workflows

Scheduled workflows for an account connected through PipeSignal for Pipedrive (`custom.pipesignal-pipedrive`). Each workflow is a set of `pipedrive.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only.** This workflow never runs a write command, with or without `--yes`. When it spots something worth changing, it reports it and offers the change; the write happens only after the owner approves that exact change in conversation (see CONNECTOR.md, write rules).
- **Silence is a feature.** A run with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.
- **Only say what the data supports.** Never invent dates, owners, amounts or activity that the commands did not return; label approximations as approximations.

## Stalled Deals Sweep

**When:** ask the owner's timezone and preferred time; default weekday mornings (for a sweep/digest, the weekday the owner picks, default Monday).
**Purpose:** a short, plain-English read of the connected Pipedrive account from this connector's read commands only.

1. Run `pipedrive.py status` to prove the connection.
2. Run `pipedrive.py deals --status open` and `pipedrive.py activities --days 14`.
3. Call a deal 'stalled' only when returned data supports it: an open deal with no matching activity in the returned activities, or returned date fields older than 14 days. If deal records carry no usable date/activity evidence, say the sweep cannot judge staleness instead of guessing.
4. Report stalled deals by title, value (with currency when returned), status and person/org when returned, plus next scheduled activities. Suggest — do not create — a follow-up; `add-activity` runs only after the owner approves that exact activity.

Shape the report short enough to read in a minute, with a headline line first. Nothing is created, sent or changed by this workflow.

## Available connectors

- Pipedrive — `CONNECTOR.md` in this package; after install it lives at `~/workspace/custom-connectors/custom.pipesignal-pipedrive/CONNECTOR.md`.
