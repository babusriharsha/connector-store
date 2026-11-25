# Sage Business Cloud Accounting Workflows

Scheduled workflows for an account connected through LedgerSignal for Sage (`custom.ledgersignal-sage`). Each workflow is a set of `sage.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only, unless the owner has pre-approved a specific write in this conversation.** These workflows never run a write command with `--yes` on their own. When a workflow spots something worth changing (a draft invoice worth creating), it reports it and offers the change; the write happens only after the owner approves that exact change (see CONNECTOR.md, write rules).
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one). Business owners uninstall noisy tools.
- **Verify before alarming.** If a command fails or returns something implausible (no invoices at all for a busy business), re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.
- **Money figures** come from Sage Business Cloud Accounting's own records. Round to whole dollars in prose unless the owner wants cents.

## Weekly Cash Brief

**When:** weekly, before the owner's working week (ask their timezone and preferred time; default Monday 7:30 AM owner-local).
**Purpose:** who owes money, what came in, and where the account stands — in 30 seconds.

1. Run `sage.py overdue` and take the overdue list and its total outstanding. Name the oldest and the largest by customer.
2. Run the connector's recent-money read (invoices / payments / bank summary, whichever this connector offers — see CONNECTOR.md commands) and summarise what was paid in the last 7 days.
3. Run the balance read this connector offers (bank accounts / bank summary / accounts) and state the current balances briefly.
4. Write the brief in this shape, short enough to read in 30 seconds:

   > **Cash brief — this week**
   > Overdue: $X across N invoices (oldest: [Customer], [date]; largest: [Customer], $Y).
   > Paid in the last 7 days: $Z.
   > Balances: [Account] $A · [Account] $B.
   > Nothing else needs attention. *(only when true)*

## Available connectors

- Sage Business Cloud Accounting — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.ledgersignal-sage/CONNECTOR.md`.
