# ImageSignal Workflows

Scheduled workflows for files handled through ImageSignal (`custom.imagesignal`). Each workflow is a set of `image.py` commands plus a reporting rule. Run them from the connector's `bin/` folder. All output is JSON; translate it into plain English for the owner — never paste raw JSON into a report unless the owner asks.

Ground rules for every workflow:

- **Reads and reports first.** This workflow never deletes, moves, renames or overwrites the owner's files on its own. Anything it proposes happens only after the owner approves that exact change in this conversation.
- **Silence is a feature.** A sweep with nothing to report sends nothing (or a one-line "all clear" only if the owner asked for one).
- **Verify before alarming.** If a command fails or returns something implausible, re-run it once; if it still fails, report the failure plainly instead of guessing.

## Photo Folder Auto-Resize Sweep (preset-driven)

**When:** on the schedule the owner sets (default daily), plus whenever the owner asks.
**Purpose:** the headline use case — images processed in batches, automatically, with the owner's presets, so a folder of photos is never resized one file at a time again.

1. The owner names a watched folder and a preset once: target width/height, output format (PNG/BMP/PPM), and an output folder (default: a `resized/` subfolder).
2. Each sweep runs `image.py batch-info` then `image.py resize`/`convert` on **new or changed images only** (keep a small local note of what was processed).
3. Report one line per file handled, plus anything out of scope (e.g. JPEG resize, which v1 does not do — say so plainly). Originals are never overwritten.

## Photo Folder Size Report

**When:** weekly, same weekday (default Monday morning).
**Purpose:** a short, useful report about the owner's files — nothing more.

1. Run `image.py batch-info` on the folder the owner names (default: their Pictures folder).
2. Report only: total size, the 5 largest images with dimensions, and any format the tool could not read.
3. Reads and reports only — never resizes, converts or deletes an original on its own.

## Available connectors

- ImageSignal — `CONNECTOR.md` in this package; after install it lives with the connector at `~/workspace/custom-connectors/custom.imagesignal/CONNECTOR.md`.
