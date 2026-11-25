# Install: WooCommerce Connector for Muse

An independent connector by CALL SNAP SYSTEMS LLC. Not affiliated with Meta, Automattic or WooCommerce.

There are two ways to install:

- **Part 1 — the copy-paste install prompt.** A store owner pastes one block into their own Muse and their Muse performs the whole setup, asking them only for the two things only they can do (generating the store's API keys, and pasting them into Muse's secure capture page).
- **Part 2 — the manual steps** the install prompt follows, written out so any Muse (or human) can do or audit the setup without the prompt.

Either way: credentials are entered only on Muse's secure capture page, never in chat, and never written to a file.

---

## Part 1 — Install prompt (copy everything in the block)

```text
Install the WooCommerce connector for Muse from this package, then connect my store.

Do these steps in order and confirm each one before moving on:

1. Copy this whole connector folder to ~/workspace/custom-connectors/custom.woocommerce/ on my machine, keeping connector.yaml, CONNECTOR.md, SKILL.md and the bin/ folder together. Read CONNECTOR.md fully before running anything.

2. Ask me for my store's base URL (for example https://shop.example.com). It must be HTTPS. Then copy store_config.example.json from the connector root to store_config.json and set store_url to my store's URL. This file holds no secrets.

3. Tell me to create the store's API keys myself: in WP Admin go to WooCommerce → Settings → Advanced → REST API → Add key, pick an admin user, set permissions to Read/Write, and choose Generate API key. Tell me the store will show a Consumer Key and a Consumer Secret exactly once, and that I must NOT paste them into this chat.

4. Register the credential using your secure API-access flow (credentials.request_api_access) with: provider "custom.woocommerce", api_hosts set to my store's hostname only, auth_scheme "api_key", and two entries — "consumer_key" with query-parameter placement named consumer_key, and "consumer_secret" with query-parameter placement named consumer_secret. Send me the secure capture link and wait until I confirm I have saved both keys there.

5. Verify the connection by running: python3 ~/workspace/custom-connectors/custom.woocommerce/bin/woo.py status
   Show me the result. It should say "connected": true with my store's currency and order counts. If it fails, follow the troubleshooting section of CONNECTOR.md — check the store URL's www/non-www form first, then the registered host, then ask me to re-check the keys. Do not ask me to paste keys in chat at any point.

6. Once status succeeds, show me what the connector can do by running the snapshot command (python3 ~/workspace/custom-connectors/custom.woocommerce/bin/woo.py snapshot) and summarising today vs yesterday vs the last 7 days in plain English.

7. Offer me the scheduled workflows from SKILL.md (Morning Store Brief, Low-Stock Sweep, Refund Spike Alert, Weekly Win-Back List) and set up the ones I pick, at the times I choose.

Notes for you, Muse: my 30-day free trial starts at the first live command. Live commands after the trial need a subscription and a license key (CONNECTOR.md explains). Demo mode (add --demo to any command) works without my store if I want to see it first.
```

---

## Part 2 — Manual install steps (what the prompt does)

1. **Place the package.** Copy the folder to `~/workspace/custom-connectors/custom.woocommerce/`. The CLI is `bin/woo.py`; it needs only Python 3's standard library.
2. **Configure the store URL.** Copy `store_config.example.json` → `store_config.json` in the connector root; set `store_url` to the store's HTTPS base URL. (Or set the `WC_STORE_URL` environment variable / pass `--store-url`.)
3. **Owner generates keys.** WP Admin → WooCommerce → Settings → Advanced → REST API → Add key → admin user → Read/Write → Generate. The Consumer Key and Consumer Secret are shown once.
4. **Register the connection.** `credentials.request_api_access` with provider `custom.woocommerce`, api_hosts = [the store's hostname], auth_scheme `api_key`, entries `consumer_key` and `consumer_secret`, each placed as a query parameter under its own name. The owner enters both values on the secure capture page. **This registration is the one wiring step the installing Muse must perform** — the helper code assumes a connection with exactly this name, these entry names, this placement, and the store host registered; a mismatch surfaces as a refused or unauthenticated first call.
5. **Verify.** `python3 bin/woo.py status` — the first real call is the proof; nothing checks the keys when they are saved.
6. **Smoke-test without a store (any time).** `python3 bin/woo.py --demo snapshot` runs against the bundled fictional store and needs no setup at all.
7. **Optional subscription.** After the 30-day trial, the owner subscribes at the Connector Store and adds the license key as a `license_key` entry on the same connection, or runs `python3 bin/license_check.py set-key <KEY>`.

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "redirect refused" | Store URL www/non-www doesn't match the store's canonical host | Correct `store_url` in `store_config.json` |
| HTTP 401 from the store | Keys wrong, revoked, or Read-only keys used for a write | Regenerate the key pair in WP Admin; re-save via the secure flow |
| Credential/host refusal from Muse | Store hostname not in the connection's api_hosts, or entry names/placement differ | Re-register the connection exactly as in step 4 |
| "trial_expired" | 30-day trial ended without a subscription | Subscribe, then add the license key |
