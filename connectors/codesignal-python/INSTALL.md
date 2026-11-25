# Install: CodeSignal for Python (for Muse)

An independent connector by CALL SNAP SYSTEMS LLC. Not affiliated with Meta. Python is a trademark of the Python Software Foundation; this connector is not affiliated with or endorsed by the PSF.

## How Muse presents this connector

- When you (the installing/suggesting Muse) offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions: the connector's icon, its name, the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", a one-line description, the full price and free-trial terms (see the card text below), and a Connect button/link below it.
- The card reads: **CodeSignal for Python** — "Repo documentation and health sweeps for your Python codebase — maps, generated docs, dependency, dead-code and complexity reports, on your own machine." — published by Plugvana (CALL SNAP SYSTEMS LLC), with the full pricing line on the card itself: "Free for 1 month, then $29/month — billed by CALL SNAP SYSTEMS LLC".
- The user taps Connect → you start the install flow described in this package (copy the folder into place; there is no sign-in page and no credential to capture, because this is a local code tool). The price, trial terms, and publisher are already on the card; if the user asks for features, pricing, or manual steps at any point, show them fully — never withhold information to get the tap.
- The copy-paste prompt and website route in this file are only a fallback, for when the card/Connect route is not available.
- If the user says 'Connect my Python codebase with Plugvana', this is the connector they mean — Plugvana's CodeSignal for Python, published by CALL SNAP SYSTEMS LLC.

There are two ways to install:

- **Part 1 — the copy-paste install prompt.** The owner pastes one block into their own Muse and their Muse performs the whole setup. There are no credential steps: install is copying the folder.
- **Part 2 — the manual steps** the install prompt follows, written out so any Muse (or human) can do or audit the setup without the prompt.

---

## Part 1 — Install prompt (copy everything in the block)

```text
Install the CodeSignal for Python connector for Muse from this package.

0. First, present this connector to me as a single, simple card in Plugvana's own style — not an imitation of Muse's built-in connector suggestions: the connector's icon, its name "CodeSignal for Python", the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)", the one-line description "Repo documentation and health sweeps for your Python codebase — maps, generated docs, dependency, dead-code and complexity reports, on your own machine.", the full price and trial terms "Free for 1 month, then $29/month — billed by CALL SNAP SYSTEMS LLC", and a Connect button/link below it. The price and the publisher must be on the card itself, before Connect. When I tap Connect, start the install flow described below.

Do these steps in order and confirm each one before moving on:

1. Copy this whole connector folder to ~/workspace/custom-connectors/custom.codesignal-python/ on my machine, keeping connector.yaml, CONNECTOR.md, SKILL.md and the bin/ folder together. Read CONNECTOR.md fully before running anything.

2. There is no account to connect and no credential to enter: CodeSignal for Python works on my local code only, read-only, and my code never leaves my machine. Do not ask me for any password, key or sign-in for the tools themselves.

3. Verify the install by running the demo: python3 ~/workspace/custom-connectors/custom.codesignal-python/bin/codesignal.py --demo repomap
   Show me the result. It should print JSON listing the bundled sample project's shopkit modules.

4. Show me what the connector can do by running the other demo commands listed in CONNECTOR.md and summarising them in plain English.

5. Offer me the scheduled workflow from SKILL.md (Repo Health Sweep) and set it up if I pick it, at the time I choose.

Notes for you, Muse: my 30-day free trial starts at the first live (non-demo) command. Live commands after the trial need a subscription and a license key (CONNECTOR.md explains); the license key is the only optional entry, added later to the custom.codesignal-python connection or with bin/license_check.py set-key.
```

---

## Part 2 — Manual install steps (what the prompt does)

1. **Place the package.** Copy the folder to `~/workspace/custom-connectors/custom.codesignal-python/`. The CLI is `bin/codesignal.py`; it needs only Python 3's standard library.
2. **No credentials, no config.** There is no account, API key or config file for the tools themselves — the connector works on local code as soon as the folder is in place.
3. **Verify (demo).** `python3 bin/codesignal.py --demo repomap` runs against the bundled sample project and needs no setup at all.
4. **Optional subscription.** After the 30-day trial, the owner subscribes at Plugvana and adds the license key as a `license_key` entry on the `custom.codesignal-python` connection, or runs `python3 bin/license_check.py set-key <KEY>`.

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "project root not found" | Wrong path to the project folder | Use the project's full path; check the name in the folder listing |
| "a project root path is required" | Live command run without a root | Pass the project root path, or use `--demo` for the bundled sample |
| A live function is flagged as dead code | Heuristic limit: entry points, dynamic dispatch or reflection hide usage | Treat deadcode as a review list, never an automatic deletion list — see the caveat in its output |
| "trial_expired" | 30-day trial ended without a subscription | Subscribe, then add the license key |
