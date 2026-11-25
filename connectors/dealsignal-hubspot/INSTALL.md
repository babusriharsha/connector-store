# Install: DealSignal for HubSpot (for Muse)

**Trademark notice:** HubSpot is a trademark of HubSpot, Inc.. This connector uses the HubSpot API and is not endorsed or certified by HubSpot, Inc..

An independent connector by CALL SNAP SYSTEMS LLC (Plugvana). Not affiliated with Meta or HubSpot, Inc..

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **DealSignal for HubSpot** — "Connects your HubSpot CRM to Muse — contacts, companies, deals and pipelines in plain numbers." — published by Plugvana (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $19/month per account — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the secure connect flow described in this package (request_api_access registration + the service's own sign-in page / secure capture page). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my HubSpot with Plugvana', this is the connector they mean — Plugvana's DealSignal for HubSpot, published by CALL SNAP SYSTEMS LLC.

There are two ways to install: **Part 1 — the copy-paste install prompt**, and **Part 2 — the manual steps** it follows. Either way: credentials are entered only on Muse's secure capture page, never in chat, and never written to a file.

---

## Part 1 — Install prompt (copy everything in the block)

```text
Install the HubSpot connector for Muse from this package, then connect my account.

0. First, present this connector to me as a single, simple card in Plugvana's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "DealSignal for HubSpot", the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", the one-line description "Connects your HubSpot CRM to Muse — contacts, companies, deals and pipelines in plain numbers.", the full price and trial terms "Free for 1 month, then $19/month per account — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the secure connect flow described below.

Do these steps in order and confirm each one before moving on:

1. Copy this whole connector folder to ~/workspace/custom-connectors/custom.dealsignal-hubspot/ on my machine, keeping connector.yaml, CONNECTOR.md, SKILL.md and the bin/ folder together. Read CONNECTOR.md fully before running anything.
2. Guide me to create the credential on HubSpot's own pages (see CONNECTOR.md, "What the owner needs"). Tell me I must NOT paste any token or key into this chat.
3. Register the credential using your secure API-access flow (credentials.request_api_access) exactly as CONNECTOR.md's Connect section specifies for custom.dealsignal-hubspot. Send me the secure capture link and wait until I confirm I have saved the credential there.
4. Verify the connection by running: python3 ~/workspace/custom-connectors/custom.dealsignal-hubspot/bin/hubspot.py status
   Show me the result. If it fails, follow the troubleshooting table below. Do not ask me to paste credentials in chat at any point.
5. Once status succeeds, show me one useful read (the first read command in CONNECTOR.md that fits my account) and summarise it in plain English.
6. Offer me the scheduled workflow from SKILL.md (Pipeline Morning Brief) and set it up if I pick it, at the time I choose.

Notes for you, Muse: my 30-day free trial starts at the first live command. Live commands after the trial need a subscription and a license key (CONNECTOR.md explains). Demo mode (add --demo to any command) works without my account if I want to see it first.
```

---

## Part 2 — Manual install steps (what the prompt does)

1. **Place the package.** Copy the folder to `~/workspace/custom-connectors/custom.dealsignal-hubspot/`. The CLI is `bin/hubspot.py`; it needs only Python 3's standard library.
2. **Owner creates the credential** on HubSpot's own pages: A HubSpot account and a Private App access token: in HubSpot go to Settings, Integrations, Private Apps, Create a private app, grant read scopes for contacts, companies and deals (and write scope for contacts if you want the approval-gated create-contact), and copy the access token shown once.
3. **Register the connection.** `credentials.request_api_access` exactly as in CONNECTOR.md's Connect section. **This registration is the one wiring step the installing Muse must perform** — the helper code assumes a connection named `custom.dealsignal-hubspot` with the entry names, placement and host in connector.yaml; a mismatch surfaces as a refused or unauthenticated first call.
4. **Verify.** `python3 bin/hubspot.py status` — the first real call is the proof; nothing checks the credential when it is saved.
5. **Smoke-test without an account (any time).** `python3 bin/hubspot.py --demo status` runs against the bundled fictional data and needs no setup at all.
6. **Optional subscription.** After the 30-day trial, subscribe at Plugvana ($19/month per account) and add the license key as a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>`.

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| HTTP 401/403 | Credential wrong, expired, revoked, or missing scopes | Recreate/refresh the credential on HubSpot's pages; re-save via the secure flow; check scopes |
| Credential/host refusal from Muse | Registered host, entry names or placement differ from connector.yaml | Re-register the connection exactly as in step 3 |
| "redirect refused" | Host variant mismatch (for Zoho: wrong datacenter host; for Pipedrive: company-domain vs api host) | Register the host this connector documents for the user's account |
| "trial_expired" / exit 3 | 30-day trial ended without a subscription | Subscribe, then add the license key |
| Airtable: "No base configured" | config.json missing | Copy config.example.json to config.json and set base_id/default_table |
