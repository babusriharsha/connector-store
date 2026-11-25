# SellSignal for Etsy

**Trademark notice:** The term 'Etsy' is a trademark of Etsy, Inc. This Application uses Etsy's API, but is not endorsed or certified by Etsy.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "SellSignal for Etsy"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your Etsy shop to Muse — sales, orders, listings, reviews and payments."; the full price and trial terms "Free for 1 month, then $9/month per shop — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the secure connect flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my Etsy shop with Plugvana', this is the connector they mean — Plugvana's SellSignal for Etsy, published by CALL SNAP SYSTEMS LLC.

- `custom.etsy` connects Muse to a seller's Etsy shop through the Etsy Open API v3. Use it when the user asks to connect Etsy to Muse, see Etsy orders in Muse, check my Etsy shop with Muse, get an Etsy sales snapshot, watch Etsy inventory, read Etsy reviews, or check the Etsy payment ledger.

- Every call needs two credentials, and both live in the registered connection `custom.etsy`. The OAuth 2.0 access token goes in the `Authorization: Bearer` header, and the registered Etsy app keystring goes in the `x-api-key` header. Helpers load Muse credential surrogates for both entries, so no key or token ever appears in a file, a command argument, or a log.

- The CLI is `bin/etsy.py` in this folder. It prints clean JSON to stdout. `bin/license_check.py` enforces the connector license and the 30-day free trial. `bin/demo_data.json` holds a fictional demo shop for the `--demo` mode.

```text
python3 bin/etsy.py status
python3 bin/etsy.py snapshot
python3 bin/etsy.py orders --status unshipped
python3 bin/etsy.py order <receipt_id>
python3 bin/etsy.py listings --search <keyword>
python3 bin/etsy.py listing <listing_id>
python3 bin/etsy.py inventory --threshold 3
python3 bin/etsy.py reviews
python3 bin/etsy.py ledger
python3 bin/etsy.py set-price <listing_id> --price 24.50
python3 bin/etsy.py set-quantity <listing_id> --quantity 10
```

- Add `--demo` anywhere on the command line to run the same commands against the fictional demo shop, Willow & Fern Studio. Demo mode needs no connection and no license, and demo writes are simulated. Demo mode is tested. Live mode is untested against a live shop, because no live Etsy app key exists yet. Treat every live result as a first proof and read it back before reporting a change as done.

## Publisher step, required before public launch

- The connector talks to Etsy through a registered Etsy developer app. Registering the app is free at etsy.com/developers, and only the publisher (CALL SNAP SYSTEMS LLC) can do it, because the app belongs to the publisher's Etsy developer account.

- After registering, put the app keystring in one of two places. Either fill `APP_KEYSTRING` in `bin/etsy.py`, or store the keystring in the registered connection as the `api_key` entry placed as the custom header `x-api-key`. A keystring is the app OAuth client_id. It appears in every authorization URL and is public by design, so shipping it inside the connector is safe.

- Never ship or store the app shared secret. This connector uses the public-client PKCE flow and never needs the secret.

- The license validation URL in `bin/license_check.py` points at the live Plugvana license service (plugvana-licenses.vercel.app). The license check also keeps its local trial and grace rules for when the service is unreachable.

- For testing before the publisher app exists, any Etsy app keystring works. Pass it with `--api-key <keystring>` on a command, and the helper uses it instead of the connection entry.

## Connect

- The connection was registered with `credentials.request_api_access` and these details. Reuse them to reconnect:

```json
{
  "provider": "etsy",
  "auth_scheme": "oauth2_code",
  "issuer_domain": "etsy.com",
  "authorization_url": "https://www.etsy.com/oauth/connect",
  "token_url": "https://openapi.etsy.com/v3/public/oauth/token",
  "scopes": "shops_r listings_r listings_w transactions_r",
  "api_hosts": ["openapi.etsy.com", "www.etsy.com", "etsy.com", "plugvana-licenses.vercel.app"]
}
```

- The registration carries two credential entries in the one connection. The `access_token` entry uses bearer header placement for the seller's OAuth token. The `api_key` entry uses the custom header placement `x-api-key` for the app keystring. An optional `license_key` entry holds the connector license key for paying subscribers.

- The scopes mean this. `shops_r` reads the shop record and resolves the shop. `listings_r` reads non-public listing states. `listings_w` creates and edits listings, which the inventory writes need. `transactions_r` reads receipts and sales data. Public active listings and reviews need the keystring plus any valid token.

- Etsy access tokens live one hour, and refresh tokens live 90 days. Muse's connection flow refreshes the token. If a call returns 401 after a long idle period, ask the user to reconnect rather than retrying blindly.

- The helper resolves the shop on its own. It reads the connected user from `GET /application/users/me`, then the user's shops from `GET /application/users/{user_id}/shops`, and caches the first shop id in `~/.cache/custom-etsy/shop.json`. For a seller with more than one shop, pass `--shop-id <id>` on any command, or save one shop with the configure command:

```text
python3 bin/etsy.py configure --shop-id <shop_id>
```

- Before the first change in a conversation, prove access with a harmless read:

```text
python3 bin/etsy.py status
```

## Credentials

- The registered connection holds the credential. Helpers import `/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`, which returns an `hsurr:` surrogate and places it where the provider reads the key. Muse swaps in the real credential only on an approved request to a registered host.

- Never put a key, token, password or cookie in this doc, a helper, a command argument, an environment variable or a log. Never ask the user to paste one in chat. The `--api-key` flag is the one exception, and it carries only the app keystring, which is a public client identifier, for testing.

- Keep redirects disabled on authenticated requests.

