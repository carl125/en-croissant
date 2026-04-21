# Puzzle Pipeline

This document describes the current puzzle-data workflow for this fork.

## Goal

Fetch puzzle data from an external source, normalize it into a stable JSON format,
and then build an app-compatible puzzle database from that normalized layer.

The workflow is intentionally layered:

- fetch raw data
- normalize into stable JSON
- build the app-specific `.db3`

The pipeline runner now executes these stages in-memory by default. Writing
intermediate `raw` and `normalized` files is optional and mainly useful for
debugging.

## Current Stages

### 1. Raw fetch

Script:

- `script/http_fetch.py`

Config:

- `script/config/http_chesscom_tactics.json`

Output:

- `script/output/chesscom_tactics_raw.json`

Purpose:

- send an HTTP request defined by JSON config
- save the response body as JSON
- avoid hardcoding fetch logic to one endpoint
- pipeline usage does not require writing this file unless debug output is enabled

Notes:

- for the Chess.com tactics request, `Accept-Encoding` is set to `identity`
  so the saved output is readable JSON instead of compressed response bytes
- `includeMetadata` is set to `false` so the saved file matches the API body
  directly

### 2. Normalize

Script:

- `script/normalize_chesscom_tactics.py`

Config:

- `script/config/normalize_chesscom_tactics.json`

Output:

- `script/output/chesscom_tactics_normalized.json`

Purpose:

- read the raw Chess.com tactics payload
- tokenize `clean_move_string`
- convert SAN moves to UCI using `initial_fen`
- save a normalized intermediate format
- pipeline usage does not require writing this file unless debug output is enabled

Notes:

- this script uses `python-chess`
- dependency is installed into repo-local `.venv`
- per-puzzle parse failures are written to `errors` instead of crashing the
  whole batch

### 3. Build DB

Script:

- `script/build_puzzle_db.py`

Config:

- `script/config/build_puzzle_db.json`

Schema:

- `script/sql/puzzle_db.sql`

Output:

- `script/output/chesscom_tactics.db3`

Purpose:

- read normalized puzzle JSON
- create a puzzle DB compatible with en-croissant
- append new puzzle data into the DB
- write `puzzles`, `themes`, and `puzzle_themes`

### 4. Orchestrated pipeline

Script:

- `script/pipeline_chesscom_tactics.py`

Config:

- `script/config/pipeline_chesscom_tactics.json`

Purpose:

- run fetch
- run normalize
- run DB build

This is only an orchestrator. Each stage can still be run independently.

Important pipeline options:

- `maxBatches`: number of fetch passes to run
- `stepIncrement`: amount added to `step` after each fetch pass
- `stopOnShortBatch`: stop if the API returns fewer than `batchSize` items
- `continueOnNormalizeWarnings`: continue building the DB even if some puzzles fail to normalize
- `saveRaw`: optionally dump the fetched body to disk
- `saveNormalized`: optionally dump the merged normalized JSON to disk

## Normalized Format

The normalized file is shaped like:

```json
{
  "source": "chesscom_tactics",
  "generated_at": "...",
  "summary": {
    "input_count": 2,
    "normalized_count": 2,
    "error_count": 0
  },
  "puzzles": [
    {
      "id": 1389572,
      "fen": "8/R4k2/3p4/1p1P2bK/1Pp3r1/6r1/8/4R3 b - - 9 53",
      "san_moves": ["Kf6", "Re6+", "Kf5", "Rf7+", "Bf6", "Rfxf6#"],
      "uci_moves": ["f7f6", "e1e6", "f6f5", "a7f7", "g5f6", "f7f6"],
      "rating": 950,
      "attempt_count": 36713,
      "passed_count": 23059,
      "average_seconds": 24,
      "themes": ["Doubled Rook"],
      "user_moves_first": false,
      "user_position": 1,
      "move_count": 3,
      "source": "chesscom_tactics"
    }
  ],
  "errors": []
}
```

Why keep both move lists:

- `san_moves` is useful for debugging and cross-checking against the source
- `uci_moves` is the machine-friendly move list that later stages can use

## Python Environment

Use a repo-local virtual environment:

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r script/requirements.txt
```

WSL/Linux/macOS:

```bash
python -m venv .venv
./.venv/bin/python -m pip install -r script/requirements.txt
```

## Commands

Fetch raw JSON:

PowerShell:

```powershell
.\.venv\Scripts\python script/http_fetch.py --config script/config/http_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/http_fetch.py --config script/config/http_chesscom_tactics.json
```

Normalize:

PowerShell:

```powershell
.\.venv\Scripts\python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics.json
```

Build DB:

PowerShell:

```powershell
.\.venv\Scripts\python script/build_puzzle_db.py --config script/config/build_puzzle_db.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/build_puzzle_db.py --config script/config/build_puzzle_db.json
```

Run the whole pipeline:

PowerShell:

```powershell
.\.venv\Scripts\python script/pipeline_chesscom_tactics.py --config script/config/pipeline_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/pipeline_chesscom_tactics.py --config script/config/pipeline_chesscom_tactics.json
```

## Relationship To En Croissant

This pipeline is intentionally upstream-agnostic until after normalization.

Relevant app constraints:

- en-croissant puzzle runtime expects local puzzle data, not live API calls
- app-facing puzzle storage ultimately needs UCI moves
- theme support exists, but is optional for the final database format
- `user_moves_first` is app logic, not just DB shape:
  - if `false`, the app auto-plays the first move in `moves`
  - if `true`, the player starts from the stored `fen`

## App Runtime Note

If you only change the exported `.db3`, an already-built app will pick up those
data changes immediately.

If you change puzzle runtime behavior in app code, such as the handling of
`user_moves_first`, a prebuilt app will not change behavior until you either:

- run the app from source with `pnpm dev`
- rebuild the desktop app with `pnpm build`

That means the normalized JSON is the bridge between:

- external source formats such as Chess.com tactics payloads
- app-specific SQLite export
