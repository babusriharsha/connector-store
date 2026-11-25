# BookSignal for Xero

**Trademark notice:** Xero and its associated designs are trademarks of Xero Limited.

Connect a Xero account to Muse. Once connected, the owner can ask their Muse things like "which invoices are overdue?", "who owes me money?", "what did I spend this month?" — and get answers from their own account's real data, plus a Weekly Cash Brief. It also makes one approval-gated change: creating a DRAFT invoice (never sent).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or the trademark owner named above.
- It runs entirely on the customer's own Muse. The account's data goes from Xero to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.booksignal-xero/bin/xero.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "BookSignal for Xero"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Xero organisation to Muse — invoices, contacts, bank transactions and profit & loss."; the full price and trial terms "Free for 1 month, then $19/month per organisation — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Xero with Plugvana', this is the connector they mean — Plugvana's BookSignal for Xero, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"connect Xero to Muse"**, "connect Xero to Muse", "Xero invoices in Muse", "check my Xero with Muse", "Xero overdue invoices", "Xero profit and loss in Muse", "connect my Xero".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional business (`--demo`, "Harbor Lane Design Studio (DEMO)") and works.
- **Live mode is UNTESTED against a real account.** No live Xero account has been connected yet. The live code follows the official Xero API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one number against Xero itself.

## What the owner needs before connecting

1. A Xero organisation the owner can sign in to and consent for.
2. A Xero developer app registered at developer.xero.com (OAuth 2.0); the owner consents through Xero's own sign-in via Muse's secure flow. After consent, the installing Muse calls GET https://api.xero.com/connections, picks the organisation, and writes its tenant id into `config.json` (see config.example.json) — the tenant id is routing info, not a secret.

Credentials never pass through chat and never live in files. The OAuth consent / token entry happens only on the platform's own sign-in page or Muse's secure capture page.

## Connect the account

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.booksignal-xero`
   - api_hosts: **api.xero.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `bearer`
   - one entry: `access_token` with bearer-header placement (`Authorization: Bearer <token>`). The installing Muse registers exactly this placement; the CLI's LiveClient calls Muse's surrogate helper (`add_surrogate_to_request`) for connection `custom.booksignal-xero`, and the helper applies the registered bearer placement — the real token never appears in the helper process, files, arguments, or logs.
2. The owner completes the platform's own OAuth sign-in/consent through that secure flow (or, where the platform offers one, pastes a self-created access token on the secure capture page only).
3. Where this package includes `config.example.json`, copy it to `config.json` and fill in the routing ids described there. That file holds no secrets.
4. Verify: `python3 bin/xero.py status`. A good result returns `"connected": true`. That first real call is the proof the credential works; nothing validates it at save time.
5. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### API surface used

GET /Organisation, GET /Invoices, GET /Invoices/{id}, GET /Contacts, GET /Accounts, GET /BankTransactions, GET /Payments, GET /Reports/ProfitAndLoss, POST /Invoices (DRAFT only)

Base: `https://api.xero.com/api.xro/2.0` (host `api.xero.com`).

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against the bundled fictional business:

```text
python3 bin/xero.py --demo status
python3 bin/xero.py --demo overdue
```

Demo mode needs no token, no config and no license, and it is the right way to show an owner what the connector does before they connect anything.

## Commands

Read commands (safe, no changes):

```text
python3 bin/xero.py status
    Verify the connection; show the connected organisation.
python3 bin/xero.py invoices [--status AUTHORISED]
python3 bin/xero.py invoice <id>
python3 bin/xero.py contacts
python3 bin/xero.py overdue
    Unpaid (not PAID) invoices whose DueDate has passed, with AmountDue total.
python3 bin/xero.py bank-summary
    Bank-type accounts plus recent bank transactions.
python3 bin/xero.py profit-loss [--period YYYY-MM]
    The ProfitAndLoss report; --period restricts it to that month.
```

Write command — **approval-gated, always**:

```text
python3 bin/xero.py create-invoice --contact-id <id> --description "..." --amount 100.00 [--due-date YYYY-MM-DD] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my books updated" is not approval for a specific invoice.
- The write only ever creates a **DRAFT** invoice. This connector never sends an invoice, never marks one paid, and never moves money.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode a `--yes` write is simulated and says so.)

## Workflows

Scheduled briefs (the Weekly Cash Brief) are defined in the companion **SKILL.md** in this package. Offer them after the connection verifies; they are just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.booksignal-xero` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. One license covers one organisation: the license check hashes the connected account/business identity from `config.json` locally; the raw identity is never sent.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)". If the log chat is missing or was deleted, recreate it and backfill entries for every Plugvana connector installed on this Muse from their live license status (see INSTALL.md) — the license server and the installed connectors are the record; the chat is a view.

## Limits and notes

- Every live call needs the `Xero-tenant-id` header; LiveClient adds it from `config.json` (`tenant_id`). A missing/blank tenant id means Xero will reject the call — set config.json at install time.
- Xero access tokens are short-lived (about 30 minutes); the secure flow's refresh handling is Muse's/platform's, not this CLI's.
- Xero answers with PascalCase field names (InvoiceID, AmountDue, DueDate); the CLI passes records through unchanged.
- Apps created on/after 2 March 2026 use Xero's granular scopes; request only the accounting scopes this connector needs (transactions, contacts, settings/accounts, reports read).
- Redirects on authenticated requests are refused, so a host mismatch fails loudly instead of leaking the request elsewhere.

## Related skills

- Xero Workflows — `SKILL.md` in this package (Weekly Cash Brief).
