# BillSignal for FreshBooks

**Trademark notice:** FreshBooks and its associated designs are trademarks of FreshBooks (2ndSite Inc. / FreshBooks).

Connect a FreshBooks account to Muse. Once connected, the owner can ask their Muse things like "which invoices are overdue?", "who owes me money?", "what did I spend this month?" — and get answers from their own account's real data, plus a Weekly Cash Brief. It also makes one approval-gated change: creating a DRAFT invoice (never sent).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or the trademark owner named above.
- It runs entirely on the customer's own Muse. The account's data goes from FreshBooks to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.billsignal-freshbooks/bin/freshbooks.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "BillSignal for FreshBooks"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your FreshBooks account to Muse — invoices, clients, expenses, payments and tracked time."; the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my FreshBooks with Plugvana', this is the connector they mean — Plugvana's BillSignal for FreshBooks, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"connect FreshBooks to Muse"**, "connect FreshBooks to Muse", "FreshBooks invoices in Muse", "check my FreshBooks with Muse", "FreshBooks expenses in Muse", "FreshBooks time tracking report", "connect my FreshBooks".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional business (`--demo`, "Solstice Cleaning Co (DEMO)") and works.
- **Live mode is UNTESTED against a real account.** No live FreshBooks account has been connected yet. The live code follows the official FreshBooks API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one number against FreshBooks itself.

## What the owner needs before connecting

1. A FreshBooks account the owner can sign in to and consent for.
2. A FreshBooks developer app (OAuth 2.0 authorization-code flow — the only grant FreshBooks supports); the owner consents through FreshBooks' own sign-in via Muse's secure flow. After consent, the installing Muse calls GET /auth/api/v1/users/me, reads the business membership's `account_id` (and numeric business `id`), and writes them into `config.json` (see config.example.json) — these ids are routing info, not secrets.

Credentials never pass through chat and never live in files. The OAuth consent / token entry happens only on the platform's own sign-in page or Muse's secure capture page.

## Connect the account

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.billsignal-freshbooks`
   - api_hosts: **api.freshbooks.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `bearer`
   - one entry: `access_token` with bearer-header placement (`Authorization: Bearer <token>`). The installing Muse registers exactly this placement; the CLI's LiveClient calls Muse's surrogate helper (`add_surrogate_to_request`) for connection `custom.billsignal-freshbooks`, and the helper applies the registered bearer placement — the real token never appears in the helper process, files, arguments, or logs.
2. The owner completes the platform's own OAuth sign-in/consent through that secure flow (or, where the platform offers one, pastes a self-created access token on the secure capture page only).
3. Where this package includes `config.example.json`, copy it to `config.json` and fill in the routing ids described there. That file holds no secrets.
4. Verify: `python3 bin/freshbooks.py status`. A good result returns `"connected": true`. That first real call is the proof the credential works; nothing validates it at save time.
5. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### API surface used

GET /auth/api/v1/users/me (identity -> account id), GET /accounting/account/{accountId}/users/clients, GET /accounting/account/{accountId}/invoices/invoices, GET /accounting/account/{accountId}/invoices/invoices/{id}, GET /accounting/account/{accountId}/expenses/expenses, GET /accounting/account/{accountId}/payments/payments, GET /accounting/account/{accountId}/time_entries/time_entries (see Limits), POST /accounting/account/{accountId}/invoices/invoices (draft only)

Base: `https://api.freshbooks.com` (host `api.freshbooks.com`).

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against the bundled fictional business:

```text
python3 bin/freshbooks.py --demo status
python3 bin/freshbooks.py --demo overdue
```

Demo mode needs no token, no config and no license, and it is the right way to show an owner what the connector does before they connect anything.

## Commands

Read commands (safe, no changes):

```text
python3 bin/freshbooks.py status
    Verify the connection; show the signed-in identity and its business memberships.
python3 bin/freshbooks.py invoices
python3 bin/freshbooks.py invoice <id>
python3 bin/freshbooks.py clients
python3 bin/freshbooks.py expenses [--days 30]
python3 bin/freshbooks.py payments
python3 bin/freshbooks.py time
    Time entries with a total-hours rollup.
```

Write command — **approval-gated, always**:

```text
python3 bin/freshbooks.py create-invoice --client-id <id> --description "..." --amount 100.00 [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my books updated" is not approval for a specific invoice.
- The write only ever creates a **DRAFT** invoice. This connector never sends an invoice, never marks one paid, and never moves money.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode a `--yes` write is simulated and says so.)

## Workflows

Scheduled briefs (the Weekly Cash Brief) are defined in the companion **SKILL.md** in this package. Offer them after the connection verifies; they are just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.billsignal-freshbooks` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. One license covers one account: the license check hashes the connected account/business identity from `config.json` locally; the raw identity is never sent.

## Limits and notes

- **Host correction (verified 2026-11-24 against FreshBooks' published API examples):** the API host is `api.freshbooks.com` (plural 'FreshBooks'); an earlier draft of this package said `api.freshbook.com` — the CLI and this package use the plural host.
- **Clients path:** FreshBooks' own examples use `/accounting/account/{id}/users/clients` (not `/clients/clients`); the CLI uses the `users/clients` form.
- **Time entries caveat:** FreshBooks splits its API — accounting resources live under `/accounting/account/{account_id}/...`, while time tracking in FreshBooks' own docs lives under `/timetracking/business/{business_id}/time_entries` using the numeric business id (also stored in config.json). The `time` command currently calls the accounting-style path given in this package's original spec (`/accounting/account/{id}/time_entries/time_entries`); treat `time` as the least-verified command and check it first on the first live connection.
- FreshBooks list responses nest records under `response.result`; the CLI unwraps that envelope.
- List calls are capped by FreshBooks (100 rows per page in their docs); very large accounts get the first page per command in this version.
- Redirects on authenticated requests are refused, so a host mismatch fails loudly instead of leaking the request elsewhere.

## Related skills

- FreshBooks Workflows — `SKILL.md` in this package (Weekly Cash Brief).
