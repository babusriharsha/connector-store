# WorkSignal for ClickUp

**Trademark notice:** ClickUp is a trademark of Mango Technologies, Inc.

Connect a ClickUp account to Muse. Once connected, the owner can ask their Muse about their own ClickUp data in plain English and get real answers, plus a scheduled brief (see SKILL.md).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or ClickUp.
- It runs entirely on the customer's own Muse. The account's data goes from ClickUp to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.clickup/bin/clickup.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "WorkSignal for ClickUp"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your ClickUp workspace to Muse — spaces, lists and tasks at a glance."; the full price and trial terms "Free for 1 month, then $15/month per workspace — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my ClickUp with Plugvana', this is the connector they mean — Plugvana's WorkSignal for ClickUp, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"ClickUp for Muse"**, "connect ClickUp to Muse", "connect my ClickUp", "ClickUp tasks in Muse", "check my ClickUp workspace with Muse", "ClickUp overdue tasks", "ClickUp task report in Muse".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works.
- **Live mode is UNTESTED against a real ClickUp account.** No live account has been connected yet. The live code follows the official ClickUp API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one item against ClickUp itself.

## What the owner needs before connecting

1. A ClickUp account the owner controls.
2. The credential described under "Connect the account" below, created by the owner in ClickUp.

## Connect the account

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.clickup`
   - api_hosts: **api.clickup.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `api_key`
   - entries: A personal token registered as an api_key entry whose placement is a custom header named Authorization (entry name access_token). ClickUp expects the raw token in the Authorization header with NO 'Bearer' prefix, so the helper applies the surrogate as the Authorization header value exactly, and the CLI adds no prefix of its own.
   The owner pastes the credential on Muse's secure capture page, never in chat.
2. Creating the credential in ClickUp: In ClickUp, open Settings -> Apps (My Settings -> Apps on newer layouts) and generate a Personal Token. The owner must NOT paste the token into chat.
3. Verify: `python3 bin/clickup.py status`. That first real call is the proof the credential works; nothing validates it at save time.
4. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/clickup.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The values it receives are surrogates (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to api.clickup.com. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against bundled fictional data ("Delivery Space"): `python3 bin/clickup.py --demo status`. Demo mode needs no keys, no config and no license.

## Commands

Read commands (safe, no changes):

```text
python3 bin/clickup.py status
    Verify the connection; show the authorized teams/workspaces and
    cache the first team id in config.json for the other commands.

python3 bin/clickup.py spaces
    Spaces in the workspace (team discovered via /team).

python3 bin/clickup.py lists --space <space-id>
    Lists in one space (folder lists are not included in v1).

python3 bin/clickup.py tasks --list <list-id> [--status <status>]
    Tasks in one list, optionally filtered by status name.

python3 bin/clickup.py task <task-id>
    One task in full.
```

Write commands — **approval-gated, always**:

```text
python3 bin/clickup.py add-task --list <list-id> --name "..." [--description "..."] [--status <status>] [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep things updated" is not approval for a specific change.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying.
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow (Overdue Tasks Sweep) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.clickup` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: a one-way SHA-256 hash of the ClickUp workspace (team id) (from the CLI's identity argument, the CLICKUP_ACCOUNT_ID env var, or config.json) — the raw identity is never sent; "" when unknown.

## Limits and notes

- ClickUp's Authorization header carries the raw personal token with no Bearer prefix; a 401 almost always means the token was registered with bearer placement instead of the custom Authorization header — re-register, do not re-paste the token in chat.
- The team (workspace) id is discovered from GET /team and cached in config.json (see config.example.json); if the token covers several workspaces, the first is used until config.json names another.
- `lists` covers space-level lists only in this version; folder-nested lists are a known gap, stated here rather than hidden.
- The only write adds a task; nothing is deleted or closed.

## Related skills

- ClickUp Workspace Workflows — `SKILL.md` in this package (Overdue Tasks Sweep).
