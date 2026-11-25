# PDFSignal Workflows

Scheduled workflows for files handled through PDFSignal (`custom.pdfsignal`). Each workflow is a set of `pdf.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads and reports first.** This workflow never deletes, moves, renames or overwrites the owner's files on its own. Anything it proposes happens only after the owner approves that exact change in this conversation.
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run it once; if it still fails, report the failure plainly instead of guessing.

## Watched-Folder PDF Sweep (standing rules)

**When:** on the schedule the owner sets (default daily), plus whenever the owner asks.
**Purpose:** the headline use case — PDFs handled in batches, automatically, with the owner's presets, so no one ever converts files one at a time again.

1. The owner names a watched folder and their standing rules once, for example: *"every text report that lands here becomes a PDF"*, *"extract the text of every new PDF into a .txt beside it"*, *"report any PDF over 10 MB or over 100 pages"*.
2. Each sweep lists the folder, applies the standing rules to **new or changed files only** (keep a small local note of what was processed), using `pdf.py info`, `pdf.py extract-text` and `pdf.py make` as the rules require.
3. Report one line per file handled and anything out of scope (e.g. a scanned PDF with no text layer). Never delete or overwrite an original; outputs are new files.

## Downloads Folder PDF Tidy-Up Report

**When:** weekly, same weekday (default Monday morning).
**Purpose:** a short, useful report about the owner's files — nothing more.

1. Run `pdf.py info` on each PDF in the folder the owner names (default: their Downloads folder) via a directory listing plus one info call per file.
2. Report only: files over a size the owner sets (default 10 MB), duplicate-looking names, and PDFs older than 90 days — as a tidy-up suggestion list.
3. Never delete, move or rename anything. The report proposes; the owner disposes.

## Available connectors

- PDFSignal — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.pdfsignal/CONNECTOR.md`.
