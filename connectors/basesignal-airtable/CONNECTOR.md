# BaseSignal for Airtable

**Trademark notice:** Airtable is a trademark of Formagrid, Inc. d/b/a Airtable. This connector uses the Airtable API and is not endorsed or certified by Formagrid, Inc. d/b/a Airtable.

Connect a Airtable account to Muse. Connects your Airtable base to Muse — bases, tables and records you can ask about in plain English.

- This is an independent connector by CALL SNAP SYSTEMS LLC (Plugvana). It is not affiliated with Meta or Formagrid, Inc. d/b/a Airtable.
- It runs entirely on the customer's own Muse. Data goes from Airtable to that Muse and nowhere else; the operator stores nothing.
- The CLI is `bin/airtable.py` in this package (installed at `/workspace/custom-connectors/custom.basesignal-airtable/bin/airtable.py`). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "BaseSignal for Airtable"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Airtable base to Muse — bases, tables and records you can ask about in plain English."; the full price and trial terms "Free for 1 month, then $15/month per base — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Airtable with Plugvana', this is the connector they mean — Plugvana's BaseSignal for Airtable, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"Airtable for Muse", **"connect Airtable to Muse", **"connect my Airtable", **"Airtable records in Muse", **"Airtable base in Muse", **"check my Airtable base with Muse".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works; write gates were tested in demo (proposal without `--yes`, simulated with `--yes`).
- **Live mode is UNTESTED against a real Airtable account.** No live account was available at build time. Live endpoints are documented Airtable Web API paths, but no live Airtable base was available at build time, so token scopes and per-table field shapes are unverified live. The first live connection is the real proof; verify one number against Airtable itself.

## What the owner needs before connecting

An Airtable account and a Personal Access Token: in Airtable's developer hub create a token with data.records:read (and data.records:write for the approval-gated create-record) scoped to the base(s) to connect, and copy it once. You also need the base id (starts with app, shown in the base's API documentation/URL) and the default table name.

## Connect

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with: provider slug `custom.basesignal-airtable`, api_hosts ["api.airtable.com", "plugvana-licenses.vercel.app"], auth_scheme bearer, one entry `access_token` with bearer_header placement. The owner pastes the Personal Access Token on Muse's secure capture page, never in chat. Then copy `config.example.json` to `config.json` and set `base_id` and `default_table` — routing info only, no secrets.
2. Verify: `python3 bin/airtable.py status`. That first real call is the proof the credential works; nothing validates it at save time.
3. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/airtable.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The value it receives is a surrogate (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to the registered host `api.airtable.com`, applying the placement registered for the connection. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

```text
python3 bin/airtable.py --demo status
```

Demo mode needs no credential, no config and no license, and is the right way to show an owner what the connector does before they connect anything. All demo people, companies and deals are clearly fictional.

## Commands

```text
status — verify the connection (GET /meta/bases) plus configured base/table
bases — list bases (GET /meta/bases)
tables [--base <baseId>] — GET /meta/bases/{baseId}/tables
records --table <name> [--base] [--limit 20] [--view <view>] — GET /{baseId}/{table}
record --table <name> <id> [--base] — GET /{baseId}/{table}/{recordId}
create-record --table <name> --field Key=Value [--field ...] [--yes] — APPROVAL-GATED WRITE (POST /{baseId}/{table})
```

Real API paths used: GET /meta/bases, GET /meta/bases/{baseId}/tables, GET /{baseId}/{table}, GET /{baseId}/{table}/{recordId}, POST /{baseId}/{table} — all under https://api.airtable.com/v0. Base id and default table live in config.json (see config.example.json).

## Write rules — approval-gated, always

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my CRM updated" is not approval for a specific record.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode the write is simulated and marked as such.)
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow in SKILL.md (Base Changes Digest) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting, reads only.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely (exit 3) and print how to subscribe: $15/month per base at Plugvana by CALL SNAP SYSTEMS LLC. Demo mode always works. Subscribers add their license key to the `custom.basesignal-airtable` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: `shop_hash` is a one-way SHA-256 of the account identity from config.json/env (AIRTABLE_BASE_IDENTITY), computed locally; when no identity is known the hash is empty rather than blocking a command, and the raw identity is never sent.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)".

## Limits and notes

- Live endpoints are documented Airtable Web API paths, but no live Airtable base was available at build time, so token scopes and per-table field shapes are unverified live.
- Rate limits are Airtable's own; the CLI makes a handful of requests per command and does not retry writes.
- Exit codes: 0 success, 1 API/runtime error (JSON on stdout), 2 write gate stopped a change, 3 license inactive.
