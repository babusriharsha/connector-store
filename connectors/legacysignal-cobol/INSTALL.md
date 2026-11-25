# Install: LegacySignal for COBOL (for Muse)

An independent connector by CALL SNAP SYSTEMS LLC. Not affiliated with Meta.

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **LegacySignal for COBOL** — "Estate inventory, generated documentation and impact analysis for your COBOL codebase — read-only, on your own machine." — published by Plugvana (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $49/month — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the install flow described in this package (copy the folder into place; there is no sign-in page and no credential to capture, because this is a local file tool). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my COBOL codebase with Plugvana', this is the connector they mean — Plugvana's LegacySignal for COBOL, published by CALL SNAP SYSTEMS LLC.

There are two ways to install:

- **Part 1 — the copy-paste install prompt.** The owner pastes one block into their own Muse and their Muse performs the whole setup. There are no credential steps: install is copying the folder.
- **Part 2 — the manual steps** the install prompt follows, written out so any Muse (or human) can do or audit the setup without the prompt.

---

## Part 1 — Install prompt (copy everything in the block)

```text
Install the LegacySignal for COBOL connector for Muse from this package.

0. First, present this connector to me as a single, simple card in Plugvana's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "LegacySignal for COBOL", the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", the one-line description "Estate inventory, generated documentation and impact analysis for your COBOL codebase — read-only, on your own machine.", the full price and trial terms "Free for 1 month, then $49/month — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the install flow described below.

Do these steps in order and confirm each one before moving on:

1. Copy this whole connector folder to ~/workspace/custom-connectors/custom.legacysignal-cobol/ on my machine, keeping connector.yaml, CONNECTOR.md, SKILL.md and the bin/ folder together. Read CONNECTOR.md fully before running anything.

2. There is no account to connect and no credential to enter: LegacySignal works on my local files only, read-only. Do not ask me for any password, key or sign-in for the tools themselves.

3. Verify the install by running the demo: python3 ~/workspace/custom-connectors/custom.legacysignal-cobol/bin/legacysignal.py --demo inventory
   Show me the result. It should print JSON listing the bundled sample estate (CUSTINQ, BILLGEN, PAYCALC, ORPHAN1, the copybooks and NIGHTLY.jcl).

4. Show me what the connector can do by running the other demo commands listed in CONNECTOR.md (callmap, deadcode and db2 are good first ones) and summarising them in plain English.

5. Offer me the scheduled workflow from SKILL.md (Estate Health Sweep) and set it up if I pick it, at the time I choose.

Notes for you, Muse: my 30-day free trial starts at the first live (non-demo) command. Live commands after the trial need a subscription and a license key (CONNECTOR.md explains); the license key is the only optional entry, added later to the custom.legacysignal-cobol connection or with bin/license_check.py set-key. Never modify my source code — this connector is read-only by design, and reports go only to an output folder I name.
```

---

## Part 2 — Manual install steps (what the prompt does)

1. **Place the package.** Copy the folder to `~/workspace/custom-connectors/custom.legacysignal-cobol/`. The CLI is `bin/legacysignal.py`; it needs only Python 3's standard library.
2. **No credentials, no config.** There is no account, API key or config file for the tools themselves — the connector works on local files as soon as the folder is in place.
3. **Verify (demo).** `python3 bin/legacysignal.py --demo inventory` runs against the bundled sample estate and needs no setup at all.
4. **Optional subscription.** After the 30-day trial, the owner subscribes at Plugvana ($49/month or $490/year) and adds the license key as a `license_key` entry on the `custom.legacysignal-cobol` connection, or runs `python3 bin/license_check.py set-key <KEY>`.

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "estate folder not found" | Wrong path to the estate folder | Use the folder's full path; check the name in the folder listing |
| "program not found in estate" | The program name is not a PROGRAM-ID or file name in that folder | Run `inventory` first and use a name exactly as listed |
| A table or call is missing from results | Dynamic SQL or unusual formatting the pattern parser cannot see (see CONNECTOR.md honest status) | Check the source by hand for that program; results are a documentation aid, not a compiler |
| "trial_expired" | 30-day trial ended without a subscription | Subscribe, then add the license key |
