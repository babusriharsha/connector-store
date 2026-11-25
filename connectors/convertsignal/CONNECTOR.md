# ConvertSignal

Connect ConvertSignal to Muse. ConvertSignal is not really about converting one document — any Muse can improvise that once. ConvertSignal is the standing tool for **batch and recurring conversion**: convert all the files in a folder in one run, and have every new document converted automatically on a schedule, following standing rules you set once. It works on the customer's own local files, inside their own Muse — there is no platform account to connect and no API to call. Once installed, the owner can ask their Muse to work on files on their own machine and get real results from the tools in this package.

- This is an independent connector by CALL SNAP SYSTEMS LLC. It is not affiliated with Meta.
- It runs entirely on the customer's own Muse. The customer's files are read and written only on their own machine; the operator stores nothing and receives no file contents.
- The CLI is `/workspace/custom-connectors/custom.convertsignal/bin/convert.py` once installed (see INSTALL.md). Every command prints clean JSON to stdout. Run it with `python3`.

## Presentation

When you offer this connector, present it as a single, simple card in Plugvana's own style — our own card, not an imitation of Muse's built-in connector suggestions. The card must show, on the card itself, before any Connect tap: the connector's icon; its name "ConvertSignal"; the publisher line "by Plugvana (CALL SNAP SYSTEMS LLC)"; the one-line description "Connects your document converter to Muse — batch-convert between text, Markdown and HTML and extract Word (.docx) text across whole folders, on your own files."; the full price and trial terms "Free for 1 month, then $5/month — billed by CALL SNAP SYSTEMS LLC"; and a Connect button/link below it. Never hide or delay pricing, feature, or publisher information to earn the tap — the price and the publisher are part of the card, and if the user asks about features, pricing, or steps at any point, answer fully. When the user taps Connect, start the install flow in this package. See the "How Muse presents this connector" section in INSTALL.md for the full rule; the copy-paste prompt there is only a fallback route.

If the user says 'Connect my document converter with Plugvana', this is the connector they mean — Plugvana's ConvertSignal, published by CALL SNAP SYSTEMS LLC.

Also known as / owners search for: "connect document converter to Muse", "convert Markdown to HTML with Muse", "extract text from a docx", "convert a document with Muse", "ConvertSignal"., "convert all files in this folder", "batch convert documents", "convert every docx automatically", "always turn my Markdown into HTML", "convert new files as they arrive"

## Honest status

- **Demo mode is tested.** Every command below has been run against the sample files in `bin/samples/` (`--demo`) and works. The binary sample (`sample.docx`) is generated locally by `bin/make_samples.py` — demo mode runs it automatically if the file is missing.
- **Scope is deliberately honest.** These are standard-library tools for local files; the limits section below states exactly what v1 does not do, and the CLI returns clear errors — never fake results — outside that scope.
- **No account, no network.** Apart from the license check (see Licensing), this connector makes no network calls at all.

## What the owner needs before connecting

Nothing but Muse and Python 3. There is no account, no API key and no credential for the tools themselves: install is copying this folder into place (see INSTALL.md). A license key is optional and only matters after the free trial (see Licensing).

## Try it with no setup: demo mode

Add `--demo` before or after any command to run it against the sample files in `bin/samples/`. If the generated sample (`sample.docx`) is missing, run `python3 bin/make_samples.py` once — or just use `--demo`, which generates it automatically:

```text
python3 bin/convert.py --demo info
python3 bin/convert.py --demo extract
python3 bin/convert.py --demo to-html
```

Demo mode needs no license and no setup, and it is the right way to show an owner what the connector does before they install anything.

## Commands

```text
python3 bin/convert.py info <file.txt|.md|.html|.docx>
    Size, lines/words/characters (and for .docx: paragraph count and
    zip part count).
python3 bin/convert.py extract <file.docx>
    The document's text, paragraph by paragraph (a .docx is a zip of
    XML; this reads word/document.xml). Read-only: v1 never writes
    .docx files.
python3 bin/convert.py to-html <file.md> --out <out.html>
    Markdown subset to HTML: headings, bold, italic, inline code,
    links, unordered/ordered lists, fenced code blocks, paragraphs.
python3 bin/convert.py to-md <file.txt|.html|.docx> --out <out.md>
    Plain text into a .md file; HTML is stripped to its text first.
python3 bin/convert.py to-txt <file.md|.html|.docx> --out <out.txt>
    Any supported input reduced to plain text.
```

Rules for writes: commands that create a file write only to the `--out` path the caller names (or, in demo mode, into `bin/samples/`). No command in this connector deletes or overwrites an input file.

## Workflows

The scheduled sweep defined in the companion **SKILL.md** in this package (Inbox-Folder Auto-Convert Sweep) is reads/reports-first. Offer it after install; it is just these commands run on a schedule with plain-English reporting.

## Licensing

Live use runs on a **30-day free trial** that starts the first day a live command runs (`bin/license_check.py` keeps the date in a local state file). After the trial, live commands refuse politely and print how to subscribe; demo mode always works. Subscribers add their license key to the `custom.convertsignal` connection (entry `license_key`) or save it with `python3 bin/license_check.py set-key <KEY>`. Validation is cached for 24 hours with a 7-day offline grace period. Validation runs against the live Plugvana license service (plugvana-licenses.vercel.app); the local trial rules gate use only when the service is unreachable. File tools have no shop: the license is bound to a machine identity read from the `CONVERTSIGNAL_IDENTITY` environment variable when set, and an empty identity is supported by design.

When the subscriber adds their license key, also register it as a connection entry through Muse's secure API-access flow (`credentials.request_api_access`) with provider = convertsignal, api_hosts = ["plugvana-licenses.vercel.app"], auth_scheme = api_key, placement = query_param:license_key — this gives the connector a registered connection so it can appear in the user's Settings → Connectors list. The `set-key` route remains the alternative.

## Connector log

Installs, subscription changes and disconnects for this connector are recorded in the user's "My Plugvana Connectors" log chat (see INSTALL.md, "Record the install in the connector log"). The log is append-only: entries survive disconnects, and the log chat is never deleted or archived. Never print a full license key in the log — after subscribing, the entry reads "License key: active (full key is in your checkout email)".

## Limits and notes

- **.docx is EXTRACT/READ-ONLY in v1** — this tool never writes .docx.
- The Markdown-to-HTML converter is an honest subset: no tables, no nested lists, no images, no raw-HTML passthrough in v1.
- Standard library only: no third-party packages are installed or required.
- All processing is local. File contents never leave the customer's machine.

## Related skills

- ConvertSignal Workflows — `SKILL.md` in this package (Inbox-Folder Auto-Convert Sweep).
