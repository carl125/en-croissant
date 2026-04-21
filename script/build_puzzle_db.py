#!/usr/bin/env python3
"""Build an en-croissant-compatible puzzle SQLite DB from normalized JSON."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("script") / "config" / "build_puzzle_db.json"
DEFAULT_SCHEMA_PATH = Path("script") / "sql" / "puzzle_db.sql"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an en-croissant-compatible puzzle DB from normalized JSON.",
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


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Schema file not found: {path}") from exc


def validate_config(config: dict[str, Any]) -> None:
    if not config.get("input", {}).get("path"):
        raise SystemExit("Config is missing input.path.")
    if not config.get("output", {}).get("path"):
        raise SystemExit("Config is missing output.path.")


def normalize_theme_name(name: str) -> str:
    return name.strip()


def load_existing_puzzle_ids(conn: sqlite3.Connection) -> set[int]:
    return {int(row[0]) for row in conn.execute("SELECT id FROM puzzles")}


def load_existing_themes(conn: sqlite3.Connection) -> tuple[dict[str, int], int]:
    themes = {
        str(name): int(theme_id)
        for theme_id, name in conn.execute("SELECT id, name FROM themes")
    }
    next_theme_id = max(themes.values(), default=0) + 1
    return themes, next_theme_id


def ensure_puzzle_columns(conn: sqlite3.Connection) -> None:
    columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(puzzles)")
    }
    if "user_moves_first" not in columns:
        conn.execute(
            "ALTER TABLE puzzles ADD COLUMN user_moves_first INTEGER NOT NULL DEFAULT 0"
        )


def ensure_schema(conn: sqlite3.Connection, schema_sql: str, output_path: Path) -> None:
    tables = {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('puzzles', 'themes', 'puzzle_themes')"
        )
    }
    if not {"puzzles", "themes", "puzzle_themes"}.issubset(tables):
        conn.executescript(schema_sql)
    ensure_puzzle_columns(conn)


def build_db(
    normalized: dict[str, Any],
    output_path: Path,
    schema_sql: str,
    rating_deviation_default: int,
    popularity_field: str,
) -> dict[str, int]:
    puzzles = normalized.get("puzzles", [])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(output_path)
    try:
        ensure_schema(conn, schema_sql, output_path)

        existing_puzzle_ids = load_existing_puzzle_ids(conn)
        theme_ids, next_theme_id = load_existing_themes(conn)
        inserted_puzzle_count = 0
        existing_puzzle_count = 0
        link_count = 0

        for puzzle in puzzles:
            uci_moves = puzzle.get("uci_moves", [])
            if not uci_moves:
                continue

            puzzle_id = int(puzzle["id"])
            if puzzle_id in existing_puzzle_ids:
                existing_puzzle_count += 1
                continue

            popularity = puzzle.get(popularity_field)
            if popularity is None:
                popularity = 0

            conn.execute(
                """
                INSERT INTO puzzles (
                  id, fen, moves, user_moves_first, rating, rating_deviation, popularity, nb_plays
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    puzzle_id,
                    puzzle["fen"],
                    " ".join(uci_moves),
                    1 if puzzle.get("user_moves_first") else 0,
                    int(puzzle.get("rating") or 0),
                    rating_deviation_default,
                    int(popularity),
                    int(puzzle.get("attempt_count") or 0),
                ),
            )
            existing_puzzle_ids.add(puzzle_id)
            inserted_puzzle_count += 1

            for theme in puzzle.get("themes", []):
                theme_name = normalize_theme_name(str(theme))
                if not theme_name:
                    continue

                theme_id = theme_ids.get(theme_name)
                if theme_id is None:
                    theme_id = next_theme_id
                    next_theme_id += 1
                    theme_ids[theme_name] = theme_id
                    conn.execute(
                        "INSERT INTO themes (id, name) VALUES (?, ?)",
                        (theme_id, theme_name),
                    )

                conn.execute(
                    "INSERT OR IGNORE INTO puzzle_themes (puzzle_id, theme_id) VALUES (?, ?)",
                    (puzzle_id, theme_id),
                )
                link_count += 1

        conn.commit()
        return {
            "inserted_puzzle_count": inserted_puzzle_count,
            "existing_puzzle_count": existing_puzzle_count,
            "puzzle_count": len(existing_puzzle_ids),
            "theme_count": len(theme_ids),
            "puzzle_theme_count": link_count,
            "total_puzzle_count": len(existing_puzzle_ids),
        }
    finally:
        conn.close()


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    validate_config(config)

    input_path = Path(config["input"]["path"])
    output_path = Path(config["output"]["path"])
    schema_path = Path(config.get("schema", {}).get("path", DEFAULT_SCHEMA_PATH))
    options = config.get("options", {})

    normalized = load_json(input_path)
    schema_sql = load_text(schema_path)
    stats = build_db(
        normalized=normalized,
        output_path=output_path,
        schema_sql=schema_sql,
        rating_deviation_default=int(options.get("ratingDeviationDefault", 0)),
        popularity_field=str(options.get("popularityField", "passed_count")),
    )

    print(output_path)
    print(
        f"inserted={stats['inserted_puzzle_count']} existing={stats['existing_puzzle_count']} "
        f"total={stats['total_puzzle_count']} themes={stats['theme_count']} "
        f"puzzle_themes={stats['puzzle_theme_count']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
