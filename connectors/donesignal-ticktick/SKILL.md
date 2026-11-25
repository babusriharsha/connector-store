# TickTick Task Workflows

Scheduled workflows for an account connected through DoneSignal for TickTick (`custom.ticktick`). Each workflow is a set of `ticktick.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only, unless the owner has pre-approved a specific write in this conversation.** These workflows never run a write command with `--yes` on their own. When a workflow spots something worth changing, it reports it and offers the change; the write happens only after the owner approves that exact change (see CONNECTOR.md, write rules).
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one). Owners uninstall noisy tools.
- **Verify before alarming.** If a command fails or returns something implausible, re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.

## Today & Overdue Brief

**When:** daily, at the start of the owner's day (ask timezone/time; default 7:00 AM local).
**Purpose:** a short, plain-English summary the owner can read in 30 seconds.

1. Run `ticktick.py projects`, then `ticktick.py tasks --project <id>` for each project.
2. Split tasks into due today, overdue (due date before today, still open), and high priority with no due date.
3. Write the brief in this shape:

   > **Today & overdue**
   > Today: [Task] ([Project], [time]).
   > Overdue: [Task] ([Project], due [date]).
   > Nothing due or overdue. *(only when true)*

## Available connectors

- TickTick — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.ticktick/CONNECTOR.md`.
