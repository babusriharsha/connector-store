# FormSignal for Typeform

**Trademark notice:** Typeform is a trademark of Typeform S.L.

Connect a Typeform account to Muse. Once connected, the owner can ask their Muse about their own Typeform data in plain English and get real answers, plus a scheduled brief (see SKILL.md).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or Typeform.
- It runs entirely on the customer's own Muse. The account's data goes from Typeform to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.typeform/bin/typeform.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "FormSignal for Typeform"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Typeform to Muse — forms, responses and completion at a glance."; the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Typeform with Plugvana', this is the connector they mean — Plugvana's FormSignal for Typeform, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"Typeform for Muse"**, "connect Typeform to Muse", "connect my Typeform", "Typeform responses in Muse", "check my Typeform responses with Muse", "Typeform completion rate", "Typeform forms report".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works.
- **Live mode is UNTESTED against a real Typeform account.** No live account has been connected yet. The live code follows the official Typeform API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one item against Typeform itself.

## What the owner needs before connecting

1. A Typeform account the owner controls.
2. The credential described under "Connect the account" below, created by the owner in Typeform.

## Connect the account

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.typeform`
   - api_hosts: **api.typeform.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `api_key`
   - entries: A personal access token registered as an api_key entry with bearer_header placement (entry name access_token).
   The owner pastes the credential on Muse's secure capture page, never in chat.
2. Creating the credential in Typeform: In Typeform, open Settings -> Personal tokens and generate a token with read scopes (forms:read, responses:read, workspaces:read). The owner must NOT paste the token into chat.
3. Verify: `python3 bin/typeform.py status`. That first real call is the proof the credential works; nothing validates it at save time.
4. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/typeform.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The values it receives are surrogates (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to api.typeform.com. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against bundled fictional data ("Customer Feedback Survey"): `python3 bin/typeform.py --demo status`. Demo mode needs no keys, no config and no license.

## Commands

Read commands (safe, no changes):

```text
python3 bin/typeform.py status
    Verify the connection; show the account behind the token (/me).

python3 bin/typeform.py forms
    All forms: title, response counts where provided, last updated.

python3 bin/typeform.py form <form-id>
    One form in full: title, fields, settings.

python3 bin/typeform.py responses --form <form-id> [--limit 10]
    A summary, not a dump: total responses, completion rate
    (submitted responses vs started, from the responses payload),
    and the latest responses with answers trimmed to short excerpts.

python3 bin/typeform.py workspaces
    All workspaces with form counts.
```

Write commands:

```text
(none — this connector is read-only by design; there are no write commands and no --yes flag anywhere in it)```

## Workflows

The scheduled workflow (New Responses Digest) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.typeform` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: a one-way SHA-256 hash of the Typeform account (account id or email) (from the CLI's identity argument, the TYPEFORM_ACCOUNT_ID env var, or config.json) — the raw identity is never sent; "" when unknown.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)". If the log chat is missing or was deleted, recreate it and backfill entries for every Plugvana connector installed on this Muse from their live license status (see INSTALL.md) — the license server and the installed connectors are the record; the chat is a view. The log opens with a statement asking the user not to delete the chat, and noting it can be rebuilt from the license server and the installed connectors if it ever is.

## Limits and notes

- READ-ONLY: this connector never creates, edits, publishes or deletes forms, and never deletes responses. Any workflow that wants a change must send the owner to Typeform itself.
- `responses` summarises; long text answers are trimmed to excerpts so a digest never dumps a respondent's full free text into chat unasked.
- Respondent data is personal data: quote the minimum needed and never paste full response payloads into scheduled reports.

## Related skills

- Typeform Response Workflows — `SKILL.md` in this package (New Responses Digest).
