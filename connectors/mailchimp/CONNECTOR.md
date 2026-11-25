# Mailchimp

- Publisher: **CALL SNAP SYSTEMS LLC** (The Connector Store). Independent connector; not affiliated with Meta or Intuit Mailchimp.

- `custom.mailchimp` connects Muse to Mailchimp through the Mailchimp Marketing API v3.0. It reads audiences, members, campaigns and campaign reports, and it makes three approval-gated changes: creating draft campaigns, tagging members and adding opted-in members.

- Find this connector by any of these phrases: connect Mailchimp to Muse, Mailchimp for Muse, Mailchimp campaign reports in Muse, check my Mailchimp audience with Muse, email campaign results, newsletter performance, audience growth, subscriber counts, open rate and click rate reports.

- The helper is `bin/mailchimp.py` in this package. It uses only the Python standard library and prints clean JSON to stdout for every command.

- The package also carries `bin/license_check.py` (trial and license state) and `bin/demo_data.json` (fictional sample data for `--demo` mode). `SKILL.md` in this package holds the scheduled workflows. `INSTALL.md` holds the install prompt and the manual setup steps.

## Connect

- Create an API key in Mailchimp first. In Mailchimp, open the profile menu, then Account, then Extras, then API keys, and create a key. The user does this on Mailchimp's own pages. Never ask the user to paste the key into chat.

- Read the datacenter from the key. A Mailchimp API key looks like `<key>-<dc>`, for example `...-us21`. The suffix after the last hyphen is the account datacenter, and the API host is `https://<dc>.api.mailchimp.com/3.0/`. The datacenter is routing info, not a secret. It also appears in the Mailchimp web address when the user is signed in.

- Register the connection with Muse's secure API-access flow (`credentials.request_api_access`) and these details. The scheme and placement cannot change after setup, so copy them exactly:

```json
{
  "provider": "mailchimp",
  "auth_scheme": "api_key",
  "placement": "bearer_header",
  "api_hosts": ["<dc>.api.mailchimp.com"]
}
```

- Replace `<dc>` in `api_hosts` with the user's own datacenter from their key. Mailchimp accepts an API key sent as a Bearer token, which is equivalent to its Basic auth form, so `bearer_header` is the right placement.

- Save the datacenter where the helper can find it. Write `config.json` beside this doc with one line, `{"datacenter": "us21"}`, using the user's datacenter. The helper also accepts a `--dc` flag or a `MAILCHIMP_DC` environment variable, in that order.

- Copy this whole package to `~/workspace/custom-connectors/custom.mailchimp/` on the user's Muse, so the doc, the descriptor and `bin/` sit together.

- Prove the install in demo mode first. This needs no credential and no network:

```text
python3 bin/mailchimp.py --demo status
python3 bin/mailchimp.py --demo audiences
python3 bin/mailchimp.py --demo report c9f1a2b3d4
```

- Prove live access with a harmless read before the first real task:

```text
python3 bin/mailchimp.py status
```

- Expect `health_status` to read `Everything's Chimpy!` and the account block to name the user's Mailchimp account. Anything else means the connection, the host or the datacenter is wrong. Work through Recover from errors below.

## Credentials

- The registered connection `custom.mailchimp` holds the API key. Helpers import `/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`, which returns an `hsurr:` surrogate and places it in the `Authorization: Bearer` header. Muse swaps in the real key only on an approved request to the registered host.

- Never put a key, token, password or cookie in this doc, a helper, a command argument, an environment variable or a log. Never ask the user to paste one in chat.

- Keep redirects disabled on authenticated requests. The helper already refuses redirects.

- On a 401 or 403, check the request first. Confirm that the helper attached the credential, that the host registered for the connection matches the key's datacenter, and that the placement is `bearer_header`.

- Only when a request that carried the credential is still rejected, register the connection again with the details above and `"reconnect": true`. The user re-enters the key on the hosted page.

## License

- The connector runs on the user's own Muse. The store stores nothing about the user or their Mailchimp account.

- Live commands allow a 30-day free trial from first activation, then need a license key. Trial and license state live in `license_state.json` beside this package, written by `bin/license_check.py`.

- Read the license state at any time:

```text
python3 bin/license_check.py
```

