#!/usr/bin/env python3
"""Run the Chess.com tactics pipeline end-to-end.

Stages:
1. fetch one or more raw JSON batches
2. normalize SAN -> UCI
3. merge and dedupe puzzles by source id
4. build en-croissant-compatible `.db3`
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_puzzle_db import build_db, load_text
from http_fetch import build_request, default_output_path, validate_config as validate_fetch_config
from normalize_chesscom_tactics import normalize_payload, write_json as write_normalized_json

DEFAULT_CONFIG_PATH = Path("script") / "config" / "pipeline_chesscom_tactics.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Chess.com tactics pipeline: fetch -> normalize -> build db.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the JSON config file.",
    )
    return parser.parse_args()


def validate_config(config: dict[str, Any]) -> None:
    stages = config.get("stages", {})
    missing = [
        name
        for name in ("fetch", "normalize", "build")
        if not stages.get(name, {}).get("config")
    ]
    if missing:
        raise SystemExit(f"Missing stage config path for: {', '.join(missing)}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def fetch_json(fetch_config: dict[str, Any]) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    validate_fetch_config(fetch_config)
    request, _ = build_request(fetch_config)

    try:
        with urllib.request.urlopen(request) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type")
            response_text = raw_bytes.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while sending request\n{error_body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error: {exc}") from exc

    if not content_type or "json" not in content_type.lower():
        raise SystemExit(f"Expected JSON response, got content-type={content_type!r}")

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Response was not valid JSON: {exc}") from exc


def dedupe_puzzles(
    aggregate: dict[int, dict[str, Any]],
    normalized: dict[str, Any],
) -> tuple[int, int]:
    added = 0
    skipped = 0
    for puzzle in normalized.get("puzzles", []):
        puzzle_id = int(puzzle["id"])
        if puzzle_id in aggregate:
            skipped += 1
            continue
        aggregate[puzzle_id] = puzzle
        added += 1
    return added, skipped


def merge_errors(all_errors: list[dict[str, Any]], normalized: dict[str, Any], step: int) -> None:
    for error in normalized.get("errors", []):
        all_errors.append(
            {
                "step": step,
                **error,
            }
        )


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    validate_config(config)

    stages = config["stages"]
    options = config.get("options", {})
    continue_on_normalize_warnings = bool(options.get("continueOnNormalizeWarnings", True))
    max_batches = int(options.get("maxBatches", 1))

    fetch_config_path = Path(stages["fetch"]["config"])
    normalize_config_path = Path(stages["normalize"]["config"])
    build_config_path = Path(stages["build"]["config"])

    fetch_config = load_json(fetch_config_path)
    normalize_config = load_json(normalize_config_path)
    build_config = load_json(build_config_path)

    request_form = fetch_config.setdefault("request", {}).setdefault("form", {})
    if "batchSize" not in request_form or "step" not in request_form:
        raise SystemExit("Fetch config must include request.form.batchSize and request.form.step.")

    batch_size = int(request_form["batchSize"])
    current_step = int(request_form["step"])
    step_increment = int(options.get("stepIncrement", batch_size))
    stop_on_short_batch = bool(options.get("stopOnShortBatch", True))
    save_raw = bool(options.get("saveRaw", False))
    save_normalized = bool(options.get("saveNormalized", False))

    fetch_output_path = Path(
        fetch_config.get("output", {}).get("path") or default_output_path("application/json")
    )
    normalized_output_path = Path(normalize_config["output"]["path"])

    aggregate_puzzles: dict[int, dict[str, Any]] = {}
    aggregate_errors: list[dict[str, Any]] = []
    batches_run = 0
    total_fetched = 0
    total_skipped = 0

    for batch_index in range(max_batches):
        request_form["step"] = current_step
        print(f"[pipeline] fetch step={current_step} batchSize={batch_size}")

        raw_data = fetch_json(fetch_config)
        if save_raw:
            fetch_output_path.parent.mkdir(parents=True, exist_ok=True)
            with fetch_output_path.open("w", encoding="utf-8") as handle:
                json.dump(raw_data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            print(fetch_output_path)

        tactics = raw_data.get("data", {}).get("tactics", [])
        fetched_count = len(tactics)
        total_fetched += fetched_count
        batches_run += 1

        normalized = normalize_payload(raw_data)
        merge_errors(aggregate_errors, normalized, current_step)
        added, skipped = dedupe_puzzles(aggregate_puzzles, normalized)
        total_skipped += skipped

        print(
            f"[pipeline] normalize step={current_step} fetched={fetched_count} "
            f"added={added} skipped={skipped} errors={len(normalized.get('errors', []))}"
        )

        if normalized["summary"]["error_count"] > 0 and not continue_on_normalize_warnings:
            break

        if fetched_count == 0:
            break
        if stop_on_short_batch and fetched_count < batch_size:
            break

        current_step += step_increment

    normalized_aggregate = {
        "source": "chesscom_tactics",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "batch_count": batches_run,
            "input_count": total_fetched,
            "normalized_count": len(aggregate_puzzles),
            "duplicate_count": total_skipped,
            "error_count": len(aggregate_errors),
        },
        "puzzles": [aggregate_puzzles[puzzle_id] for puzzle_id in sorted(aggregate_puzzles)],
        "errors": aggregate_errors,
    }
    if save_normalized:
        write_normalized_json(
            normalized_output_path,
            normalized_aggregate,
            pretty=bool(normalize_config.get("output", {}).get("pretty", True)),
        )
        print(normalized_output_path)

    schema_path = Path(
        build_config.get("schema", {}).get("path", Path("script") / "sql" / "puzzle_db.sql")
    )
    build_stats = build_db(
        normalized=normalized_aggregate,
        output_path=Path(build_config["output"]["path"]),
        schema_sql=load_text(schema_path),
        rating_deviation_default=int(
            build_config.get("options", {}).get("ratingDeviationDefault", 0)
        ),
        popularity_field=str(build_config.get("options", {}).get("popularityField", "passed_count")),
    )
    print(build_config["output"]["path"])
    print(
        f"puzzles={build_stats['puzzle_count']} themes={build_stats['theme_count']} "
        f"puzzle_themes={build_stats['puzzle_theme_count']}",
        file=sys.stderr,
    )
    return 0 if len(aggregate_errors) == 0 or continue_on_normalize_warnings else 2


if __name__ == "__main__":
    raise SystemExit(main())
