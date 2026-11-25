# DealSignal for HubSpot Workflows

Scheduled workflows for an account connected through DealSignal for HubSpot (`custom.dealsignal-hubspot`). Each workflow is a set of `hubspot.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only.** This workflow never runs a write command, with or without `--yes`. When it spots something worth changing, it reports it and offers the change; the write happens only after the owner approves that exact change in conversation (see CONNECTOR.md, write rules).
- **Silence is a feature.** A run with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.
- **Only say what the data supports.** Never invent dates, owners, amounts or activity that the commands did not return; label approximations as approximations.

## Pipeline Morning Brief

**When:** ask the owner's timezone and preferred time; default weekday mornings (for a sweep/digest, the weekday the owner picks, default Monday).
**Purpose:** a short, plain-English read of the connected HubSpot account from this connector's read commands only.

1. Run `hubspot.py status` to prove the connection.
2. Run `hubspot.py pipeline` and `hubspot.py deals`. Group deals by stage from the pipeline output; total the amount per stage, naming deals with no amount as 'no amount set' rather than $0 pipeline.
3. Run `hubspot.py contacts --limit 20` for the newest contacts.
4. Write the brief: one headline line (open deals, total pipeline value), deals per stage with amounts, the largest deal by name/amount/stage, and any observation the returned data actually supports. Do not invent close dates, owners or activity the commands did not return.

Shape the report short enough to read in a minute, with a headline line first. Nothing is created, sent or changed by this workflow.

## Available connectors

- HubSpot — `CONNECTOR.md` in this package; after install it lives at `~/workspace/custom-connectors/custom.dealsignal-hubspot/CONNECTOR.md`.
