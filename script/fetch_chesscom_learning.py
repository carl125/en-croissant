#!/usr/bin/env python3
"""Fetch many Chess.com learning tactics by sweeping theme and rating filters."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("script") / "config" / "fetch_chesscom_learning.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl Chess.com /v1/tactics/learning into data.tactics[] JSON.",
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
        help="Optional cap on theme/rating buckets for this run.",
    )
    parser.add_argument(
        "--requests-per-bucket",
        type=int,
        help="Override options.requestsPerBucket for this run.",
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
        help="Ignore an existing output file for this run.",
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


def write_json(path: Path, data: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if pretty:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        else:
            json.dump(data, handle, ensure_ascii=False)
        handle.write("\n")


def validate_config(config: dict[str, Any]) -> None:
    if not config.get("request", {}).get("url"):
        raise SystemExit("Config is missing request.url.")
    if not config.get("output", {}).get("path"):
        raise SystemExit("Config is missing output.path.")
    if not config.get("themes"):
        raise SystemExit("Config is missing themes.")
    if not config.get("ratingBuckets"):
        raise SystemExit("Config is missing ratingBuckets.")


def load_headers(request_config: dict[str, Any]) -> dict[str, str]:
    headers = request_config.get("headers")
    if headers:
        return {str(key): str(value) for key, value in headers.items()}

    headers_from_config = request_config.get("headersFromConfig")
    if headers_from_config:
        source_config = load_json(Path(headers_from_config))
        source_headers = source_config.get("request", {}).get("headers", {})
        return {str(key): str(value) for key, value in source_headers.items()}

    return {}


def build_url(
    base_url: str,
    *,
    min_rating: int,
    max_rating: int,
    missed: int,
    theme_id: int,
    cache_bust: bool,
    request_index: int,
) -> str:
    query: dict[str, Any] = {
        "maxRating": max_rating,
        "minRating": min_rating,
        "missed": missed,
        "themes[]": [theme_id],
    }
    if cache_bust:
        query["_learningCrawl"] = request_index

    encoded_query = urllib.parse.urlencode(query, doseq=True)
    separator = "&" if urllib.parse.urlparse(base_url).query else "?"
    return f"{base_url}{separator}{encoded_query}"


def fetch_learning_tactic(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_text = response.read().decode("utf-8", errors="replace")
        return json.loads(response_text)


def bucket_key(stat: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(stat.get("missed", 0)),
        int(stat["theme_id"]),
        int(stat["min_rating"]),
        int(stat["max_rating"]),
    )


def make_output(
    *,
    themes: list[int],
    rating_buckets: list[tuple[int, int]],
    missed_values: list[int],
    request_count: int,
    tactics_by_id: dict[int, dict[str, Any]],
    stats: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "success",
        "source": "chesscom_learning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "theme_count": len(themes),
            "rating_bucket_count": len(rating_buckets),
            "missed_values": missed_values,
            "request_count": request_count,
            "tactic_count": len(tactics_by_id),
            "error_count": len(errors),
        },
        "data": {
            "tactics": [tactics_by_id[tactic_id] for tactic_id in sorted(tactics_by_id)],
        },
        "stats": stats,
        "errors": errors,
    }


def parse_theme_override(value: str | None) -> list[int] | None:
    if not value:
        return None
    return [int(theme_id.strip()) for theme_id in value.split(",") if theme_id.strip()]


def parse_rating_bucket_override(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    min_rating_text, separator, max_rating_text = value.partition("-")
    if not separator:
        raise SystemExit("--rating-bucket must be formatted MIN-MAX.")
    return int(min_rating_text), int(max_rating_text)


def crawl_learning(
    config: dict[str, Any],
    *,
    max_buckets: int | None = None,
    requests_per_bucket_override: int | None = None,
    themes_override: list[int] | None = None,
    rating_bucket_override: tuple[int, int] | None = None,
    no_resume: bool = False,
) -> dict[str, Any]:
    validate_config(config)

    request_config = config["request"]
    output_config = config["output"]
    options = config.get("options", {})

    base_url = str(request_config["url"])
    headers = load_headers(request_config)
    headers.setdefault("Accept", "*/*")
    headers.setdefault("Accept-Encoding", "identity")
    headers.setdefault("Cache-Control", "no-cache")

    themes = themes_override or [int(theme_id) for theme_id in config["themes"]]
    rating_buckets = [
        (int(bucket[0]), int(bucket[1])) for bucket in config["ratingBuckets"]
    ]
    if rating_bucket_override:
        rating_buckets = [rating_bucket_override]
    missed_values = [int(value) for value in options.get("missedValues", [options.get("missed", 0)])]
    requests_per_bucket = int(requests_per_bucket_override or options.get("requestsPerBucket", 100))
    stop_after_duplicate_streak = int(options.get("stopAfterDuplicateStreak", 20))
    sleep_seconds = float(options.get("sleepSeconds", 0.1))
    timeout = float(options.get("timeoutSeconds", 20))
    cache_bust = bool(options.get("cacheBust", True))
    resume = bool(options.get("resume", True)) and not no_resume
    save_every_bucket = bool(options.get("saveEveryBucket", True))
    progress_dots = bool(options.get("progressDots", True))
    progress_dot_every = int(options.get("progressDotEvery", 1))
    pretty = bool(output_config.get("pretty", True))
    output_path = Path(output_config["path"])

    tactics_by_id: dict[int, dict[str, Any]] = {}
    stats: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    request_index = 0
    completed_buckets: set[tuple[int, int, int, int]] = set()
    processed_bucket_count = 0

    if resume and output_path.exists():
        existing_output = load_json(output_path)
        for tactic in existing_output.get("data", {}).get("tactics", []):
            if isinstance(tactic, dict) and "id" in tactic:
                tactics_by_id[int(tactic["id"])] = tactic
        raw_stats = [
            stat for stat in existing_output.get("stats", []) if isinstance(stat, dict)
        ]
        errors = [
            error for error in existing_output.get("errors", []) if isinstance(error, dict)
        ]
        bucket_counts: dict[tuple[int, int, int, int], int] = {}
        for stat in raw_stats:
            key = bucket_key(stat)
            bucket_counts[key] = bucket_counts.get(key, 0) + 1

        stats = [
            stat
            for stat in raw_stats
            if bool(stat.get("completed")) or bucket_counts[bucket_key(stat)] == 1
        ]
        completed_buckets = {bucket_key(stat) for stat in stats}
        request_index = int(existing_output.get("summary", {}).get("request_count") or 0)

    for missed in missed_values:
        for theme_id in themes:
            for min_rating, max_rating in rating_buckets:
                if max_buckets is not None and processed_bucket_count >= max_buckets:
                    break
                if (missed, theme_id, min_rating, max_rating) in completed_buckets:
                    continue

                processed_bucket_count += 1
                duplicate_streak = 0
                request_count = 0
                added_count = 0
                progress_dot_count = 0

                for _ in range(requests_per_bucket):
                    request_index += 1
                    request_count += 1
                    if (
                        progress_dots
                        and progress_dot_every > 0
                        and request_count % progress_dot_every == 0
                    ):
                        print(".", end="", file=sys.stderr, flush=True)
                        progress_dot_count += 1

                    url = build_url(
                        base_url,
                        min_rating=min_rating,
                        max_rating=max_rating,
                        missed=missed,
                        theme_id=theme_id,
                        cache_bust=cache_bust,
                        request_index=request_index,
                    )

                    try:
                        payload = fetch_learning_tactic(url, headers, timeout)
                    except urllib.error.HTTPError as exc:
                        body = exc.read().decode("utf-8", errors="replace")
                        errors.append(
                            {
                                "missed": missed,
                                "theme_id": theme_id,
                                "min_rating": min_rating,
                                "max_rating": max_rating,
                                "status": exc.code,
                                "body": body[:300],
                            }
                        )
                        if exc.code == 404:
                            break
                        continue
                    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                        errors.append(
                            {
                                "missed": missed,
                                "theme_id": theme_id,
                                "min_rating": min_rating,
                                "max_rating": max_rating,
                                "error": str(exc)[:300],
                            }
                        )
                        continue

                    tactic = payload.get("data") if isinstance(payload, dict) else None
                    if not isinstance(tactic, dict) or "id" not in tactic:
                        errors.append(
                            {
                                "missed": missed,
                                "theme_id": theme_id,
                                "min_rating": min_rating,
                                "max_rating": max_rating,
                                "error": "Response did not contain data.id.",
                            }
                        )
                        duplicate_streak += 1
                    else:
                        tactic_id = int(tactic["id"])
                        if tactic_id in tactics_by_id:
                            duplicate_streak += 1
                        else:
                            tactics_by_id[tactic_id] = tactic
                            added_count += 1
                            duplicate_streak = 0

                    if duplicate_streak >= stop_after_duplicate_streak:
                        break
                    if sleep_seconds > 0:
                        time.sleep(sleep_seconds)

                stats.append(
                    {
                        "completed": True,
                        "missed": missed,
                        "theme_id": theme_id,
                        "min_rating": min_rating,
                        "max_rating": max_rating,
                        "requests": request_count,
                        "added": added_count,
                        "duplicate_streak": duplicate_streak,
                    }
                )
                if progress_dots:
                    print(f"\r{' ' * progress_dot_count}\r", end="", file=sys.stderr, flush=True)
                print(
                    f"[learning] missed={missed} theme={theme_id} rating={min_rating}-{max_rating} "
                    f"requests={request_count} added={added_count} total={len(tactics_by_id)}",
                    file=sys.stderr,
                )
                if save_every_bucket:
                    write_json(
                        output_path,
                        make_output(
                            themes=themes,
                            rating_buckets=rating_buckets,
                            missed_values=missed_values,
                            request_count=request_index,
                            tactics_by_id=tactics_by_id,
                            stats=stats,
                            errors=errors,
                        ),
                        pretty=pretty,
                    )
            if max_buckets is not None and processed_bucket_count >= max_buckets:
                break
        if max_buckets is not None and processed_bucket_count >= max_buckets:
            break

    output = make_output(
        themes=themes,
        rating_buckets=rating_buckets,
        missed_values=missed_values,
        request_count=request_index,
        tactics_by_id=tactics_by_id,
        stats=stats,
        errors=errors,
    )
    write_json(output_path, output, pretty=pretty)
    return output


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    crawl_learning(
        config,
        max_buckets=args.max_buckets,
        requests_per_bucket_override=args.requests_per_bucket,
        themes_override=parse_theme_override(args.themes),
        rating_bucket_override=parse_rating_bucket_override(args.rating_bucket),
        no_resume=args.no_resume,
    )
    output_path = Path(config["output"]["path"])
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
