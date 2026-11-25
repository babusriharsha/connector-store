# WooCommerce Store Workflows

Scheduled workflows for a store connected through ShopSignal for WooCommerce (`custom.woocommerce`). Each workflow is a set of `woo.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads only, unless the owner has pre-approved a specific write in this conversation.** These workflows never run a write command with `--yes` on their own. When a workflow spots something worth changing (a price, a stock count, a coupon), it reports it and offers the change; the write happens only after the owner approves that exact change (see CONNECTOR.md, write rules).
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one). Store owners uninstall noisy tools.
- **Verify before alarming.** If a command fails or returns something implausible (zero sales at midday for a busy store), re-run `status` once; if the connection is broken, report the connection problem instead of the misleading number.
- **Money figures** come from WooCommerce's own reporting, which counts gross sales including tax and shipping. Round to whole dollars in prose unless the owner wants cents.

## Morning Store Brief

**When:** daily, before the owner's working day (ask their timezone and preferred time; default 7:30 AM store-local).
**Purpose:** yesterday, closed and complete, plus what needs hands today.

1. Run `woo.py snapshot` and take the **yesterday** block: gross sales, orders, average order value. Compare against the **last_7_days** block divided by 7 to say whether yesterday was above or below a typical day.
2. Run `woo.py orders --status processing --limit 50` and count unfulfilled orders; list any older than 48 hours by order number.
3. Run `woo.py orders --status on-hold --limit 20`; on-hold orders usually mean a payment or stock problem — always surface them.
4. Run `woo.py inventory` and take the top 5 lowest items, naming anything at zero.
5. Write the brief in this shape, short enough to read in 30 seconds:

   > **Store brief — yesterday**
   > Sales: $X from N orders (avg $Y) — a [strong/typical/slow] day vs your last 7.
   > Needs you: N orders waiting to ship ([oldest: #1234, 3 days]).
   > Stock: [Product] is out; [Product] has 3 left.
   > Nothing else needs attention. *(only when true)*

## Low-Stock Sweep

**When:** every day or every other day, an hour after the Morning Brief or standalone.
**Purpose:** catch stock-outs before customers do.

1. Run `woo.py inventory` (uses each product's own WooCommerce low-stock amount, fallback threshold 5).
2. Report **only changes since the last sweep**: newly low items, items that hit zero, items that got worse. Keep a small local note of the last sweep's list to diff against.
3. Shape: one line per item — name, quantity left, threshold. If nothing changed, send nothing.

## Refund Spike Alert

**When:** daily, with or right after the Morning Brief.
**Purpose:** refunds are the earliest smell of a product, shipping or listing problem.

1. Run `woo.py refunds --days 1` and `woo.py refunds --days 7`.
2. Baseline: the 7-day refund total divided by 7. Alert when **today's refund total is more than 3× the daily baseline AND at least 2 refunds**, or whenever a single refund exceeds an amount the owner sets (ask once; default $100).
3. When alerting, group the day's refunds by reason from the output and name the orders involved. A cluster with the same reason (e.g. "arrived cracked") is the story — say it plainly and suggest the likely fix (packaging, listing photos, sizing note) as a suggestion, not an instruction.
4. No spike → no message.

## Weekly Win-Back List

**When:** weekly, same weekday (default Monday morning).
**Purpose:** customers who used to buy and went quiet are the cheapest sales a store has.

1. Run `woo.py lapsed --days 90` (the owner may prefer 60 or 120 — ask once, remember it). The output is approximate by design; keep that word in the report.
2. Sort the list by `total_spent` descending and take the top 10. These are real past customers, not leads.
3. For each, note what they bought last if the order detail is cheap to fetch (`woo.py order <last order id>`), so outreach can mention it.
4. Draft — do not send — one short win-back message the owner can paste into their email tool, and offer the approval-gated `create-coupon` for a comeback code (e.g. `BACK10`) as an explicit proposal: code, amount, expiry. The coupon is created only if the owner approves it in this conversation.
5. Shape:

   > **Win-back list — 10 past customers quiet for 90+ days**
   > Top by past spend: [Name] ($X lifetime, last order [item], [date]) …
   > Draft message and a proposed comeback coupon are ready for your approval. Nothing has been sent or created.

## Available connectors

- WooCommerce — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.woocommerce/CONNECTOR.md`.
