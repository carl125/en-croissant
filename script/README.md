# Scripts

Utility scripts for this fork live here.

## Python Env

Use a repo-local virtual environment so Python dependencies stay isolated from
the rest of the machine.

### Setup

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r script/requirements.txt
```

bash:

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r script/requirements.txt
```

If you are using WSL/Linux/macOS, the Python executable is usually:

```bash
./.venv/bin/python -m pip install -r script/requirements.txt
```

Recommended pattern: call the venv Python directly instead of relying on shell
activation.

## Design

The scripts in this directory should stay layered:

- fetch raw HTTP responses first
- normalize data later in a separate step
- build app-specific formats later still

This keeps network access separate from data conversion and avoids locking the
tooling to one endpoint too early.

## `http_fetch.py`

Generic HTTP fetcher driven by a JSON config file.

It can be reused for:
- Chess.com tactics endpoints
- other Chess.com endpoints
- unrelated JSON or form-based APIs

Supported request config:
- `request.method`
- `request.url`
- `request.headers`
- `request.query`
- `request.form`
- `request.json`
- `request.body`

Supported output config:
- `output.path`
- `output.pretty`
- `output.includeMetadata`

### Example

Start by copying the sample config:

```powershell
Copy-Item script/config/http_chesscom_tactics.example.json script/config/http_chesscom_tactics.json
```

Then fill in the request values and run:

```powershell
.\.venv\Scripts\python script/http_fetch.py --config script/config/http_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/http_fetch.py --config script/config/http_chesscom_tactics.json
```

The sample config is only a preset. The fetcher itself is not Chess.com-specific.

## `normalize_chesscom_tactics.py`

Converts the raw Chess.com tactics JSON into an intermediate puzzle format.

This stage:
- reads `data.tactics`
- tokenizes `clean_move_string`
- converts SAN moves into UCI moves
- writes a normalized JSON file
- records per-puzzle parse errors without failing the whole batch

This stage does not create any SQLite database.

### Example

```powershell
.\.venv\Scripts\python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics.json
```

## `normalize_chesscom_daily.py`

Converts one Chess.com daily puzzle response into the shared intermediate puzzle format.

This stage:
- reads `data` from the daily puzzle response
- parses the PGN into `fen` and `uci_moves`
- assigns the fixed theme `daily`
- offsets IDs by default with `1000000000 + daily_id`

### Example

```powershell
.\.venv\Scripts\python script/normalize_chesscom_daily.py --config script/config/normalize_chesscom_daily.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/normalize_chesscom_daily.py --config script/config/normalize_chesscom_daily.json
```

## `build_puzzle_db.py`

Builds an en-croissant-compatible `.db3` puzzle database from normalized JSON.

This stage:
- reads normalized puzzle JSON
- creates SQLite tables matching the app's puzzle backend expectations
- appends only new puzzles into an existing DB
- writes `puzzles`, `themes`, and `puzzle_themes`

Schema file:

- `script/sql/puzzle_db.sql`

Config:

- `script/config/build_puzzle_db.json`

Output example:

- `script/output/chesscom_tactics.db3`

### Example

PowerShell:

```powershell
.\.venv\Scripts\python script/build_puzzle_db.py --config script/config/build_puzzle_db.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/build_puzzle_db.py --config script/config/build_puzzle_db.json
```

## `pipeline_chesscom_tactics.py`

Runs the whole current Chess.com tactics pipeline:

- fetch raw JSON
- normalize puzzle data
- build the `.db3`

Config:

- `script/config/pipeline_chesscom_tactics.json`
- `script/config/pipeline_chesscom_tactics.example.json`

This is a thin orchestrator over the existing scripts, but it runs in-memory by
default. Intermediate `raw` and `normalized` files are only written when the
pipeline config enables them.

Useful options in `script/config/pipeline_chesscom_tactics.json`:

- `maxBatches`: how many fetch/normalize passes to run
- `stepIncrement`: how much to increase `request.form.step` after each batch
- `stopOnShortBatch`: stop early if the API returns fewer items than `batchSize`
- `continueOnNormalizeWarnings`: keep building even if some puzzles fail to normalize
- `saveRaw`: optionally write the fetched body to the fetch output path
- `saveNormalized`: optionally write the merged normalized JSON before DB build

### Example

PowerShell:

```powershell
.\.venv\Scripts\python script/pipeline_chesscom_tactics.py --config script/config/pipeline_chesscom_tactics.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/pipeline_chesscom_tactics.py --config script/config/pipeline_chesscom_tactics.json
```

## `pipeline_chesscom_daily.py`

Runs the Chess.com daily puzzle pipeline:

- fetch one daily puzzle by date
- normalize `pgn` into puzzle moves
- append it into the shared `.db3`
- move backward one day at a time

Config:

- `script/config/pipeline_chesscom_daily.json`
- `script/config/pipeline_chesscom_daily.example.json`

State handling:

- `state.currentDate` is the next day to process
- `state.workingDate` is written before each fetch so an interrupted run can resume safely

Useful options:

- `oldestDate`: stop when the cursor moves past this date
- `maxDays`: maximum number of days to process per run
- `idOffset`: namespace offset for daily puzzle IDs
- `themeName`: fixed theme name to attach to every daily puzzle
- `defaultRating`: rating written for daily puzzles so app-side rating filters can see them

### Example

PowerShell:

```powershell
.\.venv\Scripts\python script/pipeline_chesscom_daily.py --config script/config/pipeline_chesscom_daily.json
```

WSL/Linux/macOS:

```bash
./.venv/bin/python script/pipeline_chesscom_daily.py --config script/config/pipeline_chesscom_daily.json
```
