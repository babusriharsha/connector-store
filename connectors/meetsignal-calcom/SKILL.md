# Cal.com Booking Workflows

Scheduled workflows for an account connected through MeetSignal for Cal.com (`custom.calcom`). Each workflow is a set of `calcom.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only, unless the owner has pre-approved a specific write in this conversation.** These workflows never run a write command with `--yes` on their own. When a workflow spots something worth changing, it reports it and offers the change; the write happens only after the owner approves that exact change (see CONNECTOR.md, write rules).
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one). Owners uninstall noisy tools.
- **Verify before alarming.** If a command fails or returns something implausible, re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.

## Today's Bookings Brief

**When:** daily, before the owner's working day (ask timezone/time; default 7:30 AM local).
**Purpose:** a short, plain-English summary the owner can read in 30 seconds.

1. Run `calcom.py bookings --status upcoming` and keep only bookings starting today in the owner's timezone.
2. Run `calcom.py event-types` once if a booking's event type title is missing, to name the meeting type.
3. Write the brief in this shape:

   > **Today's bookings**
   > [Time] — [Title] with [attendee name] ([event type]).
   > No bookings today. *(only when true)*

## Available connectors

- Cal.com — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.calcom/CONNECTOR.md`.
