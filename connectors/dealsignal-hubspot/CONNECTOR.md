# DealSignal for HubSpot

**Trademark notice:** HubSpot is a trademark of HubSpot, Inc.. This connector uses the HubSpot API and is not endorsed or certified by HubSpot, Inc..

Connect a HubSpot account to Muse. Connects your HubSpot CRM to Muse — contacts, companies, deals and pipelines in plain numbers.

- This is an independent connector by CALL SNAP SYSTEMS LLC (Plugvana). It is not affiliated with Meta or HubSpot, Inc..
- It runs entirely on the customer's own Muse. Data goes from HubSpot to that Muse and nowhere else; the operator stores nothing.
- The CLI is `bin/hubspot.py` in this package (installed at `/workspace/custom-connectors/custom.dealsignal-hubspot/bin/hubspot.py`). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "DealSignal for HubSpot"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your HubSpot CRM to Muse — contacts, companies, deals and pipelines in plain numbers."; the full price and trial terms "Free for 1 month, then $19/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my HubSpot with Plugvana', this is the connector they mean — Plugvana's DealSignal for HubSpot, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"HubSpot for Muse", **"connect HubSpot to Muse", **"connect my HubSpot", **"HubSpot deals in Muse", **"HubSpot pipeline report in Muse", **"CRM pipeline in Muse", **"HubSpot contacts in Muse".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works; write gates were tested in demo (proposal without `--yes`, simulated with `--yes`).
- **Live mode is UNTESTED against a real HubSpot account.** No live account was available at build time. Live endpoints are documented HubSpot CRM v3 paths, but no live HubSpot portal was available at build time, so response fields beyond the documented results/properties/id shape are unverified live. The first live connection is the real proof; verify one number against HubSpot itself.

## What the owner needs before connecting

A HubSpot account and a Private App access token: in HubSpot go to Settings, Integrations, Private Apps, Create a private app, grant read scopes for contacts, companies and deals (and write scope for contacts if you want the approval-gated create-contact), and copy the access token shown once.

## Connect

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with: provider slug `custom.dealsignal-hubspot`, api_hosts ["api.hubapi.com", "plugvana-licenses.vercel.app"], auth_scheme bearer, one entry `access_token` with bearer_header placement. The owner pastes the Private App access token on Muse's secure capture page, never in chat.
2. Verify: `python3 bin/hubspot.py status`. That first real call is the proof the credential works; nothing validates it at save time.
3. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/hubspot.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The value it receives is a surrogate (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to the registered host `api.hubapi.com`, applying the placement registered for the connection. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

```text
python3 bin/hubspot.py --demo status
```

Demo mode needs no credential, no config and no license, and is the right way to show an owner what the connector does before they connect anything. All demo people, companies and deals are clearly fictional.

## Commands

```text
status — verify the connection (samples contacts, deals, companies)
contacts [--limit 20] — list contacts
contact <id> — one contact
companies [--limit 20] — list companies
deals [--stage <stage>] [--limit 20] — list deals, or search by stage (POST /crm/v3/objects/deals/search)
deal <id> — one deal
pipeline — deal pipelines and stages (GET /crm/v3/pipelines/deals)
create-contact --email <email> [--first-name] [--last-name] [--company] [--yes] — APPROVAL-GATED WRITE (POST /crm/v3/objects/contacts)
```

Real API paths used: GET /crm/v3/objects/contacts (with ?properties=), GET /crm/v3/objects/companies, GET /crm/v3/objects/deals, GET /crm/v3/objects/contacts/{id}, GET /crm/v3/objects/deals/{id}, POST /crm/v3/objects/deals/search, GET /crm/v3/pipelines/deals, POST /crm/v3/objects/contacts.

## Write rules — approval-gated, always

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my CRM updated" is not approval for a specific record.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode the write is simulated and marked as such.)
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow in SKILL.md (Pipeline Morning Brief) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting, reads only.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely (exit 3) and print how to subscribe: $19/month per account at Plugvana by CALL SNAP SYSTEMS LLC. Demo mode always works. Subscribers add their license key to the `custom.dealsignal-hubspot` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: `shop_hash` is a one-way SHA-256 of the account identity from config.json/env (HUBSPOT_ACCOUNT_IDENTITY), computed locally; when no identity is known the hash is empty rather than blocking a command, and the raw identity is never sent.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)".

## Limits and notes

- Live endpoints are documented HubSpot CRM v3 paths, but no live HubSpot portal was available at build time, so response fields beyond the documented results/properties/id shape are unverified live.
- Rate limits are HubSpot's own; the CLI makes a handful of requests per command and does not retry writes.
- Exit codes: 0 success, 1 API/runtime error (JSON on stdout), 2 write gate stopped a change, 3 license inactive.
