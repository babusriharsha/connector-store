# ReachSignal for Constant Contact

**Trademark notice:** Constant Contact is a trademark of Constant Contact, Inc. (Endurance International Group). This connector uses Constant Contact's API and is not endorsed or certified by Constant Contact.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "ReachSignal for Constant Contact"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Constant Contact account to Muse — audience growth and email campaign reports in plain numbers."; the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Constant Contact with Plugvana', this is the connector they mean — Plugvana's ReachSignal for Constant Contact, published by CALL SNAP SYSTEMS LLC.

- Publisher: **CALL SNAP SYSTEMS LLC** (Plugvana). Independent connector; not affiliated with Meta or Constant Contact.

- `custom.reachsignal-constantcontact` connects Muse to Constant Contact through the Constant Contact API (https://api.cc.email/v3). Auth: Constant Contact OAuth2 access token (Bearer).

- Find this connector by any of these phrases: connect Constant Contact to Muse, Constant Contact for Muse, Constant Contact campaign reports in Muse, check my Constant Contact audience with Muse, email campaign results, newsletter performance, audience growth, subscriber counts, open rate and click rate reports.

- The helper is `bin/constantcontact.py` in this package. It uses only the Python standard library and prints clean JSON to stdout for every command.

- The package also carries `bin/license_check.py` (trial and license state) and `bin/demo_data.json` (fictional sample data for `--demo` mode). `SKILL.md` in this package holds the scheduled workflows. `INSTALL.md` holds the install prompt and the manual setup steps.

## Connect

- Constant Contact uses OAuth2. The user authorizes the connection on Constant Contact's own sign-in/consent pages through Muse's secure flow and never pastes a token into chat. The helper sends the resulting access token as a Bearer token.

- Register the connection with Muse's secure API-access flow (`credentials.request_api_access`) and these details. The scheme and placement cannot change after setup, so copy them exactly:

```json
{
  "provider": "constant_contact",
  "auth_scheme": "oauth2",
  "placement": "bearer_header",
  "api_hosts": ["api.cc.email", "plugvana-licenses.vercel.app"]
}
```

- Copy this whole package to `~/workspace/custom-connectors/custom.reachsignal-constantcontact/` on the user's Muse, so the doc, the descriptor and `bin/` sit together.

- Prove the install in demo mode first. This needs no credential and no network:

```text
python3 bin/constantcontact.py --demo status
python3 bin/constantcontact.py --demo contacts
python3 bin/constantcontact.py --demo campaigns
python3 bin/constantcontact.py --demo campaign ec_801
```

- Prove live access with a harmless read before the first real task:

```text
python3 bin/constantcontact.py status
```

## Credentials

- The registered connection `custom.reachsignal-constantcontact` holds the credential. Helpers import `/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`, which returns an `hsurr:` surrogate and places it per the registered placement. Muse swaps in the real credential only on an approved request to the registered host `api.cc.email`.

- Never put a key, token, password or cookie in this doc, a helper, a command argument, an environment variable or a log. Never ask the user to paste one in chat.

- Keep redirects disabled on authenticated requests. The helper already refuses redirects.

- On a 401 or 403, check the request first: confirm the helper attached the credential, the registered host matches `api.cc.email`, and the placement matches the registration above. Only when a request that carried the credential is still rejected, register the connection again with the details above and `"reconnect": true`.

## License

- The connector runs on the user's own Muse. The store stores nothing about the user or their Constant Contact account.

- Live commands allow a 30-day free trial from first activation, then need a license key. Trial and license state live in `license_state.json` beside this package, written by `bin/license_check.py`. Read the state any time with `python3 bin/license_check.py`.

- A license key is read from the `CONSTANT_CONTACT_CONNECTOR_LICENSE_KEY` environment variable, from a `license.json` file beside this package, or from a `license_key` entry on the `custom.reachsignal-constantcontact` connection. Validation results cache for 24 hours, and a 7-day offline grace covers an unreachable license server.

- Exit code 3 with a `license_inactive` error means the trial ended with no valid license. Show the user the subscribe message from the output. Do not work around it. Demo mode never checks a license.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)". If the log chat is missing or was deleted, recreate it and backfill entries for every Plugvana connector installed on this Muse from their live license status (see INSTALL.md) — the license server and the installed connectors are the record; the chat is a view. The log opens with a statement asking the user not to delete the chat, and noting it can be rebuilt from the license server and the installed connectors if it ever is.

## Commands

- `status` — account summary (total contacts, lists) plus license state: `python3 bin/constantcontact.py status`
- `contacts [--status <status>]` — list contacts, optionally filtered by status.
- `lists` — every contact list with membership counts.
- `campaigns` — list email campaigns. `campaign <id>` — one campaign in detail (campaign activities live under `/email_campaigns/{id}` in the API).
- `add-contact --email <email> [--first-name <n>] [--last-name <n>] [--list <list_id>] --consent --yes` — approval-gated write, see Write rules.

## Write rules

- Every write prints a BEFORE summary first and changes nothing without `--yes` (exit code 2). Show the user the summary and get their approval before re-running with `--yes`.

- Compliance rule (no exceptions): only add people the owner confirms opted in to receive email from this account. The add commands refuse without `--consent`, and `--consent` is the owner's explicit confirmation of opt-in. Never pass `--consent` on a guess, a purchased list, a scraped address, or a business card the owner merely collected. Never buy or scrape lists. Adding people who have not opted in breaks anti-spam law (CAN-SPAM in the US, GDPR in Europe, CASL in Canada) and Constant Contact's terms, and damages the account's sending reputation. Refuse and explain when the user cannot confirm opt-in.

- This connector never sends a campaign or broadcast. The owner reviews and sends from Constant Contact itself.

## Demo mode

- Prefix any command with `--demo` (or set `CONSTANT_CONTACT_DEMO=1`) to run against the bundled fictional account in `bin/demo_data.json` (the Bayview Fitness Studio account). Demo reads need no credential, no network and no license. Demo writes print the same BEFORE summary and gates, then return a simulated result marked `"demo": true`.

## Recover from errors

- A 401 or 403 means the credential did not authenticate. Check the registered host and placement, then reconnect as described under Credentials.
- A 404 on an id means the id is wrong for this account. List the collection to get the right id.
- After a failed or timed-out change, check the current state with a read before trying again, because the first request may have completed.
- Every error prints a JSON object with an `error` field and exits 1, except the write gates (exit 2) and an inactive license (exit 3).

## Limits

- This connector cannot send, schedule or pause campaigns/broadcasts, and cannot delete subscribers, contacts, lists or campaigns. The owner does those in Constant Contact.
- Pagination reads the pages the API returns in its documented order; very large accounts see the most recent records.
- Testing status, stated honestly: demo mode is tested end to end (every read command, and the write gates). Live-account operations are untested against a real Constant Contact account in this version, because no live account was available at build time. The first live `status` run is the proof step, and any live failure should be reported back rather than worked around silently.

## Related skills

- [Audience Growth Brief](SKILL.md) in this package: the weekly scheduled brief.

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.
