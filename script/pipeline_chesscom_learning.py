#!/usr/bin/env python3
"""Run the Chess.com learning tactics pipeline directly into the shared DB."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_puzzle_db import build_db, load_text
from fetch_chesscom_learning import (
    crawl_learning,
    parse_rating_bucket_override,
    parse_theme_override,
    write_json,
)
from normalize_chesscom_tactics import normalize_payload, write_json as write_normalized_json


DEFAULT_CONFIG_PATH = Path("script") / "config" / "pipeline_chesscom_learning.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Chess.com learning tactics: crawl -> normalize -> build db.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the JSON config file.",
    )
    parser.add_argument(
        "--max-buckets",
        type=int,
        help="Optional cap on missed/theme/rating buckets for this run.",
    )
    parser.add_argument(
        "--requests-per-bucket",
        type=int,
        help="Override fetch options.requestsPerBucket for this run.",
    )
    parser.add_argument(
        "--themes",
        help="Comma-separated theme ids to use for this run.",
    )
    parser.add_argument(
        "--rating-bucket",
        help="Single rating bucket for this run, formatted MIN-MAX.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore an existing raw output file for this run.",
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
    stages = config.get("stages", {})
    missing = [
        name
        for name in ("fetch", "build")
        if not stages.get(name, {}).get("config")
    ]
    if missing:
        raise SystemExit(f"Missing stage config path for: {', '.join(missing)}")


def dedupe_puzzles(normalized: dict[str, Any]) -> dict[str, Any]:
    puzzles_by_id: dict[int, dict[str, Any]] = {}
    duplicate_count = 0
    for puzzle in normalized.get("puzzles", []):
        puzzle_id = int(puzzle["id"])
        if puzzle_id in puzzles_by_id:
            duplicate_count += 1
            continue
        puzzles_by_id[puzzle_id] = puzzle

    return {
        "source": "chesscom_learning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            **normalized.get("summary", {}),
            "normalized_count": len(puzzles_by_id),
            "duplicate_count": duplicate_count,
        },
        "puzzles": [puzzles_by_id[puzzle_id] for puzzle_id in sorted(puzzles_by_id)],
        "errors": normalized.get("errors", []),
    }


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    validate_config(config)

    stages = config["stages"]
    options = config.get("options", {})
    fetch_config = load_json(Path(stages["fetch"]["config"]))
    build_config = load_json(Path(stages["build"]["config"]))

    raw_data = crawl_learning(
        fetch_config,
        max_buckets=args.max_buckets,
        requests_per_bucket_override=args.requests_per_bucket,
        themes_override=parse_theme_override(args.themes),
        rating_bucket_override=parse_rating_bucket_override(args.rating_bucket),
        no_resume=args.no_resume,
    )

    if bool(options.get("saveRaw", False)):
        raw_output_path = Path(fetch_config["output"]["path"])
        write_json(raw_output_path, raw_data, pretty=bool(fetch_config.get("output", {}).get("pretty", True)))
        print(raw_output_path)

    normalized = dedupe_puzzles(normalize_payload(raw_data))
    normalized_output_path = None
    if bool(options.get("saveNormalized", False)):
        normalized_output_path = Path(
            options.get("normalizedOutputPath", "script/output/chesscom_learning_normalized.json")
        )
        write_normalized_json(
            normalized_output_path,
            normalized,
            pretty=bool(options.get("prettyNormalized", True)),
        )
        print(normalized_output_path)

    schema_path = Path(
        build_config.get("schema", {}).get("path", Path("script") / "sql" / "puzzle_db.sql")
    )
    build_stats = build_db(
        normalized=normalized,
        output_path=Path(build_config["output"]["path"]),
        schema_sql=load_text(schema_path),
        rating_deviation_default=int(
            build_config.get("options", {}).get("ratingDeviationDefault", 0)
        ),
        popularity_field=str(build_config.get("options", {}).get("popularityField", "passed_count")),
    )

    print(build_config["output"]["path"])
    print(
        f"fetched={raw_data['summary']['tactic_count']} "
        f"normalized={normalized['summary']['normalized_count']} "
        f"errors={normalized['summary']['error_count']} "
        f"db_inserted={build_stats['inserted_puzzle_count']} "
        f"db_existing={build_stats['existing_puzzle_count']} "
        f"db_total={build_stats['total_puzzle_count']}"
    )
    return 0 if normalized["summary"]["error_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
