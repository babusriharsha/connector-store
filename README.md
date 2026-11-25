# Plugvana

**Independent connectors that link the services you use to your Muse personal AI agent.**

**The store website is the public front door: [connector-store.vercel.app](https://connector-store.vercel.app/)** — this repository is the distribution package behind it, not the storefront.

Published by **CALL SNAP SYSTEMS LLC**, Eureka, Missouri, USA.
*Independent store. Not affiliated with Meta, WooCommerce, Automattic, Etsy, or Mailchimp.*

| <img src="assets/icons/woocommerce.svg" width="72" alt="ShopSignal for WooCommerce"> | <img src="assets/icons/etsy.svg" width="72" alt="SellSignal for Etsy"> | <img src="assets/icons/mailchimp.svg" width="72" alt="ListSignal for Mailchimp"> |
| :---: | :---: | :---: |
| **ShopSignal for WooCommerce** | **SellSignal for Etsy** | **ListSignal for Mailchimp** |
| Free for 1 month · then $19/month | Free for 1 month · then $9/month | Free for 1 month · then $15/month |
| [**Connect →**](connectors/woocommerce/INSTALL.md) | [**Connect →**](connectors/etsy/INSTALL.md) | [**Connect →**](connectors/mailchimp/INSTALL.md) |

GitHub can't copy on click, so here Connect opens the install prompt — use GitHub's copy button on that page, then paste it in your Muse. On the store website, the same Connect button copies it in one click.

## Pricing rules

- **First month free** on every connector. No card needed to start the trial.
- After the trial, the connector pauses unless you subscribe — it never charges silently.
- Every connector is priced and subscribed to on its own. **No bundles, no all-access pass.**
- Annual billing costs 10 months — two months free. Subscriptions are with CALL SNAP SYSTEMS LLC (that's the name on your card statement), processed by Stripe. Cancel anytime.

## Safety

- Credentials are handled only through Muse's secure connection flow — never in chat, never in these files.
- Connectors store nothing on our side; your data stays in your Muse and in the service you connected.
- Read-only by default; any change a connector can make is shown to you first and needs your approval.
- Every package ships with a demo mode and fictional sample data, so you (or your Muse) can test every command before connecting a real account.

## For Muse / discovery

- **ShopSignal for WooCommerce** (`connectors/woocommerce/`) — connect a WooCommerce store on WordPress to Muse: store snapshot, orders, refunds, best sellers, inventory and low-stock alerts, lapsed customers, Morning Store Brief.
- **SellSignal for Etsy** (`connectors/etsy/`) — connect an Etsy shop to Muse: shop snapshot, orders, listings and inventory, reviews, payment ledger, Morning Shop Brief.
- **ListSignal for Mailchimp** (`connectors/mailchimp/`) — connect a Mailchimp account to Muse: audience growth, campaign reports in plain numbers, top campaigns, list health checks.

Each connector's `INSTALL.md` holds its install prompt and manual steps; its `CONNECTOR.md` is the full manual. The human-facing store website lives in [`site/`](site/).
