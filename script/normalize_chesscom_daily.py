#!/usr/bin/env python3
"""Normalize a Chess.com daily puzzle response into the shared puzzle format."""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import chess
    import chess.pgn
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "Missing dependency: python-chess. Install it with `python -m pip install python-chess`."
    ) from exc


DEFAULT_CONFIG_PATH = Path("script") / "config" / "normalize_chesscom_daily.json"
DEFAULT_ID_OFFSET = 1_000_000_000
DEFAULT_THEME = "daily"
DEFAULT_RATING = 800


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a Chess.com daily puzzle response into an intermediate puzzle format.",
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


def parse_pgn(pgn_text: str) -> tuple[str, list[str]]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN did not contain a game.")

    starting_fen = game.headers.get("FEN")
    board = chess.Board(starting_fen) if starting_fen else game.board()
    initial_fen = board.fen()
    uci_moves: list[str] = []

    for move in game.mainline_moves():
        uci_moves.append(move.uci())
        board.push(move)

    return initial_fen, uci_moves


def normalize_daily_puzzle(
    raw_data: dict[str, Any],
    *,
    id_offset: int = DEFAULT_ID_OFFSET,
    theme_name: str = DEFAULT_THEME,
    default_rating: int = DEFAULT_RATING,
) -> dict[str, Any]:
    data = raw_data.get("data")
    if not isinstance(data, dict):
        raise ValueError("Response is missing data.")

    source_id = int(data["id"])
    fen, uci_moves = parse_pgn(str(data["pgn"]))
    solved_count = int(data.get("solved_count") or 0)

    return {
        "id": id_offset + source_id,
        "source_id": source_id,
        "fen": fen,
        "san_moves": [],
        "uci_moves": uci_moves,
        "user_moves_first": True,
        "rating": default_rating,
        "attempt_count": solved_count,
        "passed_count": solved_count,
        "average_seconds": None,
        "themes": [theme_name],
        "source": "chesscom_daily",
        "puzzle_date": data.get("puzzle_date"),
        "title": data.get("title"),
    }


def normalize_payload(
    raw_data: dict[str, Any],
    *,
    id_offset: int = DEFAULT_ID_OFFSET,
    theme_name: str = DEFAULT_THEME,
    default_rating: int = DEFAULT_RATING,
) -> dict[str, Any]:
    puzzles: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    try:
        puzzles.append(
            normalize_daily_puzzle(
                raw_data,
                id_offset=id_offset,
                theme_name=theme_name,
                default_rating=default_rating,
            )
        )
    except Exception as exc:  # pragma: no cover - per-record fault tolerance
        errors.append(
            {
                "id": raw_data.get("data", {}).get("id"),
                "error": str(exc),
            }
        )

    return {
        "source": "chesscom_daily",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "input_count": 1 if raw_data.get("data") else 0,
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
    options = config.get("options", {})

    raw_data = load_json(input_path)
    normalized = normalize_payload(
        raw_data,
        id_offset=int(options.get("idOffset", DEFAULT_ID_OFFSET)),
        theme_name=str(options.get("themeName", DEFAULT_THEME)),
        default_rating=int(options.get("defaultRating", DEFAULT_RATING)),
    )
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
