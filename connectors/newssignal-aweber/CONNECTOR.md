# NewsSignal for AWeber

**Trademark notice:** AWeber is a trademark of AWeber Systems, Inc. This connector uses AWeber's API and is not endorsed or certified by AWeber.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "NewsSignal for AWeber"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your AWeber account to Muse — list growth and broadcast reports in plain numbers."; the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my AWeber with Plugvana', this is the connector they mean — Plugvana's NewsSignal for AWeber, published by CALL SNAP SYSTEMS LLC.

- Publisher: **CALL SNAP SYSTEMS LLC** (Plugvana). Independent connector; not affiliated with Meta or AWeber.

- `custom.newssignal-aweber` connects Muse to AWeber through the AWeber API (https://api.aweber.com/1.0). Auth: AWeber OAuth2 access token (Bearer).

- Find this connector by any of these phrases: connect AWeber to Muse, AWeber for Muse, AWeber campaign reports in Muse, check my AWeber audience with Muse, email campaign results, newsletter performance, audience growth, subscriber counts, open rate and click rate reports.

- The helper is `bin/aweber.py` in this package. It uses only the Python standard library and prints clean JSON to stdout for every command.

- The package also carries `bin/license_check.py` (trial and license state) and `bin/demo_data.json` (fictional sample data for `--demo` mode). `SKILL.md` in this package holds the scheduled workflows. `INSTALL.md` holds the install prompt and the manual setup steps.

## Connect

- AWeber uses OAuth2. The user authorizes the connection on AWeber's own sign-in/consent pages through Muse's secure flow and never pastes a token into chat. The helper sends the resulting access token as a Bearer token. After connecting, the helper discovers the account id via `/accounts` and stores it in `config.json` beside this doc (`{"account_id": "..."}`); `config.example.json` shows the shape.

- Register the connection with Muse's secure API-access flow (`credentials.request_api_access`) and these details. The scheme and placement cannot change after setup, so copy them exactly:

```json
{
  "provider": "aweber",
  "auth_scheme": "oauth2",
  "placement": "bearer_header",
  "api_hosts": ["api.aweber.com", "plugvana-licenses.vercel.app"]
}
```

- Copy this whole package to `~/workspace/custom-connectors/custom.newssignal-aweber/` on the user's Muse, so the doc, the descriptor and `bin/` sit together.

- Prove the install in demo mode first. This needs no credential and no network:

```text
python3 bin/aweber.py --demo status
python3 bin/aweber.py --demo lists
python3 bin/aweber.py --demo subscribers --list awlist_01
python3 bin/aweber.py --demo broadcasts --list awlist_01
```

- Prove live access with a harmless read before the first real task:

```text
python3 bin/aweber.py status
```

## Credentials

- The registered connection `custom.newssignal-aweber` holds the credential. Helpers import `/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`, which returns an `hsurr:` surrogate and places it per the registered placement. Muse swaps in the real credential only on an approved request to the registered host `api.aweber.com`.

- Never put a key, token, password or cookie in this doc, a helper, a command argument, an environment variable or a log. Never ask the user to paste one in chat.

- Keep redirects disabled on authenticated requests. The helper already refuses redirects.

- On a 401 or 403, check the request first: confirm the helper attached the credential, the registered host matches `api.aweber.com`, and the placement matches the registration above. Only when a request that carried the credential is still rejected, register the connection again with the details above and `"reconnect": true`.

## License

- The connector runs on the user's own Muse. The store stores nothing about the user or their AWeber account.

- Live commands allow a 30-day free trial from first activation, then need a license key. Trial and license state live in `license_state.json` beside this package, written by `bin/license_check.py`. Read the state any time with `python3 bin/license_check.py`.

- A license key is read from the `AWEBER_CONNECTOR_LICENSE_KEY` environment variable, from a `license.json` file beside this package, or from a `license_key` entry on the `custom.newssignal-aweber` connection. Validation results cache for 24 hours, and a 7-day offline grace covers an unreachable license server.

- Exit code 3 with a `license_inactive` error means the trial ended with no valid license. Show the user the subscribe message from the output. Do not work around it. Demo mode never checks a license.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)".

## Commands

- `status` — account info plus license state: `python3 bin/aweber.py status`. The account id is discovered via `/accounts` on first use and stored in `config.json` (see `config.example.json`).
- `lists` — the account's lists. `subscribers --list <id>`, `broadcasts --list <id>`, `campaigns --list <id>` — per-list reads.
- `add-subscriber --list <id> --email <email> [--name <name>] --consent --yes` — approval-gated write, see Write rules.

## Write rules

- Every write prints a BEFORE summary first and changes nothing without `--yes` (exit code 2). Show the user the summary and get their approval before re-running with `--yes`.

- Compliance rule (no exceptions): only add people the owner confirms opted in to receive email from this account. The add commands refuse without `--consent`, and `--consent` is the owner's explicit confirmation of opt-in. Never pass `--consent` on a guess, a purchased list, a scraped address, or a business card the owner merely collected. Never buy or scrape lists. Adding people who have not opted in breaks anti-spam law (CAN-SPAM in the US, GDPR in Europe, CASL in Canada) and AWeber's terms, and damages the account's sending reputation. Refuse and explain when the user cannot confirm opt-in.

- This connector never sends a campaign or broadcast. The owner reviews and sends from AWeber itself.

## Demo mode

- Prefix any command with `--demo` (or set `AWEBER_DEMO=1`) to run against the bundled fictional account in `bin/demo_data.json` (the North Fork Gardening Co. account). Demo reads need no credential, no network and no license. Demo writes print the same BEFORE summary and gates, then return a simulated result marked `"demo": true`.

## Recover from errors

- A 401 or 403 means the credential did not authenticate. Check the registered host and placement, then reconnect as described under Credentials.
- A 404 on an id means the id is wrong for this account. List the collection to get the right id.
- After a failed or timed-out change, check the current state with a read before trying again, because the first request may have completed.
- Every error prints a JSON object with an `error` field and exits 1, except the write gates (exit 2) and an inactive license (exit 3).

## Limits

- This connector cannot send, schedule or pause campaigns/broadcasts, and cannot delete subscribers, contacts, lists or campaigns. The owner does those in AWeber.
- Pagination reads the pages the API returns in its documented order; very large accounts see the most recent records.
- Testing status, stated honestly: demo mode is tested end to end (every read command, and the write gates). Live-account operations are untested against a real AWeber account in this version, because no live account was available at build time. The first live `status` run is the proof step, and any live failure should be reported back rather than worked around silently.

## Related skills

- [Audience Growth Brief](SKILL.md) in this package: the weekly scheduled brief.

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.
