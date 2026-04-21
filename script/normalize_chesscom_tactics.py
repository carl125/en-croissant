#!/usr/bin/env python3
"""Normalize Chess.com tactics JSON into a stable intermediate puzzle format.

This script reads the raw HTTP response body saved by `http_fetch.py`, converts
the SAN move string into a SAN list plus a UCI list, and writes a normalized
JSON file. It intentionally does not create any SQLite database.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import chess
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "Missing dependency: python-chess. Install it with `python -m pip install python-chess`."
    ) from exc


DEFAULT_CONFIG_PATH = Path("script") / "config" / "normalize_chesscom_tactics.json"

MOVE_NUMBER_RE = re.compile(r"\d+\.(?:\.\.)?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize Chess.com tactics JSON into an intermediate puzzle format.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the JSON config file.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def validate_config(config: dict[str, Any]) -> None:
    input_path = config.get("input", {}).get("path")
    output_path = config.get("output", {}).get("path")
    if not input_path:
        raise SystemExit("Config is missing input.path.")
    if not output_path:
        raise SystemExit("Config is missing output.path.")


def tokenize_san_moves(clean_move_string: str) -> list[str]:
    stripped = MOVE_NUMBER_RE.sub(" ", clean_move_string).strip()
    if not stripped:
        return []
    return [token for token in stripped.split() if token]


def convert_san_to_uci(initial_fen: str, san_moves: list[str]) -> list[str]:
    board = chess.Board(initial_fen)
    uci_moves: list[str] = []
    for san in san_moves:
        move = board.parse_san(san)
        uci_moves.append(move.uci())
        board.push(move)
    return uci_moves


def normalize_tactic(tactic: dict[str, Any]) -> dict[str, Any]:
    san_moves = tokenize_san_moves(str(tactic["clean_move_string"]))
    uci_moves = convert_san_to_uci(str(tactic["initial_fen"]), san_moves)
    themes = [theme["name"] for theme in tactic.get("themes", [])]

    return {
        "id": tactic["id"],
        "fen": tactic["initial_fen"],
        "san_moves": san_moves,
        "uci_moves": uci_moves,
        "rating": tactic.get("rating"),
        "attempt_count": tactic.get("attempt_count"),
        "passed_count": tactic.get("passed_count"),
        "average_seconds": tactic.get("average_seconds"),
        "themes": themes,
        "user_moves_first": tactic.get("user_moves_first"),
        "user_position": tactic.get("user_position"),
        "move_count": tactic.get("move_count"),
        "source": "chesscom_tactics",
    }


def normalize_payload(raw_data: dict[str, Any]) -> dict[str, Any]:
    tactics = raw_data.get("data", {}).get("tactics", [])
    puzzles: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for tactic in tactics:
        try:
            puzzles.append(normalize_tactic(tactic))
        except Exception as exc:  # pragma: no cover - per-record fault tolerance
            errors.append(
                {
                    "id": tactic.get("id"),
                    "fen": tactic.get("initial_fen"),
                    "clean_move_string": tactic.get("clean_move_string"),
                    "error": str(exc),
                }
            )

    return {
        "source": "chesscom_tactics",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "input_count": len(tactics),
            "normalized_count": len(puzzles),
            "error_count": len(errors),
        },
        "puzzles": puzzles,
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if pretty:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        else:
            json.dump(data, handle, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    validate_config(config)

    input_path = Path(config["input"]["path"])
    output_path = Path(config["output"]["path"])
    pretty = bool(config.get("output", {}).get("pretty", True))

    raw_data = load_json(input_path)
    normalized = normalize_payload(raw_data)
    write_json(output_path, normalized, pretty=pretty)

    print(output_path)
    if normalized["summary"]["error_count"] > 0:
        print(
            f"Normalized with {normalized['summary']['error_count']} puzzle errors.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