- A license key is read from the `MAILCHIMP_CONNECTOR_LICENSE_KEY` environment variable, from a `license.json` file beside this package, or from a `license_key` entry on the `custom.mailchimp` connection. Validation results cache for 24 hours, and a 7-day offline grace covers an unreachable license server.

- Exit code 3 with an `license_inactive` error means the trial ended with no valid license. Show the user the subscribe message from the output. Do not work around it.

- Demo mode never checks a license.

## Read the account

- Show the account, its health and the license state:

```text
python3 bin/mailchimp.py status
```

- The output carries `health_status`, an `account` block (account id, name, industry, timezone, total subscribers), `ecommerce_stores_connected` (0 is normal for accounts with no connected store), and the `license` block.

## Read audiences

- List every audience with subscriber counts and lifetime stats:

```text
python3 bin/mailchimp.py audiences
```

- Each audience carries `member_count`, `total_contacts`, `unsubscribe_count`, `cleaned_count`, `campaign_count`, average daily subscribe and unsubscribe rates, lifetime `open_rate` and `click_rate`, and `date_created`.

- Show one audience with its recent monthly growth:

```text
python3 bin/mailchimp.py audience <audience_id> --months 6
```

- The growth rows carry `month`, `existing_at_month_start`, `imports`, `optins`, `unsubscribed`, `cleaned`, `subscribed_at_month_end` and a computed `net_change`. Mailchimp reports growth by calendar month only.

- Summarize growth across audiences, or for one audience:

```text
python3 bin/mailchimp.py growth --months 6
python3 bin/mailchimp.py growth --audience-id <audience_id> --months 12
```

- The summary adds up net change, opt-ins, unsubscribes and cleaned addresses over the months shown. Use it for the Weekly Audience Brief in `SKILL.md`.

## Read campaigns and reports

- List recent campaigns, newest sends first. Filter by status or by send window when the user asks:

```text
python3 bin/mailchimp.py campaigns
python3 bin/mailchimp.py campaigns --status sent --days 30
python3 bin/mailchimp.py campaigns --status save
```

- Campaign status values are `sent`, `save` (a draft), `sending`, `schedule` and `paused`. Drafts have no report.

- Show one campaign:

```text
python3 bin/mailchimp.py campaign <campaign_id>
```

- Show the full report for a sent campaign, in plain numbers:

```text
python3 bin/mailchimp.py report <campaign_id>
```

- The report carries `emails_sent`, `opens_total`, `unique_opens`, `open_rate`, `clicks_total`, `unique_clicks`, `click_rate`, `hard_bounces`, `soft_bounces`, `bounces_total`, `unsubscribes`, `unsub_rate`, `abuse_reports`, `forwards`, and the account's industry averages for comparison. `total_orders` and `total_revenue` appear only when the account has a connected e-commerce store feeding Mailchimp. They are `null` otherwise. Say so plainly instead of treating missing revenue as zero sales everywhere.

- Rank sent campaigns by open rate or click rate over a period:

```text
python3 bin/mailchimp.py top-campaigns --by open --days 90 --limit 10
python3 bin/mailchimp.py top-campaigns --by click --days 30
```

- Rates come from each campaign's report summary. Present the ranking with subject lines and send dates, not just ids.

## Read members

- Search members inside one audience by name or email:

```text
python3 bin/mailchimp.py members <audience_id> "maya"
```

- List members of an audience without a search, optionally by status:

```text
python3 bin/mailchimp.py members <audience_id> --count 25
python3 bin/mailchimp.py members <audience_id> --status unsubscribed
```

- Member output carries email, first and last name, `status`, tag names, `vip`, `member_rating`, opt-in time and last change time. Member status values are `subscribed`, `unsubscribed`, `cleaned`, `pending` and `archived`.

## Create a draft campaign

- This is a change. Show the user the exact subject, audience, from name and reply-to, and get their approval before running it with `--yes`. The helper prints a BEFORE summary first and changes nothing without `--yes` (exit code 2).

```text
python3 bin/mailchimp.py create-campaign --audience-id <audience_id> --subject "<subject line>" --from-name "<from name>" --reply-to <email> --title "<internal title>"
```

- Add `--yes` only after the user approves the summary.

