# DoneSignal for TickTick

**Trademark notice:** TickTick is a trademark of Appest, Inc.

Connect a TickTick account to Muse. Once connected, the owner can ask their Muse about their own TickTick data in plain English and get real answers, plus a scheduled brief (see SKILL.md).

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta or TickTick.
- It runs entirely on the customer's own Muse. The account's data goes from TickTick to that Muse and nowhere else; the operator stores nothing.
- The CLI is `/workspace/custom-connectors/custom.ticktick/bin/ticktick.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "DoneSignal for TickTick"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your TickTick to Muse — today's tasks, overdue items and completions."; the full price and trial terms "Free for 1 month, then $5/month per account — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my TickTick with Plugvana', this is the connector they mean — Plugvana's DoneSignal for TickTick, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: **"TickTick for Muse"**, "connect TickTick to Muse", "connect my TickTick", "TickTick tasks in Muse", "check my TickTick with Muse", "TickTick today list", "TickTick overdue tasks".

## Honest status

- **Demo mode is tested.** Every read command below has been run against the bundled fictional data (`--demo`) and works.
- **Live mode is UNTESTED against a real TickTick account.** No live account has been connected yet. The live code follows the official TickTick API documentation and Muse's documented dynamic-credential pattern, but the first live connection is the real proof. Treat first-live results with care and verify one item against TickTick itself.

## What the owner needs before connecting

1. A TickTick account the owner controls.
2. The credential described under "Connect the account" below, created by the owner in TickTick.

## Connect the account

Credentials never pass through chat and never live in files. Wire the connection exactly like this:

1. Register the credential through Muse's secure API-access flow (`credentials.request_api_access`) with:
   - provider slug: `custom.ticktick`
   - api_hosts: **api.ticktick.com** Also register **plugvana-licenses.vercel.app** (the Plugvana license service) so the license_key entry can be validated on egress.
   - auth_scheme: `api_key`
   - entries: An OAuth2 access token registered as an api_key entry with bearer_header placement (entry name access_token). The owner completes TickTick's OAuth consent (or supplies a token from their TickTick developer app) and the token value is entered only on Muse's secure capture page.
   The owner pastes the credential on Muse's secure capture page, never in chat.
2. Creating the credential in TickTick: The owner creates an app at TickTick's developer portal (developer.ticktick.com), completes the OAuth2 consent for the Open API scopes (tasks:read and tasks:write), and saves the resulting access token on Muse's secure capture page. Refresh-token handling is the installing Muse's job if the token expires; the owner must NOT paste tokens into chat.
3. Verify: `python3 bin/ticktick.py status`. That first real call is the proof the credential works; nothing validates it at save time.
4. Optional, after subscribing: add a `license_key` entry on the same connection, or run `python3 bin/license_check.py set-key <KEY>` (see Licensing).

### How the credential flows

`bin/ticktick.py` imports Muse's bundled `dynamic_credentials` helper (`/opt/muse/skills/custom-connector-setup/bin`). The values it receives are surrogates (`hsurr:*`); Muse swaps in the real credential only on an approved outbound request to api.ticktick.com. The real credential never appears in the helper process, in files, in command arguments, or in logs. Redirects on authenticated requests are refused.

## Try it with no account: demo mode

Add `--demo` before or after any read command to run it against bundled fictional data ("Home Projects"): `python3 bin/ticktick.py --demo status`. Demo mode needs no keys, no config and no license.

## Commands

Read commands (safe, no changes):

```text
python3 bin/ticktick.py status
    Verify the connection; list the account's projects as proof.

python3 bin/ticktick.py projects
    All projects (lists) with task counts where the API provides them.

python3 bin/ticktick.py tasks --project <project-id>
    Open tasks in one project: title, status, priority, due date.

python3 bin/ticktick.py completed --project <project-id>
    Completed tasks in one project, from the project data payload's
    completed tasks when the API returns them, else by filtering the
    project's tasks to completed status. The output names which route
    was used, because the Open API's completed-task coverage varies.
```

Write commands — **approval-gated, always**:

```text
python3 bin/ticktick.py add-task --project <project-id> --title "..." [--content "..."] [--due 2026-12-01T09:00:00+00:00] [--priority 3] [--yes]
python3 bin/ticktick.py complete-task <task-id> --project <project-id> [--yes]
```

Rules for writes, with no exceptions:

- Without `--yes`, a write command changes **nothing**. It prints a JSON summary with `approval_required: true` and the exact proposed change, and exits with code 2.
- The calling Muse must show that summary to the owner and re-run with `--yes` only after the owner approves that specific change. A general "keep things updated" is not approval for a specific change.
- After a `--yes` write, read the record back before reporting success — a write can time out after applying.
- No command in this connector deletes anything or moves money.

## Workflows

The scheduled workflow (Today & Overdue Brief) is defined in the companion **SKILL.md** in this package. Offer it after the connection verifies; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.ticktick` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. License identity: a one-way SHA-256 hash of the TickTick account (user identifier from the connected account) (from the CLI's identity argument, the TICKTICK_ACCOUNT_ID env var, or config.json) — the raw identity is never sent; "" when unknown.

## Limits and notes

- UNVERIFIED ENDPOINT SHAPE: the Open API documentation describes completing a task at POST /open/v1/project/{projectId}/task/{taskId}/complete; this connector follows the package spec's POST /task/{id}/complete and the first live completion must be verified — if it 404s, that documented path is the fix. This is flagged, not hidden.
- TickTick access tokens expire; a 401 usually means re-consent in the developer app, not a broken connector.
- Completed-task coverage depends on what /project/{id}/data returns for the account; the command labels its source either way.

## Related skills

- TickTick Task Workflows — `SKILL.md` in this package (Today & Overdue Brief).
