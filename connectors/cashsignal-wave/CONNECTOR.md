# CashSignal for Wave

**Trademark notice:** Wave and its associated designs are trademarks of Wave Financial Inc. (H&R Block).

Connect a Wave account to Muse. Once connected, the owner can ask their Muse things like "which invoices are overdue?", "who owes me money?", "what did I spend this month?" — and get answers from their own account's real data, plus a Weekly Cash Brief. It also makes one approval-gated change: creating a DRAFT invoice (never sent).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or the trademark owner named above.
- It runs entirely on the customer's own Muse. The account's data goes from Wave to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.cashsignal-wave/bin/wave.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "CashSignal for Wave"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Wave accounting to Muse — businesses, invoices, customers and accounts via Wave's GraphQL API."; the full price and trial terms "Free for 1 month, then $9/month per business — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Wave accounting with Plugvana', this is the connector they mean — Plugvana's CashSignal for Wave, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"connect Wave to Muse"**, "connect Wave to Muse", "Wave accounting in Muse", "check my Wave invoices with Muse", "Wave overdue invoices", "Wave GraphQL connector", "connect my Wave accounting".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional business (`--demo`, "Lantern Books & Gifts (DEMO)") and works.
- **Live mode is UNTESTED against a real account.** No live Wave account has been connected yet. The live code follows the official Wave API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one number against Wave itself.

## What the owner needs before connecting

1. A Wave account with at least one business.
2. API access from Wave's developer portal (developer.waveapps.com): either an OAuth app the owner consents to through Wave's own sign-in via Muse's secure flow, or a Full Access Token the owner creates in the developer portal and pastes only into Muse's secure capture page — never in chat. Business ids are discovered with the `businesses` command; they are routing info, not secrets.

Credentials never pass through chat and never live in files. The OAuth consent / token entry happens only on the platform's own sign-in page or Muse's secure capture page.

## Connect the account

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.cashsignal-wave`
   - api_hosts: **gql.waveapps.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `bearer`
   - one entry: `access_token` with bearer-header placement (`Authorization: Bearer <token>`). The installing Muse registers exactly this placement; the CLI's LiveClient calls Muse's surrogate helper (`add_surrogate_to_request`) for connection `custom.cashsignal-wave`, and the helper applies the registered bearer placement — the real token never appears in the helper process, files, arguments, or logs.
2. The owner completes the platform's own OAuth sign-in/consent through that secure flow (or, where the platform offers one, pastes a self-created access token on the secure capture page only).
3. Where this package includes `config.example.json`, copy it to `config.json` and fill in the routing ids described there. That file holds no secrets.
4. Verify: `python3 bin/wave.py status`. A good result returns `"connected": true`. That first real call is the proof the credential works; nothing validates it at save time.
5. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### API surface used

POST https://gql.waveapps.com/graphql/public for everything: query `user`, query `businesses`, query `business(id) { invoices }`, query `business(id) { customers }`, query `business(id) { accounts }`, query `business(id) { products }` (products are how invoice lines are priced), mutation `invoiceCreate` (DRAFT only)

Base: `https://gql.waveapps.com/graphql/public` (host `gql.waveapps.com`).

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against the bundled fictional business:

```text
python3 bin/wave.py --demo status
python3 bin/wave.py --demo overdue
```

Demo mode needs no token, no config and no license, and it is the right way to show an owner what the connector does before they connect anything.

## Commands

Read commands (safe, no changes):

```text
python3 bin/wave.py status
    Verify the connection; show the signed-in Wave user.
python3 bin/wave.py businesses
    List the account's businesses and their ids (needed by the commands below).
python3 bin/wave.py invoices --business <id>
python3 bin/wave.py customers --business <id>
python3 bin/wave.py accounts --business <id>
python3 bin/wave.py overdue --business <id>
    Invoices for the business whose dueDate has passed and which are not PAID.
```

Write command — **approval-gated, always**:

```text
python3 bin/wave.py create-invoice --business <id> --customer-id <id> --product-id <id> --amount 100.00 [--description "..."] [--due-date YYYY-MM-DD] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my books updated" is not approval for a specific invoice.
- The write only ever creates a **DRAFT** invoice. This connector never sends an invoice, never marks one paid, and never moves money.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode a `--yes` write is simulated and says so.)

## Workflows

Scheduled briefs (the Weekly Cash Brief) are defined in the companion **SKILL.md** in this package. Offer them after the connection verifies; they are just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.cashsignal-wave` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. One license covers one business: the license check hashes the connected account/business identity from `config.json` locally; the raw identity is never sent.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)". If the log chat is missing or was deleted, recreate it and backfill entries for every Plugvana connector installed on this Muse from their live license status (see INSTALL.md) — the license server and the installed connectors are the record; the chat is a view.

## Limits and notes

- Wave is GraphQL-only: a single POST endpoint, and HTTP 200 can still carry a GraphQL `errors` array — the CLI surfaces those as errors.
- Connection-style fields (invoices/customers/products) require a `sort` argument in Wave's schema; the CLI's documents include one. Accounts listing follows the same connection pattern.
- Wave invoice lines must reference an existing product (`productId` is required by `InvoiceCreateItemInput`) — there is no free-text-only line; find product ids from the business's products in Wave.
- A full-access token reaches every business on the account; the per-command `--business <id>` flag is what scopes each read.
- Redirects on authenticated requests are refused, so a host mismatch fails loudly instead of leaking the request elsewhere.

## Related skills

- Wave Workflows — `SKILL.md` in this package (Weekly Cash Brief).