- The command creates a draft with no content. The owner adds content, reviews and sends from Mailchimp itself.

- Never try to send a campaign through this connector. Sending is not supported, by design. There is no send command, and no workflow in `SKILL.md` may ask for one.

## Tag a member

- This is a change. Get the user's approval, then run with `--yes`. The helper prints a BEFORE summary first and changes nothing without it. Repeat `--tag` for several tags:

```text
python3 bin/mailchimp.py add-tag --audience-id <audience_id> --email <member email> --tag vip --tag workshop --yes
```

- Tags are applied as active. The helper computes the member hash from the email itself, so pass the email exactly as the member uses it.

## Add a member

- This is a change with a legal gate. Only add a person who has opted in to receive email from this audience. The helper refuses without `--consent`, and `--consent` is the user's explicit confirmation that the person opted in. Never pass `--consent` on a guess, a purchased list, a scraped address or a business card the user merely collected.

```text
python3 bin/mailchimp.py add-member --audience-id <audience_id> --email <email> --first-name <name> --last-name <name> --consent --yes
```

- The default status is `subscribed`, which adds the person immediately. Pass `--status pending` to send a double opt-in confirmation instead. Prefer `pending` whenever the opt-in evidence is thin.

- Adding people who have not opted in breaks anti-spam law (CAN-SPAM in the US, GDPR in Europe, CASL in Canada) and Mailchimp's terms, and it damages the account's sending reputation. Refuse and explain when the user cannot confirm opt-in.

## Demo mode

- Prefix any command with `--demo` (or set `MAILCHIMP_DEMO=1`) to run against the bundled fictional account in `bin/demo_data.json`: the Willow Creek Studio account, two audiences, six campaigns with reports for the four sent ones, members and six months of growth.

- Demo reads need no credential, no network and no license. Demo writes print the same BEFORE summary and gates, then return a simulated result marked `"demo": true`.

- Useful demo ids: audiences `a1b2c3d4e5` (Newsletter Subscribers) and `f6g7h8i9j0` (Customers), sent campaigns `c9f1a2b3d4`, `d5e6f7a8b9`, `e1a2b3c4d5`, `f2b3c4d5e6`, drafts `a7c8d9e0f1` and `b8d9e0f1a2`.

## Recover from errors

- A 401 or 403 means the credential did not authenticate. Check that the registered host matches the datacenter suffix of the user's current key, then reconnect as described under Credentials. A key also stops working when the Mailchimp user who created it leaves the account.

- A 404 on `report` means the campaign has no report. Drafts and scheduled campaigns have none. Check the campaign status with the `campaign` command.

- A 404 on an audience or campaign id means the id is wrong for this account. List audiences or campaigns to get the right id.

- A `No Mailchimp datacenter configured` error means the helper cannot find the datacenter. Set it with `--dc`, `MAILCHIMP_DC`, or `config.json` as described under Connect.

- Mailchimp allows 10 simultaneous connections per user and answers the eleventh with 429. The helper works one request at a time. Wait and retry after a 429 instead of looping.

- After a failed or timed-out change, check the current state with a read before trying again, because the first request may have completed. For `create-campaign`, list campaigns with `--status save` and look for the title before creating a second draft.

- Every error prints a JSON object with an `error` field and exits 1, except the write gates (exit 2) and an inactive license (exit 3).

## Limits

- This connector cannot send, schedule or pause campaigns, and cannot delete audiences, campaigns or members. The owner does those in Mailchimp.

- It does not read automations, landing pages, surveys, or per-link click detail. Reports stop at campaign level.

- E-commerce revenue appears only for accounts with a connected store. Many accounts have none, and the helper reports `null` rather than failing.

- Pagination reads up to 1,000 records per collection. Very large accounts see the most recent pages the API returns in the documented sort order.

- Testing status, stated honestly: demo mode is tested end to end (every read command, and the write gates). Live-account operations are untested against a real Mailchimp account in this version, because no live account was available at build time. The first live `status` run is the proof step, and any live failure should be reported back rather than worked around silently.

## Related skills

- [Mailchimp Briefs and Alerts](SKILL.md) in this package: the Weekly Audience Brief, the Campaign Performance Alert and the List Health Check.

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.
