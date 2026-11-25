# Mailchimp Briefs and Alerts

Workflows for the Mailchimp connector (`custom.mailchimp`, see CONNECTOR.md in
this package). Each workflow is written so another Muse can run it on a
schedule (a cron job in the user's own Muse) or on demand. All data comes
from the connector helper:

```text
python3 bin/mailchimp.py <command>
```

Paths below assume the package is installed at
`~/workspace/custom-connectors/custom.mailchimp/`. Run from that folder, or
use the full path to `bin/mailchimp.py`.

Rules that apply to every workflow:

- Prove the connection once per run with `status`. If it fails, stop and tell
  the user what the error says. Do not guess at numbers.
- Present rates as percentages with one decimal (an `open_rate` of 0.412 is
  41.2%). Always name the audience and the campaign subject line, never just
  an id.
- Revenue fields are `null` for accounts with no connected e-commerce store.
  Say "no store connected, so no revenue data" instead of reporting $0.
- Never send a campaign, and never add a member, inside these workflows.
  Drafts and tags still need the user's approval, exactly as CONNECTOR.md
  describes.

## Weekly Audience Brief

Schedule: once a week, the same weekday and time (Monday morning works well).
Also run it whenever the user asks "how is my list doing?" or similar.

Steps:

1. Run `status`. Note the account name and total subscribers.
2. Run `growth --months 3` for the per-audience picture over the last three
   complete calendar months (Mailchimp growth is monthly; say that in the
   brief so the user is not expecting daily numbers).
3. Run `top-campaigns --by open --days 7` and, if it returns nothing (no send
   this week), run it again with `--days 30` and label the wider window.
   Also run `top-campaigns --by click --days 30` for the click view.
4. Write the brief in this shape, short enough to read in a minute:
   - One headline line: total subscribers now, and net change over the
     period, per audience when there is more than one.
   - Growth: opt-ins, imports, unsubscribes and cleaned addresses per
     audience, with the net. Flag any audience whose net went negative.
   - Best campaign of the period: subject line, audience, open rate, click
     rate, emails sent, and revenue when present.
   - One plain-language observation (for example: "Customers open at 41%
     while the newsletter list opens at 28%, so announcements earn more
     attention on the customer list"). Only say what the numbers support.
5. Do not attach raw JSON. The numbers in sentences are the brief.

## Campaign Performance Alert

Purpose: catch a weak send early, while the user can still react (a follow-up
email, a corrected link, a subject-line lesson for next time).

Setup: when the user says a campaign went out, note its campaign id and the
send time. Schedule a one-time check 24 hours after the send. Reports are
still settling before 24 hours, so do not pull them earlier and call them
final.

Steps at the 24-hour mark:

1. Run `status`, then `report <campaign_id>`.
2. Run `top-campaigns --by open --days 90` and `--by click --days 90` to get
   the account's recent field. Compute the average open rate and click rate
   across the returned sent campaigns (excluding the campaign being checked
   if it appears).
3. Compare and report:
   - Always send the user the result: subject line, emails sent, open rate,
     click rate, bounces (hard and soft), unsubscribes and unsub rate, and
     orders and revenue when present.
   - Flag it as an alert when the open rate or click rate is more than 20%
     below the 90-day average, when hard bounces exceed 2% of emails sent,
     or when the unsub rate exceeds 0.5%. Name which threshold tripped and
     by how much.
   - When it beats the averages, say that too, with the same numbers.
4. Suggest at most one next step, tied to the numbers (for example, a high
   open rate with a low click rate points at the email body or the link
   placement, not the subject line). Do not invent causes the data cannot
   show.

## List Health Check

Schedule: once a month. Also run it when the user worries about deliverability
or a sudden drop in opens.

Steps:

1. Run `status` and `audiences`. Note each audience's `cleaned_count`,
   `unsubscribe_count`, lifetime open and click rates.
2. Run `growth --months 6`. For each audience, look at the trend, not one
   month: unsubscribes and cleaned addresses per month against opt-ins.
3. Run `campaigns --status sent --days 90`, then `report <campaign_id>` for
   the three most recent sends. Collect hard bounces, soft bounces and
   unsubscribes per send.
4. Report, per audience:
   - Growth trend: growing, flat or shrinking, with the six-month net.
   - Loss rate: (unsubscribes + cleaned) as a share of opt-ins over six
     months. Flag it when losses exceed half of gains for two months in a
     row, or when any month shows negative net.
   - Bounce trend: flag hard bounces rising across the last three sends, or
     any single send above 2% hard bounces. Rising hard bounces usually mean
     old or purchased addresses are in the list; say that as a possibility
     to check, not a verdict.
   - Unsub trend: flag an unsub rate above 0.5% on recent sends.
5. Close with the single most useful action the numbers support (for example:
   re-confirm or sunset contacts who have not opened in 12 months, using
   Mailchimp's own tools). The connector does not delete or archive members;
   the owner does list cleaning in Mailchimp.

## Available connectors

- [Mailchimp](CONNECTOR.md) in this package (`custom.mailchimp`): audiences,
  growth, campaigns, reports, members, draft creation, tags, opted-in adds.
