# The Connector Store

**Independent connectors that link the services you use to your Muse personal AI agent.**

Ask your Muse about your store, sales, inventory and email campaigns in plain words — and get answers from your real data. Every connector runs inside **your own Muse**, on your own accounts. The store never sees your business data.

Published by **CALL SNAP SYSTEMS LLC**, Eureka, Missouri, USA.
*Independent store. Not affiliated with Meta, WooCommerce, Automattic, Etsy, or Mailchimp.*

## The connectors

| Connector | What it does | Price |
|---|---|---|
| [WooCommerce Connector](connectors/woocommerce/) | Store snapshot, orders, refunds, best sellers, low-stock alerts, lapsed customers, Morning Store Brief | Free for 1 month, then **$19/month per store** |
| [Etsy Connector](connectors/etsy/) | Shop snapshot, orders, listings & inventory, reviews, payment ledger, Morning Shop Brief | Free for 1 month, then **$9/month per shop** |
| [Mailchimp Connector](connectors/mailchimp/) | Audience growth, campaign reports in plain numbers, top campaigns, list health checks | Free for 1 month, then **$15/month per account** |

More connectors are on the way — the catalog is growing toward 100+. Every connector is priced and subscribed to on its own. **No bundles, no all-access pass** — you only ever pay for the ones you use.

## How to install a connector

1. Open the connector's folder above and read its `INSTALL.md`.
2. Copy the install prompt from that file and paste it to **your Muse**.
3. Your Muse installs the package, runs the secure sign-in (your credentials never pass through chat), checks the connection, and proves it works with a live snapshot of your own data.

Each connector's `CONNECTOR.md` is the full manual: every command, the setup steps, and the safety rules. Read-only by default; any change a connector can make is shown to you first and needs your approval.

## Pricing rules

- **First month free** on every connector. No card needed to start the trial.
- After the trial, the connector pauses unless you subscribe — it never charges silently.
- Annual billing costs 10 months — two months free.
- Subscriptions are with CALL SNAP SYSTEMS LLC (that's the name on your card statement), processed by Stripe. Cancel anytime.

## The store website

The human-facing store — searchable catalog, full feature lists, pricing and FAQ — lives in [`site/`](site/) and is deployed as a static site.

## Safety

- Credentials are handled only through Muse's secure connection flow — never in chat, never in these files.
- Connectors store nothing on our side; your data stays in your Muse and in the service you connected.
- Every package ships with a demo mode and fictional sample data, so you (or your Muse) can test every command before connecting a real account.