- On a 401 or 403, check the request first. Confirm that the helper attached the credential, that the host is registered and that the placement and scopes match.

- Only when a request that carried the credential is still rejected, call `credentials.request_api_access` with the details above and `"reconnect": true`.

## Read the shop

- Read the connected shop's name, title, currency, active listing count and review average:

```text
python3 bin/etsy.py status
```

- Read sales totals for today, yesterday and the last 7 days:

```text
python3 bin/etsy.py snapshot
```

- The snapshot aggregates receipts on this machine. It sums the grandtotal of every paid receipt, bucketed by local calendar date, and the output names this method. It does not net out fees or refunds. Use the ledger for Etsy's own accounting.

## Read orders

- List receipts from the last 30 days, newest first. Filter with `--status unpaid`, `paid`, `unshipped`, `shipped` or `delivered`, and widen or narrow the window with `--days`:

```text
python3 bin/etsy.py orders --status unshipped --limit 25
```

- Read one receipt in full, with its transactions, totals and the buyer's message:

```text
python3 bin/etsy.py order <receipt_id>
```

- Receipts are paged at 100 per request, up to 1000 receipts per call. The output reports `total_matched` and a `truncated` flag when the cap is hit.

## Read listings and inventory

- List active listings, optionally filtered by a keyword matched against titles and tags:

```text
python3 bin/etsy.py listings --search mug
```

- Read one listing in full, including its description and materials:

```text
python3 bin/etsy.py listing <listing_id>
```

- Read inventory for one listing, or for every active listing. Quantities live on offerings, not on the listing, so each row names the listing, product, SKU, variant and offering:

```text
python3 bin/etsy.py inventory <listing_id>
python3 bin/etsy.py inventory --threshold 3
```

- With `--threshold`, only offerings at or below that quantity come back. That is the low-stock list. The all-listings form reads at most 25 listings by default. Raise it with `--max-listings`.

## Read reviews and money

- Read the most recent reviews, with the average of the returned set and the shop's own review average beside it:

```text
python3 bin/etsy.py reviews --limit 10
```

- Read recent payment account ledger entries, with amounts, running balances and what each entry refers to:

```text
python3 bin/etsy.py ledger --days 30 --limit 20
```

- The ledger reads Etsy's payment account only. It cannot move money, and this connector offers no payout or bank features.

## Change a price or a quantity

- Two writes exist, and both are approval-gated. Run either one without `--yes` and it prints a BEFORE summary and the planned change, then stops. Show that output to the shop owner. Only when the owner approves, run the same command again with `--yes`.

```text
python3 bin/etsy.py set-price <listing_id> --price 24.50
python3 bin/etsy.py set-price <listing_id> --price 24.50 --yes
python3 bin/etsy.py set-quantity <listing_id> --quantity 10
python3 bin/etsy.py set-quantity <listing_id> --quantity 10 --yes
```

- Prices and quantities live on offerings inside a listing's inventory. A listing with one variant has one offering. When a listing has several offerings, target one with `--offering-id`, or one variant's offerings with `--product-id`. Without a target, the command refuses and lists the offering ids rather than changing all of them at once.

- Know Etsy's inventory model before trusting a write. Etsy has no patch for one price. An inventory update replaces the listing's whole inventory object, so the helper reads the current inventory, changes only the targeted offering in that copy, and sends the full object back with `PUT /application/listings/{listing_id}/inventory`. The `listings_w` scope is required.

- After any write, read the listing's inventory back and confirm the new value before telling the owner it is done. After a timeout, read first and never resend blindly, because the first request may have completed.

## License and trial

- Every live command checks the license first through `bin/license_check.py`. A 30-day free trial runs from the first live activation on that machine. Results cache for 24 hours, and a 7-day offline grace covers an unreachable validation endpoint.

- When the trial ends without a subscription, the CLI refuses politely with a JSON message and exit code 3, and prints where to subscribe. Demo mode never checks the license.

- Check license state at any time:

```text
python3 bin/license_check.py status
```

## Recover from errors

- An error prints a JSON object with `ok: false`, an `error` code and a plain `message`. Exit code 1 means the command failed. Exit code 3 means the license or trial stopped it.

- `credentials_unavailable` means the connection is missing, expired, or registered with the wrong placement or scopes. Reconnect with the details under Connect.

- `etsy_api_error` carries Etsy's own error text and HTTP status. A 403 usually means a missing scope. A 404 on inventory usually means the listing has no inventory record yet.

- `ambiguous_target` means a write matched several offerings with no target chosen. Pick one from the ids in the message.

- `shop_unresolved` means the helper could not find the shop for this account. Set it once with the configure command.

## Limits

- Live mode is untested against a live shop. Demo mode is tested end to end. No live Etsy app key exists yet, so the first live connection is the proof.

- Reads are capped for sanity. Receipts stop at 1000 per call, the all-listings inventory read stops at 25 listings by default, and reviews return at most 100 per call.

- The connector reads receipts, listings, inventory, reviews and the payment ledger, and writes only prices and quantities. It does not create or delete listings, send messages, mark orders shipped, issue refunds, or touch payouts.

- Snapshot totals are computed on this machine from receipt grandtotals. They include shipping and tax as charged, and they exclude unpaid receipts. They are a seller's quick read, not an accounting report.

- Etsy rate limits apply per app. Slow down rather than retrying in a loop when Etsy returns 429.

## Related skills

- [Etsy Shop Workflows](SKILL.md) in this package covers the Morning Shop Brief, the Low-Quantity Sweep, the New-Review Alert and the Weekly Sales Read.

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.
