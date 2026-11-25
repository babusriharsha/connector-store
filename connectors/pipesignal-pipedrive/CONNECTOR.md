# PipeSignal for Pipedrive

**Trademark notice:** Pipedrive is a trademark of Pipedrive Inc. / Vista (Pipedrive). This connector uses the Pipedrive API and is not endorsed or certified by Pipedrive Inc. / Vista (Pipedrive).

Connect a Pipedrive account to Muse. Connects your Pipedrive company to Muse — persons, deals, organisations, activities and pipelines.

- This is an independent connector by CALL SNAP SYSTEMS LLC (Plugvana). It is not affiliated with Meta or Pipedrive Inc. / Vista (Pipedrive).
- It runs entirely on the customer's own Muse. Data goes from Pipedrive to that Muse and nowhere else; the operator stores nothing.
- The CLI is `bin/pipedrive.py` in this package (installed at `/workspace/custom-connectors/custom.pipesignal-pipedrive/bin/pipedrive.py`). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "PipeSignal for Pipedrive"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Pipedrive company to Muse — persons, deals, organisations, activities and pipelines."; the full price and trial terms "Free for 1 month, then $15/month per company — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Pipedrive with Plugvana', this is the connector they mean — Plugvana's PipeSignal for Pipedrive, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"Pipedrive for Muse", **"connect Pipedrive to Muse", **"connect my Pipedrive", **"Pipedrive deals in Muse", **"Pipedrive pipeline in Muse", **"stalled deals in Muse", **"sales activities in Muse".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works; write gates were tested in demo (proposal without `--yes`, simulated with `--yes`).
- **Live mode is UNTESTED against a real Pipedrive account.** No live account was available at build time. Live endpoints are documented Pipedrive v1 paths, but no live Pipedrive company was available at build time, so exact per-field availability (dates, values) is unverified live. The first live connection is the real proof; verify one number against Pipedrive itself.

## What the owner needs before connecting

A Pipedrive account and its API token: in Pipedrive go to Settings, Personal preferences, API and copy the personal API token. (Pipedrive also supports OAuth bearer; this connector registers the api_token route — see connector.yaml.)

## Connect

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with: provider slug `custom.pipesignal-pipedrive`, api_hosts ["api.pipedrive.com", "plugvana-licenses.vercel.app"], auth_scheme `api_key`, one entry `api_token` with query-parameter placement named `api_token` (Muse's surrogate helper applies the registered placement on egress to api.pipedrive.com). The owner pastes the API token on Muse's secure capture page, never in chat. Note: Pipedrive also offers a company-domain host variant (companydomain.pipedrive.com); this connector uses api.pipedrive.com as documented in connector.yaml.
2. Verify: `python3 bin/pipedrive.py status`. That first real call is the proof the credential works; nothing validates it at save time.
3. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/pipedrive.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The value it receives is a surrogate (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to the registered host `api.pipedrive.com`, applying the placement registered for the connection. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

```text
python3 bin/pipedrive.py --demo status
```

Demo mode needs no credential, no config and no license, and is the right way to show an owner what the connector does before they connect anything. All demo people, companies and deals are clearly fictional.

## Commands

```text
status — verify the connection (lists pipelines)
persons [--limit 20] — list persons
person <id> — one person
deals [--status open|won|lost] [--limit 50] — list deals (GET /deals?status=open etc.)
deal <id> — one deal
orgs — list organisations
activities [--days N] — list activities, window-filtered client-side when dates allow
pipelines — list pipelines
add-activity --subject <text> [--type call] [--person-id] [--deal-id] [--due-date YYYY-MM-DD] [--yes] — APPROVAL-GATED WRITE (POST /activities)
```

Real API paths used: GET /persons, GET /persons/{id}, GET /deals, GET /deals/{id}, GET /organizations, GET /activities, GET /pipelines, POST /activities — all under https://api.pipedrive.com/v1.

## Write rules — approval-gated, always

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep my CRM updated" is not approval for a specific record.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying. (In demo mode the write is simulated and marked as such.)
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow in SKILL.md (Stalled Deals Sweep) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting, reads only.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely (exit 3) and print how to subscribe: $15/month per company at Plugvana by CALL SNAP SYSTEMS LLC. Demo mode always works. Subscribers add their license key to the `custom.pipesignal-pipedrive` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: `shop_hash` is a one-way SHA-256 of the account identity from config.json/env (PIPEDRIVE_COMPANY_IDENTITY), computed locally; when no identity is known the hash is empty rather than blocking a command, and the raw identity is never sent.

## Limits and notes

- Live endpoints are documented Pipedrive v1 paths, but no live Pipedrive company was available at build time, so exact per-field availability (dates, values) is unverified live.
- Rate limits are Pipedrive's own; the CLI makes a handful of requests per command and does not retry writes.
- Exit codes: 0 success, 1 API/runtime error (JSON on stdout), 2 write gate stopped a change, 3 license inactive.
