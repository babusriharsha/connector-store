# BoardSignal for Trello

**Trademark notice:** Trello and Atlassian are trademarks of Atlassian Pty Ltd.

Connect a Trello account to Muse. Once connected, the owner can ask their Muse about their own Trello data in plain English and get real answers, plus a scheduled brief (see SKILL.md).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or Trello.
- It runs entirely on the customer's own Muse. The account's data goes from Trello to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.trello/bin/trello.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "BoardSignal for Trello"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Trello boards to Muse — boards, lists and cards at a glance."; the full price and trial terms "Free for 1 month, then $9/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Trello with Plugvana', this is the connector they mean — Plugvana's BoardSignal for Trello, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"Trello for Muse"**, "connect Trello to Muse", "connect my Trello", "Trello boards in Muse", "check my Trello boards with Muse", "Trello card search", "Trello board report in Muse".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works.
- **Live mode is UNTESTED against a real Trello account.** No live account has been connected yet. The live code follows the official Trello API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one item against Trello itself.

## What the owner needs before connecting

1. A Trello account the owner controls.
2. The credential described under "Connect the account" below, created by the owner in Trello.

## Connect the account

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.trello`
   - api_hosts: **api.trello.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `api_key`
   - entries: API key + user token, each registered as an api_key entry with query-parameter placement (api_key -> query param `key`; token -> query param `token`). The CLI applies both surrogates to the request URL with Muse's url_with_surrogate_query_param helper before the request is created; Muse swaps in the real values only on egress to api.trello.com.
   The owner pastes the credential on Muse's secure capture page, never in chat.
2. Creating the credential in Trello: In Trello, open https://trello.com/power-ups/admin (or trello.com/app-key) signed in as the account owner to see the personal API Key, then use Trello's token link on that page to generate a user Token with read/write scope. The owner must NOT paste either value into chat.
3. Verify: `python3 bin/trello.py status`. That first real call is the proof the credential works; nothing validates it at save time.
4. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/trello.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The values it receives are surrogates (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to api.trello.com. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against bundled fictional data ("Atlas Launch Board"): `python3 bin/trello.py --demo status`. Demo mode needs no keys, no config and no license.

## Commands

Read commands (safe, no changes):

```text
python3 bin/trello.py status
    Verify the connection; show the member profile (id, username, full name).

python3 bin/trello.py boards
    All boards the member can see, with closed boards flagged.

python3 bin/trello.py lists --board <board-id>
    Lists on one board, in board order.

python3 bin/trello.py cards --board <board-id> [--list <list-id>]
    Cards on a board (optionally only one list): name, list, labels,
    due date, members, description excerpt.

python3 bin/trello.py card <card-id>
    One card in full.
```

Write commands — **approval-gated, always**:

```text
python3 bin/trello.py add-card --list <list-id> --name "..." [--desc "..."] [--due 2026-12-01] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep things updated" is not approval for a specific change.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying.
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow (Board Morning Brief) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.trello` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: a one-way SHA-256 hash of the Trello account (member id or username) (from the CLI's identity argument, the TRELLO_ACCOUNT_ID env var, or config.json) — the raw identity is never sent; "" when unknown.

## Limits and notes

- Auth is the API key + token pair as query parameters over HTTPS, exactly as Trello documents; never log full request URLs (they carry the credential surrogates).
- `cards` reads one board at a time; there is no cross-board search command in this connector.
- No command deletes, archives or moves cards; the only write adds a new card.

## Related skills

- Trello Board Workflows — `SKILL.md` in this package (Board Morning Brief).
