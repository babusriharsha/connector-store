# TaskSignal for monday.com

**Trademark notice:** monday.com is a trademark of monday.com Ltd.

Connect a monday.com account to Muse. Once connected, the owner can ask their Muse about their own monday.com data in plain English and get real answers, plus a scheduled brief (see SKILL.md).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or monday.com.
- It runs entirely on the customer's own Muse. The account's data goes from monday.com to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.monday/bin/monday.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "TaskSignal for monday.com"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your monday.com boards to Muse — items, groups and updates at a glance."; the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my monday.com with Plugvana', this is the connector they mean — Plugvana's TaskSignal for monday.com, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"monday.com for Muse"**, "connect monday.com to Muse", "connect my monday.com", "monday boards in Muse", "check my monday.com boards with Muse", "monday.com items report", "monday updates digest".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works.
- **Live mode is UNTESTED against a real monday.com account.** No live account has been connected yet. The live code follows the official monday.com API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one item against monday.com itself.

## What the owner needs before connecting

1. A monday.com account the owner controls.
2. The credential described under "Connect the account" below, created by the owner in monday.com.

## Connect the account

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.monday`
   - api_hosts: **api.monday.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `api_key`
   - entries: A personal API token registered as an api_key entry with bearer_header placement (entry name access_token). Every request is a POST to https://api.monday.com/v2 with the header API-Version: 2023-10, exactly as monday.com documents.
   The owner pastes the credential on Muse's secure capture page, never in chat.
2. Creating the credential in monday.com: In monday.com, click the avatar -> Developers / API (or Admin -> Connections -> API tokens, depending on plan) and generate a personal API token with read/write scope. The owner must NOT paste the token into chat.
3. Verify: `python3 bin/monday.py status`. That first real call is the proof the credential works; nothing validates it at save time.
4. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/monday.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The values it receives are surrogates (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to api.monday.com. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against bundled fictional data ("Product Roadmap Board"): `python3 bin/monday.py --demo status`. Demo mode needs no keys, no config and no license.

## Commands

Read commands (safe, no changes):

```text
python3 bin/monday.py status
    Verify the connection; show the authenticated user (me query).

python3 bin/monday.py boards
    All boards visible to the token, with item counts.

python3 bin/monday.py items --board <board-id> [--limit 25]
    Items on one board (first items page): id, name, group, updated_at.

python3 bin/monday.py groups --board <board-id>
    Groups on one board: id and title.

python3 bin/monday.py updates [--limit 10]
    The most recent updates across the account's boards.
```

Write commands — **approval-gated, always**:

```text
python3 bin/monday.py add-item --board <board-id> --name "..." [--group <group-id>] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep things updated" is not approval for a specific change.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying.
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow (Board Changes Digest) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.monday` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: a one-way SHA-256 hash of the monday.com account (user id or email) (from the CLI's identity argument, the MONDAY_ACCOUNT_ID env var, or config.json) — the raw identity is never sent; "" when unknown.

## Limits and notes

- The monday.com API is GraphQL only; every command is a POST to /v2 with API-Version: 2023-10. GraphQL errors arrive in an `errors` array with HTTP 200 in some cases — the CLI surfaces them as errors either way.
- `items` reads the first items_page of a board (cursor pagination is not followed); very large boards are sampled, and the output says how many were returned.
- The only write creates a new item; no command edits, moves or deletes items.

## Related skills

- monday.com Board Workflows — `SKILL.md` in this package (Board Changes Digest).
