#!/usr/bin/env python3
"""Run the Chess.com daily puzzle pipeline day-by-day into the shared DB."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from build_puzzle_db import build_db, load_text
from normalize_chesscom_daily import (
    DEFAULT_ID_OFFSET,
    DEFAULT_RATING,
    DEFAULT_THEME,
    normalize_payload,
)


DEFAULT_CONFIG_PATH = Path("script") / "config" / "pipeline_chesscom_daily.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Chess.com daily puzzle pipeline: fetch -> normalize -> build db.",
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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid ISO date in {field_name}: {value}") from exc


def format_output_path(path_template: str, working_date: str) -> Path:
    return Path(path_template.format(date=working_date))


def validate_config(config: dict[str, Any]) -> None:
    request = config.get("request", {})
    state = config.get("state", {})
    stages = config.get("stages", {})

    if not request.get("urlTemplate"):
        raise SystemExit("Config is missing request.urlTemplate.")
    if "{date}" not in str(request["urlTemplate"]):
        raise SystemExit("request.urlTemplate must contain {date}.")
    if not state.get("currentDate"):
        raise SystemExit("Config is missing state.currentDate.")
    if not stages.get("build", {}).get("config"):
        raise SystemExit("Config is missing stages.build.config.")


def fetch_json(request_config: dict[str, Any], working_date: str) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    url = str(request_config["urlTemplate"]).format(date=working_date)
    headers = {str(key): str(value) for key, value in request_config.get("headers", {}).items()}
    method = str(request_config.get("method", "GET")).upper()
    request = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type")
            response_text = raw_bytes.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} while fetching {working_date}\n{error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while fetching {working_date}: {exc}") from exc

    if not content_type or "json" not in content_type.lower():
        raise RuntimeError(
            f"Expected JSON response for {working_date}, got content-type={content_type!r}"
        )

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Response for {working_date} was not valid JSON: {exc}") from exc


def main() -> int:
    args = parse_args()
    config_path = args.config
    config = load_json(config_path)
    validate_config(config)

    request_config = config["request"]
    options = config.get("options", {})
    state = config.setdefault("state", {})
    build_config = load_json(Path(config["stages"]["build"]["config"]))
    schema_path = Path(
        build_config.get("schema", {}).get("path", Path("script") / "sql" / "puzzle_db.sql")
    )

    current_date = parse_iso_date(str(state["currentDate"]), "state.currentDate")
    oldest_date_text = options.get("oldestDate")
    oldest_date = (
        parse_iso_date(str(oldest_date_text), "options.oldestDate")
        if oldest_date_text
        else date(1900, 1, 1)
    )
    max_days = int(options.get("maxDays", 1))
    save_raw = bool(options.get("saveRaw", False))
    save_normalized = bool(options.get("saveNormalized", False))
    raw_output_template = options.get("rawOutputPathTemplate")
    normalized_output_template = options.get("normalizedOutputPathTemplate")
    id_offset = int(options.get("idOffset", DEFAULT_ID_OFFSET))
    theme_name = str(options.get("themeName", DEFAULT_THEME))
    default_rating = int(options.get("defaultRating", DEFAULT_RATING))

    processed_day_count = 0
    inserted_total = 0
    existing_total = 0
    error_total = 0

    for _ in range(max_days):
        if current_date < oldest_date:
            break

        working_date = current_date.isoformat()
        state["workingDate"] = working_date
        write_json(config_path, config)
        print(f"[pipeline] fetch date={working_date}")

        raw_data = fetch_json(request_config, working_date)
        if save_raw and raw_output_template:
            raw_output_path = format_output_path(str(raw_output_template), working_date)
            write_json(raw_output_path, raw_data)
            print(raw_output_path)

        normalized = normalize_payload(
            raw_data,
            id_offset=id_offset,
            theme_name=theme_name,
            default_rating=default_rating,
        )
        if save_normalized and normalized_output_template:
            normalized_output_path = format_output_path(
                str(normalized_output_template),
                working_date,
            )
            write_json(normalized_output_path, normalized)
            print(normalized_output_path)

        print(
            f"[pipeline] normalize date={working_date} "
            f"added={normalized['summary']['normalized_count']} "
            f"errors={normalized['summary']['error_count']}"
        )
        if normalized["summary"]["error_count"] > 0:
            error_total += normalized["summary"]["error_count"]
            break

        build_stats = build_db(
            normalized=normalized,
            output_path=Path(build_config["output"]["path"]),
            schema_sql=load_text(schema_path),
            rating_deviation_default=int(
                build_config.get("options", {}).get("ratingDeviationDefault", 0)
            ),
            popularity_field=str(
                build_config.get("options", {}).get("popularityField", "passed_count")
            ),
        )

        inserted_total += build_stats["inserted_puzzle_count"]
        existing_total += build_stats["existing_puzzle_count"]
        error_total += normalized["summary"]["error_count"]
        processed_day_count += 1

        print(
            f"[pipeline] build date={working_date} "
            f"db_inserted={build_stats['inserted_puzzle_count']} "
            f"db_existing={build_stats['existing_puzzle_count']} "
            f"db_total={build_stats['puzzle_count']}"
        )

        current_date -= timedelta(days=1)
        state["currentDate"] = current_date.isoformat()
        state["workingDate"] = None
        write_json(config_path, config)

    print(build_config["output"]["path"])
    print(
        f"days={processed_day_count} inserted={inserted_total} existing={existing_total} "
        f"errors={error_total} next_date={state['currentDate']}",
        file=sys.stderr,
    )
    return 0 if error_total == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
