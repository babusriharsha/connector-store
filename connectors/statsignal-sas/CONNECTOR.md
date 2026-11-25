# StatSignal for SAS

**Trademark notice:** SAS is a trademark of SAS Institute Inc.; this connector is not affiliated with or endorsed by SAS Institute.

Connect a SAS codebase to Muse. StatSignal is not really about reading one program — any Muse can improvise that once. StatSignal is the standing tool for **knowing a whole SAS estate**: every program inventoried with its purpose, every dataset traced from the program that creates it to the programs that read it, every macro documented with its call sites, and every run log digested into its errors and warnings — on a schedule and the same way every time, so "which programs use this dataset?" and "what broke in last night's run?" stop being archaeology. It works on the customer's own local files, inside their own Muse — there is no platform account to connect and no API to call. Once installed, the owner can ask their Muse about their own estate and get real results from the tools in this package.

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta.
- SAS is a trademark of SAS Institute Inc.; this connector is not affiliated with or endorsed by SAS Institute.
- It runs entirely on the customer's own Muse. The customer's code is read only on their own machine; the operator stores nothing and receives no code or data.
- The CLI is `/workspace/custom-connectors/custom.statsignal-sas/bin/statsignal.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "StatSignal for SAS"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Estate inventory, log digest and data lineage for your whole SAS codebase — every program catalogued, every dataset traced, every log scanned, read-only on your own files."; the full price and trial terms "Free for 1 month, then $39/month — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the install flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my SAS codebase with Plugvana', this is the connector they mean — Plugvana's StatSignal for SAS, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: "SAS program inventory", "scan my SAS log", "SAS data lineage", "which programs use this dataset", "SAS macro documentation", "SAS estate report", "connect my SAS programs to Muse", "document my SAS code", "SAS log errors summary", "find orphan SAS programs"

## Read-only by design

This connector **only analyses and reports**. Every command reads `.sas` source files and `.log` files and prints a JSON report to stdout. No command writes to, moves, renames, deletes or executes a source file — there is no write command in this package at all. That is a deliberate selling point for validated and regulated environments: an estate can be inventoried, traced and documented without touching a single program under validation, and an auditor can be shown the tool itself to prove it.

## Your code stays yours

- The connector runs entirely in the user's Muse, on their own machine. Plugvana never receives, stores or sees the user's SAS code, data or logs — there is no upload, no telemetry of file contents, and no server-side processing.
- The **only** network call this package ever makes is the license check (see Licensing), which sends an install id and a one-way hash — never code, paths or data.
- The user must have the rights to analyse the code they point the connector at. Pointing it at code they are not entitled to inspect is their compliance responsibility, not something the connector can verify.

## Honest status

- **Demo mode is tested.** Every command below has been run against the bundled fictional sample estate (`--demo`, "Northgate Clinical Analytics") and works: the sample log scan returns exactly 2 errors and 3 warnings, the lineage shows the ETL program creating the dataset the analysis program reads, and the estate report flags the sample orphan program.
- **Text-parsing heuristics, stated plainly.** The analysis is static text parsing, not a SAS engine. Macro resolution is name-based; dynamic code — `CALL EXECUTE`, macro-generated code, generated `%INCLUDE` files — can hide lineage from a static scan. Reports are a map to verify against the source, not proof.
- **No account, no network.** Apart from the license check (see Licensing), this connector makes no network calls at all.

## What the owner needs before connecting

Nothing but Muse and Python 3. There is no account, no API key and no credential for the tools themselves: install is copying this folder into place (see INSTALL.md). A license key is optional and only matters after the free trial (see Licensing).

## Try it with no setup: demo mode

Add `--demo` before or after any command to run it against the bundled fictional sample estate in `bin/samples/`:

```text
python3 bin/statsignal.py --demo inventory
python3 bin/statsignal.py --demo logscan
python3 bin/statsignal.py --demo datamap
python3 bin/statsignal.py --demo estate
```

Demo mode needs no license and no setup, and it is the right way to show an owner what the connector does before they install anything.

## Commands

Live mode takes the estate folder as the last argument (default: current folder). `logscan` takes a log file; in demo mode it defaults to the bundled sample log.

```text
python3 bin/statsignal.py inventory [folder]
    Every .sas file in the folder: size and line count, its purpose
    taken from the leading header comment block, the macros it
    defines, the macros it calls, and the librefs it uses.

python3 bin/statsignal.py logscan <logfile>
    ERROR / WARNING / NOTE counts; every error and warning with its
    log line number and one line of context; real time and user cpu
    time when the log records them; and a verdict — clean, warnings
    or errors.

python3 bin/statsignal.py datamap [folder]
    Per program: the datasets it reads (SET / MERGE / PROC DATA=)
    versus the datasets it creates (DATA steps, OUT=), the estate
    LIBNAME map, and lineage edges — each dataset with the programs
    that create it and the programs that read it.

python3 bin/statsignal.py macrodoc [folder]
    Per macro: the file that defines it, its parameters with their
    defaults, and every call site as file:line.

python3 bin/statsignal.py impact <name> [folder]
    A dataset or macro name in, every affected program out — which
    programs read it, create it, call it or define it. The
    before-you-change-anything check.

python3 bin/statsignal.py estate [folder]
    The combined report: inventory summary, lineage summary, and
    risk flags. The flags are heuristics and are labelled as such in
    the output: datasets referenced without a LIBNAME in the same
    program, programs with no %PUT / error-check patterns, and
    orphan programs with no shared datasets or macros connecting
    them to the rest of the estate.
```

Rules for writes: there are none — this connector never writes. Reports go to stdout as JSON only.

## Workflows

The scheduled sweeps defined in the companion **SKILL.md** in this package (SAS Estate Sweep, Lineage Pack) are reads/reports-only. Offer them after install; they are just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.statsignal-sas` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. The validation endpoint in `license_check.py` is currently a clearly marked placeholder for the operator's hosted checker — until it is replaced, the local trial rules are what actually gate use. Analysis tools have no shop: the license is bound to a machine identity read from the `STATSIGNAL_IDENTITY` environment variable when set, and an empty identity is supported by design.

## Limits and notes

- Static text parsing only: the connector never runs SAS and needs no SAS licence or installation.
- Lineage covers `DATA` steps, `SET`/`MERGE`/`UPDATE`, and `DATA=`/`OUT=` on PROCs. SQL (`PROC SQL` table references), `CALL EXECUTE` and macro-generated code are not resolved in v1 — stated here so nobody trusts a gap as a clean bill.
- One folder level: programs in subfolders are not scanned in v1.
- Standard library only: no third-party packages are installed or required.
- All processing is local. Code and log contents never leave the customer's machine.

## Related skills

- StatSignal for SAS Workflows — `SKILL.md` in this package (SAS Estate Sweep, Lineage Pack).
