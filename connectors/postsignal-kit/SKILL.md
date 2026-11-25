# Kit Briefs

Workflows for PostSignal for Kit (`custom.postsignal-kit`, see CONNECTOR.md in this package). Written so another Muse can run it on a schedule (a cron job in the user's own Muse) or on demand. All data comes from the connector helper:

```text
python3 bin/kit.py <command>
```

Paths below assume the package is installed at `~/workspace/custom-connectors/custom.postsignal-kit/`.

Ground rules (same spirit as the WooCommerce briefs):

- Prove the connection once per run with `status`. If it fails, stop and tell the user what the error says. Do not guess at numbers.
- Present rates as percentages with one decimal (an open rate of 0.412 is 41.2%). Always name the list/group and the campaign subject line, never just an id.
- Reads only inside scheduled workflows: never add a subscriber/contact, never tag anyone, and never send anything from a brief.
- Do not attach raw JSON. The numbers in sentences are the brief.

## Audience Growth Brief

Schedule: once a week, the same weekday and time (Monday morning works well). Also run it whenever the user asks "how is my list doing?" or similar.

Steps:

1. Run `status`. Note the account name and the total subscriber/contact count.
2. Read the current audience picture (subscribers, tags, forms, sequences and broadcasts). Compare the totals with last week's brief when one exists and compute the subscriber delta (new total minus last week's total); say plainly when there is no previous brief to compare against.
3. Read the recent campaigns/broadcasts and pick the most recent sent one: report its subject line, emails sent, open rate, click rate, bounces and unsubscribes in plain numbers.
4. Write the brief in this shape, short enough to read in a minute:
   - One headline line: total subscribers now, and the net change since last week.
   - Growth: the per-list/group counts that moved, with the net. Flag any list whose count went down.
   - Best/recent campaign: subject line, audience, open rate, click rate, emails sent.
   - One plain-language observation the numbers support (for example: "Customers open at 41% while the main list opens at 28%, so announcements earn more attention on the customer list"). Only say what the numbers support.
5. Save the headline totals so next week's brief can compute the delta.

## Available connectors

- [Kit](CONNECTOR.md) in this package (`custom.postsignal-kit`): subscribers, tags, forms, sequences and broadcasts, plus the approval-gated write in CONNECTOR.md (never used by this brief).
