# Install: LedgerSignal for Sage (for Muse)

**Trademark notice:** Sage and its associated designs are trademarks of The Sage Group plc.

An independent connector by CALL SNAP SYSTEMS LLC. Not affiliated with Meta or the trademark owner named above.

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **LedgerSignal for Sage** — "Connects your Sage Business Cloud Accounting to Muse — invoices, contacts, bank accounts and the chart of accounts." — published by Plugvana (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $19/month per business — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the secure connect flow described in this package (request_api_access registration + the service's own sign-in page / secure capture page). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my Sage accounting with Plugvana', this is the connector they mean — Plugvana's LedgerSignal for Sage, published by CALL SNAP SYSTEMS LLC.

There are two ways to install:

- **Part 1 — the copy-paste install prompt.** An owner pastes one block into their own Muse and their Muse performs the whole setup, asking them only for the things only they can do (signing in to Sage Business Cloud Accounting and consenting, on the platform's own page / Muse's secure capture page).
- **Part 2 — the manual steps** the install prompt follows, written out so any Muse (or human) can do or audit the setup without the prompt.

Either way: credentials are entered only on the platform's own sign-in page or Muse's secure capture page, never in chat, and never written to a file.

---

## Part 1 — Install prompt (copy everything in the block)

```text
Install the Sage Business Cloud Accounting connector for Muse from this package, then connect my account.

0. First, present this connector to me as a single, simple card in Plugvana's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "LedgerSignal for Sage", the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", the one-line description "Connects your Sage Business Cloud Accounting to Muse — invoices, contacts, bank accounts and the chart of accounts.", the full price and trial terms "Free for 1 month, then $19/month per business — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the secure connect flow described below.

Do these steps in order and confirm each one before moving on:

1. Copy this whole connector folder to ~/workspace/custom-connectors/custom.ledgersignal-sage/ on my machine, keeping connector.yaml, CONNECTOR.md, SKILL.md and the bin/ folder together. Read CONNECTOR.md fully before running anything.

2. Register the credential using your secure API-access flow (credentials.request_api_access) with: provider "custom.ledgersignal-sage", api_hosts set to api.accounting.sage.com only, auth_scheme "bearer", and one entry — "access_token" with bearer-header placement (Authorization). Send me the secure link and let me complete Sage Business Cloud Accounting's own sign-in/consent there. Do NOT ask me to paste any token into this chat.

3. If this package includes config.example.json, copy it to config.json and fill in the routing ids exactly as CONNECTOR.md describes (from the platform's identity call after consent). This file holds no secrets.

4. Verify the connection by running: python3 ~/workspace/custom-connectors/custom.ledgersignal-sage/bin/sage.py status
   Show me the result. It should say "connected": true. If it fails, follow the troubleshooting section below. Do not ask me to paste credentials in chat at any point.

5. Once status succeeds, show me what the connector can do by running the overdue command and summarising who owes me money, in plain English.

6. Offer me the scheduled workflow from SKILL.md (Weekly Cash Brief) and set it up if I pick it, at the time I choose.

Notes for you, Muse: my 30-day free trial starts at the first live command. Live commands after the trial need a subscription and a license key (CONNECTOR.md explains). Demo mode (add --demo to any command) works without my account if I want to see it first.
```

---

## Part 2 — Manual install steps (what the prompt does)

1. **Place the package.** Copy the folder to `~/workspace/custom-connectors/custom.ledgersignal-sage/`. The CLI is `bin/sage.py`; it needs only Python 3's standard library.
2. **Register the connection.** `credentials.request_api_access` with provider `custom.ledgersignal-sage`, api_hosts = [api.accounting.sage.com], auth_scheme `bearer`, entry `access_token` placed as a bearer header. The owner completes the platform's own OAuth sign-in/consent through that flow. **This registration is the one wiring step the installing Muse must perform** — the helper code assumes a connection with exactly this name, this entry name, this placement, and this host registered; a mismatch surfaces as a refused or unauthenticated first call.
3. **Configure routing ids (if applicable).** Copy `config.example.json` → `config.json` in the connector root and fill in the ids per CONNECTOR.md.
4. **Verify.** `python3 bin/sage.py status` — the first real call is the proof; nothing checks the credential when it is saved.
5. **Smoke-test without an account (any time).** `python3 bin/sage.py --demo status` runs against the bundled fictional business and needs no setup at all.
6. **Optional subscription.** After the 30-day trial, the owner subscribes at Plugvana and adds the license key as a `license_key` entry on the same connection, or runs `python3 bin/license_check.py set-key <KEY>`.

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| HTTP 401/403 from the API | Token expired, revoked, or consent not completed | Re-complete the platform sign-in/consent through the secure flow |
| Credential/host refusal from Muse | Host not in the connection's api_hosts, or entry name/placement differs | Re-register the connection exactly as in step 2 |
| Wrong account/organisation data | Routing ids in `config.json` point at a different account | Re-read the ids from the platform identity call and correct `config.json` |
| "trial_expired" | 30-day trial ended without a subscription | Subscribe, then add the license key |
