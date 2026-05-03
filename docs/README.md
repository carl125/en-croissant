# Docs

Local development notes for this fork live in this directory.

Suggested convention:
- `repo-context.md`: high-signal notes about architecture, constraints, and implementation details discovered while working in the codebase
- `features/`: focused notes for individual areas such as puzzles, databases, engines, or accounts
- `decisions/`: design decisions for this fork

Current feature notes:
- `features/puzzles.md`: external puzzle fetch, normalize, and DB build pipeline
- `features/user-created-puzzles.md`: local-only personal puzzle creation and slug-based reload flow

This directory is intentionally fork-specific and does not need to match upstream.


PowerShell:
```
python -m venv .venv
.\.venv\Scripts\python -m pip install -r script/requirements.txt
.\.venv\Scripts\python script/http_fetch.py --config script/config/http_chesscom_tactics.json
.\.venv\Scripts\python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics.json
```

WSL/Linux/macOS:
```
python -m venv .venv
./.venv/bin/python -m pip install -r script/requirements.txt
./.venv/bin/python script/http_fetch.py --config script/config/http_chesscom_tactics.json
./.venv/bin/python script/normalize_chesscom_tactics.py --config script/config/normalize_chesscom_tactics
```
