# Etsy Shop Workflows

Workflows for a Muse connected to a seller's Etsy shop through the `custom.etsy` connector in this package. Each workflow names the connector commands to run, what to report, and when to stay silent. Schedule them with cron only when the shop owner asks. Commands below assume the connector folder is installed at `~/workspace/custom-connectors/custom.etsy/`; adjust the path to where the package actually lives.

## Guardrails for every workflow

- Run `python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py status` first. If it reports a license refusal (exit code 3), relay the subscribe message once and stop. If it reports `credentials_unavailable`, tell the owner the shop needs reconnecting and stop.
- Never run a write (`set-price`, `set-quantity`) inside a scheduled workflow. These workflows only read. Any change needs the owner's approval in conversation, following the approval flow in CONNECTOR.md.
- Report numbers exactly as the JSON gives them. Name the snapshot method when quoting sales totals: client-side sums of paid receipt grandtotals, fees and refunds not netted out.
- Stay silent when a workflow says so. A seller who gets noise every morning stops reading the brief.

## Morning Shop Brief

- Schedule: once each morning, at a time the owner picks (their timezone).
- Run:
  - `etsy.py snapshot`
  - `etsy.py orders --status unshipped --days 7 --limit 25`
  - `etsy.py inventory --threshold 3`
  - `etsy.py reviews --limit 3`
- Report, in this order, in a few short lines:
  1. Yesterday's orders, items and gross sales, with today's so far beside it.
  2. Unshipped paid orders: count, oldest first, naming the buyer and what they bought. These are the day's packing list.
  3. Offerings at quantity 3 or below: listing title, variant, quantity left. One line each.
  4. Any review since the last brief: stars and one short quote. Flag anything under 4 stars at the top instead.
- Skip a section silently when it is empty. Never pad the brief.

## Low-Quantity Sweep

- Schedule: once a day, or every other day for quiet shops. The owner sets the threshold; default 3.
- Run: `etsy.py inventory --threshold <n>`.
- Keep a small local record of what was already reported (listing id, offering id, quantity, date) in the workflow's own notes.
- Report only what is new or worse: an offering that crossed the threshold since the last sweep, or one whose quantity dropped further. Repeat warnings about the same unchanged offering at most once a week.
- If nothing is new, send nothing.

## New-Review Alert

- Schedule: every few hours during the owner's working day, or once daily for a gentler pace.
- Run: `etsy.py reviews --limit 10`.
- Compare against the newest review seen last time (remember its transaction id and timestamp in the workflow's notes).
- For each new review, report the stars, the listing, and the review text. Draft a short, warm reply the owner can post, in the owner's voice, and wait for their approval before anything is posted anywhere. This connector cannot post replies; hand the draft to the owner.
- A new review under 4 stars gets flagged first, with a calmer, non-defensive draft reply that thanks the buyer and offers to make it right.
- If there are no new reviews, send nothing.

## Weekly Sales Read

- Schedule: once a week, on a morning the owner picks.
- Run:
  - `etsy.py snapshot`
  - `etsy.py orders --status all --days 7 --limit 100`
  - `etsy.py ledger --days 7 --limit 50`
  - `etsy.py listings --limit 25`
- Report:
  1. The week's orders, items and gross sales from the snapshot's `last_7_days` bucket, labelled with its method.
  2. Best sellers of the week: aggregate the orders' transactions by listing, ranked by quantity sold, top 5.
  3. Money in and out from the ledger: total sale credits, total fees, any deposits, and the latest balance.
  4. Listings that got no orders this week, from the active list minus the sellers in step 2. Name them plainly as candidates for fresh photos, titles or a price look — suggestions only, never changes.
- End with one sentence: the single most useful thing the numbers say this week.
