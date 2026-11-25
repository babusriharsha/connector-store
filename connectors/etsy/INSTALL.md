# Install the Etsy Connector for Muse

**Trademark notice:** The term 'Etsy' is a trademark of Etsy, Inc. This Application uses Etsy's API, but is not endorsed or certified by Etsy.

This package connects a seller's Etsy shop to their Muse, so they can ask Muse about orders, sales, listings, inventory, reviews and their Etsy payment ledger in plain words. Published by CALL SNAP SYSTEMS LLC. Independent connector; not affiliated with Meta or Etsy.

Everything runs on the user's own Muse. The connector stores no shop data anywhere. Credentials live only in Muse's secure connection flow, never in files.

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in The Connector Store's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by The Connector Store (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **Etsy Connector** — "Connect your Etsy shop to Muse" — published by The Connector Store (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $9/month per shop — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the secure connect flow described in this package (request_api_access registration + the service's own sign-in page). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my Etsy shop with The Connector Store', this is the connector they mean — The Connector Store's Etsy Connector, published by CALL SNAP SYSTEMS LLC.

## Copy-paste install prompt

Paste this whole block to your Muse and it will install the connector for you:

```text
Install the Etsy connector for Muse from this package.

0. First, present this connector to me as a single, simple card in The Connector Store's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "Etsy Connector", the publisher line "by The Connector Store (CALL SNAP SYSTEMS LLC)", the one-line description "Connect your Etsy shop to Muse", the full price and trial terms "Free for 1 month, then $9/month per shop — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the secure connect flow described below.
1. Copy this package folder to ~/workspace/custom-connectors/custom.etsy/ so that
   ~/workspace/custom-connectors/custom.etsy/CONNECTOR.md and
   ~/workspace/custom-connectors/custom.etsy/bin/etsy.py exist.
2. Read CONNECTOR.md in that folder and follow its Connect section exactly.
3. Register the connection with credentials.request_api_access using the JSON in
   the Connect section: provider "etsy", auth_scheme "oauth2_code",
   authorization_url "https://www.etsy.com/oauth/connect",
   token_url "https://openapi.etsy.com/v3/public/oauth/token",
   issuer_domain "etsy.com", scopes "shops_r listings_r listings_w transactions_r",
   api_hosts ["openapi.etsy.com", "www.etsy.com", "etsy.com"].
   The connection holds two entries: access_token with bearer header placement,
   and api_key with the custom header placement x-api-key carrying the Etsy app
   keystring supplied with this package.
4. Send me the connect link and wait while I sign in with Etsy and approve.
5. Prove it works: run the demo first, then the live status check:
   python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py status --demo
   python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py status
   Show me my shop name and today's sales snapshot when it works.
```

## Manual install steps (what the prompt does)

1. **Place the package.** Copy the `etsy` folder to `~/workspace/custom-connectors/custom.etsy/`. The folder name matters: the descriptor id, the folder and the registered connection must all read `custom.etsy`.

2. **Check the helpers run.** No dependencies beyond Python 3 and its standard library.

   ```text
   python3 -m py_compile ~/workspace/custom-connectors/custom.etsy/bin/etsy.py ~/workspace/custom-connectors/custom.etsy/bin/license_check.py
   python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py status --demo
   ```

   The demo command prints the fictional Willow & Fern Studio shop. If that works, the package is sound and only the connection remains.

3. **Register the connection.** Call `credentials.request_api_access` with the JSON from the Connect section of CONNECTOR.md. Two credential entries live in the one connection:
   - `access_token` — the seller's OAuth 2.0 token, bearer header placement. The seller creates this by signing in on the hosted connect page; never ask them for it in chat.
   - `api_key` — the Etsy app keystring, custom header placement `x-api-key`. The keystring ships with the package (it is the app's public OAuth client ID) and is already filled in `APP_KEYSTRING` in `bin/etsy.py`, or supplied as this entry. Either source works; the helper prefers the connection entry when `APP_KEYSTRING` is empty.

4. **The seller signs in.** Share the connect link from the registration call. The seller signs in with Etsy and approves the scopes `shops_r listings_r listings_w transactions_r`. Etsy access tokens live one hour and refresh tokens 90 days; the connection flow handles refresh.

5. **First live proof.** Run:

   ```text
   python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py status
   python3 ~/workspace/custom-connectors/custom.etsy/bin/etsy.py snapshot
   ```

   The helper resolves the shop itself from the connected user. For a seller with several shops, pass `--shop-id <id>` or save one with `etsy.py configure --shop-id <id>`.

6. **License.** The first live command starts a 30-day free trial automatically; there is nothing to enter. When the seller subscribes, their license key is added to the connection as a third entry named `license_key`, and `bin/license_check.py` validates it from then on. Check state any time with `python3 bin/license_check.py status`.

## Testing with your own Etsy app (bring your own keystring)

Developers who registered their own app at etsy.com/developers can test before the publisher keystring is filled in:

```text
python3 bin/etsy.py status --api-key <your-keystring>
```

The OAuth token still comes from the registered connection. Only the keystring is overridden, and only for that command.

## Honest status

- Demo mode is fully tested: every read command, the approval gate on both writes, simulated writes, and the license trial and expiry behaviour.
- Live mode is **untested against a live shop**, because the publisher's Etsy developer app registration is the one step that must happen before a live keystring exists. The endpoints, scopes, headers and payload shapes follow Etsy's official Open API v3 documentation.
- Publisher pre-launch checklist: register the Etsy developer app at etsy.com/developers (free), fill `APP_KEYSTRING` in `bin/etsy.py`, replace the placeholder validation URL in `bin/license_check.py`, then run one live `status` and `snapshot` against a real shop and read the results before announcing anything.
