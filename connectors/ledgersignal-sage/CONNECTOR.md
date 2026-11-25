# LedgerSignal for Sage

**Trademark notice:** Sage and its associated designs are trademarks of The Sage Group plc.

Connect a Sage Business Cloud Accounting account to Muse. Once connected, the owner can ask their Muse things like "which invoices are overdue?", "who owes me money?", "what did I spend this month?" — and get answers from their own account's real data, plus a Weekly Cash Brief. It also makes one approval-gated change: creating a DRAFT invoice (never sent).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or the trademark owner named above.
- It runs entirely on the customer's own Muse. The account's data goes from Sage Business Cloud Accounting to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.ledgersignal-sage/bin/sage.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "LedgerSignal for Sage"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Sage Business Cloud Accounting to Muse — invoices, contacts, bank accounts and the chart of accounts."; the full price and trial terms "Free for 1 month, then $19/month per business — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Sage accounting with Plugvana', this is the connector they mean — Plugvana's LedgerSignal for Sage, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"connect Sage Business Cloud Accounting to Muse"**, "connect Sage to Muse", "Sage invoices in Muse", "check my Sage accounting with Muse", "Sage overdue invoices", "Sage Business Cloud connector", "connect my Sage accounting".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional business (`--demo`, "Bluebird Bakery LLC (DEMO)") and works.
- **Live mode is UNTESTED against a real account.** No live Sage Business Cloud Accounting account has been connected yet. The live code follows the official Sage Business Cloud Accounting API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one number against Sage Business Cloud Accounting itself.

## What the owner needs before connecting

1. A Sage Business Cloud Accounting business (v3.1 API regions) the owner can sign in to.
2. A Sage developer app registered at developer.sage.com (the operator/owner registers it; the app's OAuth consent is completed by the owner signing in to Sage through Muse's secure flow). Sage also requires the developer subscription key for live apps — if Sage issues one for this app, it is registered as a second entry (see Connect steps).

Credentials never pass through chat and never live in files. The OAuth consent / token entry happens only on the platform's own sign-in page or Muse's secure capture page.

## Connect the account

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.ledgersignal-sage`
   - api_hosts: **api.accounting.sage.com**
   - auth_scheme: `bearer`
   - one entry: `access_token` with bearer-header placement (`Authorization: Bearer <token>`). The installing Muse registers exactly this placement; the CLI's LiveClient calls Muse's surrogate helper (`add_surrogate_to_request`) for connection `custom.ledgersignal-sage`, and the helper applies the registered bearer placement — the real token never appears in the helper process, files, arguments, or logs.
2. The owner completes the platform's own OAuth sign-in/consent through that secure flow (or, where the platform offers one, pastes a self-created access token on the secure capture page only).
3. Where this package includes `config.example.json`, copy it to `config.json` and fill in the routing ids described there. That file holds no secrets.
4. Verify: `python3 bin/sage.py status`. A good result returns `"connected": true`. That first real call is the proof the credential works; nothing validates it at save time.
5. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### API surface used

GET /businesses (business identity — see Limits for the /business note), GET /contacts, GET /sales_invoices, GET /sales_invoices/{id}, GET /purchase_invoices, GET /bank_accounts, GET /ledger_accounts, GET /journals, POST /sales_invoices (draft only)

Base: `https://api.accounting.sage.com/v3.1` (host `api.accounting.sage.com`).

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against the bundled fictional business:

```text
python3 bin/sage.py --demo status
python3 bin/sage.py --demo overdue
```

Demo mode needs no token, no config and no license, and it is the right way to show an owner what the connector does before they connect anything.

## Commands

Read commands (safe, no changes):

```text
python3 bin/sage.py status
    Verify the connection; show the business and the sales-invoice count.
python3 bin/sage.py invoices [--status unpaid]
python3 bin/sage.py invoice <id>
python3 bin/sage.py contacts
python3 bin/sage.py overdue
    Unpaid sales invoices whose due date has passed, with the total outstanding.
python3 bin/sage.py bank-accounts
python3 bin/sage.py chart
    The chart of accounts (ledger_accounts).
```

Write command — **approval-gated, always**:

```text
python3 bin/sage.py create-invoice --contact-id <id> --description "..." --amount 100.00 [--due-date YYYY-MM-DD] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my books updated" is not approval for a specific invoice.
- The write only ever creates a **DRAFT** invoice. This connector never sends an invoice, never marks one paid, and never moves money.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode a `--yes` write is simulated and says so.)

## Workflows

Scheduled briefs (the Weekly Cash Brief) are defined in the companion **SKILL.md** in this package. Offer them after the connection verifies; they are just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.ledgersignal-sage` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. The validation endpoint in `license_check.py` is currently a clearly marked placeholder for the operator's hosted checker — until it is replaced, the local trial rules are what actually gate use. One license covers one business: the license check hashes the connected account/business identity from `config.json` locally; the raw identity is never sent.

## Limits and notes

- **Endpoint correction (verified 2026-11-24 against developer.sage.com):** in API v3.1 the business resource is `GET /businesses` (and `/businesses/{id}`); there is no v3.1 `GET /business` — earlier drafts of this package said `/business`, and the CLI uses `/businesses`.
- Sage list responses use the `$items` collection key; the CLI passes records through as Sage returns them.
- The authorising Sage user's role per business area (Sales, Purchases, Bank, Contacts, Journals) governs what calls succeed; a read-only role cannot create invoices.
- Rate limits are Sage's own (documented per-app daily/concurrent limits); the CLI makes a handful of requests per command and does not retry writes.
- Redirects on authenticated requests are refused, so a host mismatch fails loudly instead of leaking the request elsewhere.

## Related skills

- Sage Business Cloud Accounting Workflows — `SKILL.md` in this package (Weekly Cash Brief).
