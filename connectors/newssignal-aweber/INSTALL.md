# Install NewsSignal for AWeber (for Muse)

**Trademark notice:** AWeber is a trademark of AWeber Systems, Inc. This connector uses AWeber's API and is not endorsed or certified by AWeber.

By Plugvana (CALL SNAP SYSTEMS LLC). Independent connector. Not affiliated with Meta or AWeber.

This connector runs entirely on your own Muse. Your AWeber data is read by your Muse, on your machine, with your credential held in Muse's secure connection store. The store never sees your credential, your audience or your campaigns.

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **NewsSignal for AWeber** — "Connects your AWeber account to Muse — list growth and broadcast reports in plain numbers." — published by Plugvana (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the secure connect flow described in this package (request_api_access registration + the service's own sign-in page / secure capture page). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my AWeber with Plugvana', this is the connector they mean — Plugvana's NewsSignal for AWeber, published by CALL SNAP SYSTEMS LLC.

## The install prompt (fastest route)

Copy everything in the block below and paste it to your Muse.

```text
Install the AWeber connector for Muse from this package.

0. First, present this connector to me as a single, simple card in Plugvana's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "NewsSignal for AWeber", the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", the one-line description "Connects your AWeber account to Muse — list growth and broadcast reports in plain numbers.", the full price and trial terms "Free for 1 month, then $15/month per account — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the secure connect flow described below.
1. Put the package at ~/workspace/custom-connectors/custom.newssignal-aweber/ so that CONNECTOR.md, connector.yaml, SKILL.md and the bin/ folder sit together.
2. Walk me through creating the credential on AWeber's own pages (see CONNECTOR.md, Connect). Never ask me to paste a credential into chat.
3. Register the connection with credentials.request_api_access using the exact provider, auth scheme, placement and api_hosts from CONNECTOR.md / connector.yaml. Send me the secure link the tool returns so I can complete it on the hosted page.
4. Verify in demo mode first:
python3 bin/aweber.py --demo status
python3 bin/aweber.py --demo lists
python3 bin/aweber.py --demo subscribers --list awlist_01
python3 bin/aweber.py --demo broadcasts --list awlist_01
5. Then verify live: python3 ~/workspace/custom-connectors/custom.newssignal-aweber/bin/aweber.py status
   If it fails, read the Recover from errors section of CONNECTOR.md and fix the setup rather than guessing.
6. Offer to set up the Audience Growth Brief from SKILL.md as a weekly job.
```

## Manual setup (the same steps, without the prompt)

1. **Copy the package** to `~/workspace/custom-connectors/custom.newssignal-aweber/`.
2. **Create the credential** on AWeber's own pages — see the Connect section of `CONNECTOR.md`.
3. **Connect it** through Muse's secure API-access flow with the exact registration in `CONNECTOR.md` / `connector.yaml`. The credential is stored in the connection `custom.newssignal-aweber` and never written to a file.
4. **Test with demo data** (no credential, no network):

   ```text
python3 bin/aweber.py --demo status
python3 bin/aweber.py --demo lists
python3 bin/aweber.py --demo subscribers --list awlist_01
python3 bin/aweber.py --demo broadcasts --list awlist_01
   ```

5. **Test live**: `python3 bin/aweber.py status`

## Trial and license

- Live use is free for 30 days from the first live command. Demo mode is always free and never checks a license.
- After the trial, add your license key via the `AWEBER_CONNECTOR_LICENSE_KEY` environment variable, a `license.json` file beside `CONNECTOR.md` (`{"license_key": "..."}`), or the `license_key` entry on the `custom.newssignal-aweber` connection.
- Check the state any time: `python3 bin/license_check.py`. Validation caches for 24 hours and tolerates 7 days offline.

## Troubleshooting

- **401/403:** the credential did not authenticate. Confirm the registered host is `api.aweber.com` and the placement matches `connector.yaml`, then reconnect (`"reconnect": true`) and complete the hosted page again.
- **404 on an id:** the id belongs to another account or is mistyped. List the collection first and copy the id from the output.
- **License inactive (exit 3):** the trial ended. Subscribe at Plugvana, add the license key as above, and re-run.
- **Write stopped with exit 2:** that is the approval/compliance gate working as designed. Review the BEFORE summary; for add commands, confirm opt-in (`--consent`) only when the person truly opted in, then re-run with `--yes`.

Full command reference, approval rules, email-compliance rules and limits are in `CONNECTOR.md`.
