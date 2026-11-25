# LegacySignal for COBOL

Connect LegacySignal for COBOL to Muse. LegacySignal is not really about reading one file — it is the standing tool for **understanding a whole COBOL estate**: a complete inventory of every program, copybook and JCL job, generated documentation for programs nobody documented, impact analysis that answers "what breaks if I change this?" before anyone touches production, call graphs, DB2 usage matrices, dead-code candidates, and a modernisation brief with honest complexity scores. It works on the customer's own local files, inside their own Muse — there is no platform account to connect and no API to call. Once installed, the owner can ask their Muse about code on their own machine and get real results from the tools in this package.

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta.
- It runs entirely on the customer's own Muse. The customer's code is read only on their own machine; the operator stores nothing and receives no code.
- The CLI is `/workspace/custom-connectors/custom.legacysignal-cobol/bin/legacysignal.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.
- Designed with input from a working mainframe developer — the publisher's own background is mainframe engineering.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "LegacySignal for COBOL"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Estate inventory, generated documentation and impact analysis for your COBOL codebase — read-only, on your own machine."; the full price and trial terms "Free for 1 month, then $49/month — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the install flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my COBOL codebase with Plugvana', this is the connector they mean — Plugvana's LegacySignal for COBOL, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: "COBOL estate inventory", "document my COBOL programs", "copybook impact analysis", "who calls this program", "modernize my COBOL", "JCL job flow", "DB2 table usage", "COBOL call graph", "find dead COBOL programs", "mainframe code documentation"

## Read-only by design

This connector is **analysis and reports only**. No command modifies, reformats, renames or deletes a source file — ever. That is deliberate, and it is a selling point for production code: you can point LegacySignal at a live estate folder and know the code comes out exactly as it went in. The only writes anywhere in the package are generated report files (`.md`) from `document --out <dir>` and `modernize --out <dir>`, written only into the separate output folder the user names, only when they name one. There is no default output folder, including in demo mode.

## Your code stays yours

LegacySignal runs entirely in the user's Muse, on their own machine. Plugvana never receives, stores or sees the code being analysed — not the programs, not the copybooks, not the reports. The only network call this package ever makes is the license check (see Licensing), which sends an install id and a one-way hash — **no code, no file names from your estate, no report contents**. One responsibility stays with the user: only analyse code you have the rights to analyse. Checking an employer's or a client's codebase with any tool is that user's own compliance responsibility — LegacySignal does not grant rights to anyone's code.

## Honest status

- **Demo mode is tested.** Every command below has been run against the bundled sample estate (`--demo`) — a small, fictional Meridian Mutual Insurance estate whose programs genuinely interlock (CUSTINQ calls BILLGEN, BILLGEN calls PAYCALC, both share copybooks, one JCL job runs them) — and works.
- **Live mode is your own folders.** Point any command at a folder of your own `.cob` / `.cbl` / `.cpy` / `.jcl` files; the same parsers run.
- **Parsing limits, stated plainly.** Parsing is heuristic text parsing, not a compiler: fixed-format basics are handled, free-format is partially supported, and EXEC SQL extraction is pattern-based — it can miss dynamic SQL, SQL built in working-storage, and unusual formatting. Treat every result as a documentation aid to verify, not as compiler truth.
- **No account, no network.** Apart from the license check (see Licensing), this connector makes no network calls at all.

## What the owner needs before connecting

Nothing but Muse and Python 3. There is no account, no API key and no credential for the tools themselves: install is copying this folder into place (see INSTALL.md). A license key is optional and only matters after the free trial (see Licensing).

## Try it with no setup: demo mode

Add `--demo` before or after any command to run it against the bundled sample estate in `bin/samples/`:

```text
python3 bin/legacysignal.py --demo inventory
python3 bin/legacysignal.py --demo callmap
python3 bin/legacysignal.py --demo deadcode
```

Demo mode needs no license and no setup, and it is the right way to show an owner what the connector does before they install anything.

## Commands

Every command takes an estate folder (in demo mode it defaults to the bundled samples). Source files are never modified by any command.

```text
python3 bin/legacysignal.py inventory <estate-folder>
    Every .cob/.cbl/.cpy/.jcl file: type (program/copybook/jcl),
    line count, program-id where found, one-line summary.

python3 bin/legacysignal.py document <PROGRAM> <estate-folder> [--out <dir>]
    Generated documentation for one program: program-id, purpose
    (from its header comments), files (SELECT names + FD entries),
    copybooks used, called programs, paragraph list, DB2 tables and
    verbs, and CICS commands found. With --out, also writes a .md
    report into that folder.

python3 bin/legacysignal.py callmap <estate-folder>
    The CALL graph across the estate, as a readable text tree and
    as a Mermaid graph block you can paste into documentation.

python3 bin/legacysignal.py copybooks <estate-folder>
    Per copybook: which programs use it, and its extracted fields
    (01/05/10 levels with PIC clauses).

python3 bin/legacysignal.py impact <name> <estate-folder>
    Given a program, copybook or field name: everything that
    references it — programs, copybooks, JCL jobs — plus direct
    and transitive callers for a program.

python3 bin/legacysignal.py db2 <estate-folder>
    DB2 matrix: each table -> the verbs used on it (SELECT /
    INSERT / UPDATE / DELETE) and the programs that use it,
    extracted from EXEC SQL blocks.

python3 bin/legacysignal.py jcl <estate-folder>
    Per JCL job: steps -> program (EXEC PGM=) -> datasets (DD DSN=).

python3 bin/legacysignal.py deadcode <estate-folder>
    Programs and copybooks never referenced by any CALL, COPY or
    JCL step in the estate. Candidates to investigate — a program
    run only from outside the folder can look dead, so verify
    before acting. This tool never deletes anything.

python3 bin/legacysignal.py modernize <estate-folder> [--out <dir>]
    Per program: a complexity score and risk notes, plus a
    migration brief summary. The formula is transparent and is
    printed in the output: complexity = lines + 2*paragraphs +
    5*SQL statements + 5*CICS commands + 3*CALL statements.
    Risk notes flag things like heavy SQL, CICS use, and programs
    with no error-handling keywords found. With --out, also
    writes a modernisation-brief .md report into that folder.
```

## Workflows

The scheduled sweep defined in the companion **SKILL.md** in this package (Estate Health Sweep, plus the Modernisation Brief Pack) is reads/reports-first. Offer it after install; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Price: **$49/month, or $490/year**. Subscribers add their license key to the `custom.legacysignal-cobol` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. The license is bound to a machine identity read from the `LEGACYSIGNAL_IDENTITY` environment variable when set, and an empty identity is supported by design.

When the subscriber adds their license key, also register it as a connection entry through Muse's secure API-access flow (`credentials.request_api_access`) with provider = legacysignal-cobol, api_hosts = ["plugvana-licenses.vercel.app"], auth_scheme = api_key, placement = query_param:license_key — this gives the connector a registered connection so it can appear in the user's Settings → Connectors list. The `set-key` route remains the alternative.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)".

## Limits and notes

- Heuristic text parsing only — see "Honest status" for exactly what that means. Fixed-format basics; free-format partially supported; dynamic SQL may be missed.
- One flat folder per run: the CLI reads the files directly in the estate folder you name; it does not recurse into subfolders in v1.
- Standard library only: no third-party packages are installed or required.
- All processing is local. Code contents never leave the customer's machine.

## Related skills

- LegacySignal Workflows — `SKILL.md` in this package (Estate Health Sweep, Modernisation Brief Pack).
