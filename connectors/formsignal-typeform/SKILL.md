# Typeform Response Workflows

Scheduled workflows for an account connected through FormSignal for Typeform (`custom.typeform`). Each workflow is a set of `typeform.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only, unless the owner has pre-approved a specific write in this conversation.** These workflows never run a write command with `--yes` on their own. When a workflow spots something worth changing, it reports it and offers the change; the write happens only after the owner approves that exact change (see CONNECTOR.md, write rules).
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one). Owners uninstall noisy tools.
- **Verify before alarming.** If a command fails or returns something implausible, re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.

## New Responses Digest

**When:** daily, at a time the owner picks (default 9:00 AM local), or weekly for quiet forms.
**Purpose:** a short, plain-English summary the owner can read in 30 seconds.

1. Run `typeform.py forms` and note each form's response count; compare with the count from the last digest (keep a small local note).
2. For each form whose count grew, run `typeform.py responses --form <id> --limit 10` and summarise only the NEW responses: count, completion rate, and one-line excerpts of the latest answers.
3. Shape:

   > **New responses**
   > [Form]: N new (total M, completion X%). Latest: "[excerpt]".
   > No new responses. *(send nothing instead, unless the owner asked for an all-clear)*

## Available connectors

- Typeform — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.typeform/CONNECTOR.md`.
