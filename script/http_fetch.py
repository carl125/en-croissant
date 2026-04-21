#!/usr/bin/env python3
"""Generic HTTP fetcher driven by a JSON config file.

This script is intentionally generic. It handles request construction and raw
response capture only; endpoint-specific normalization should happen elsewhere.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("script") / "config" / "http_request.json"
DEFAULT_OUTPUT_DIR = Path("script") / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send an HTTP request defined in a JSON config file.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the JSON config file.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Config file is not valid JSON: {exc}") from exc


def validate_config(config: dict[str, Any]) -> None:
    request_data = config.get("request")
    if not isinstance(request_data, dict):
        raise SystemExit("Config is missing a request object.")
    if not request_data.get("url"):
        raise SystemExit("Config is missing request.url.")

    body_fields = [key for key in ("form", "json", "body") if key in request_data]
    if len(body_fields) > 1:
        raise SystemExit("Use only one of request.form, request.json, or request.body.")


def normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(key): str(value) for key, value in headers.items()}


def build_url(url: str, query: dict[str, Any] | None) -> str:
    if not query:
        return url
    encoded_query = urllib.parse.urlencode(
        [(str(key), str(value)) for key, value in query.items()],
        doseq=True,
    )
    separator = "&" if urllib.parse.urlparse(url).query else "?"
    return f"{url}{separator}{encoded_query}"


def build_body(request_data: dict[str, Any], headers: dict[str, str]) -> bytes | None:
    if "form" in request_data:
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        return urllib.parse.urlencode(request_data["form"]).encode("utf-8")
    if "json" in request_data:
        headers.setdefault("Content-Type", "application/json")
        return json.dumps(request_data["json"], ensure_ascii=False).encode("utf-8")
    if "body" in request_data:
        body = request_data["body"]
        if isinstance(body, str):
            return body.encode("utf-8")
        return json.dumps(body, ensure_ascii=False).encode("utf-8")
    return None


def build_request(config: dict[str, Any]) -> tuple[urllib.request.Request, dict[str, Any]]:
    request_data = config["request"]
    method = str(request_data.get("method", "GET")).upper()
    headers = normalize_headers(request_data.get("headers"))
    url = build_url(str(request_data["url"]), request_data.get("query"))
    body = build_body(request_data, headers)

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    metadata = {
        "method": method,
        "url": url,
        "headers": headers,
        "hasBody": body is not None,
    }
    if "query" in request_data:
        metadata["query"] = request_data["query"]
    if "form" in request_data:
        metadata["form"] = request_data["form"]
    if "json" in request_data:
        metadata["json"] = request_data["json"]
    if "body" in request_data:
        metadata["body"] = request_data["body"]
    return request, metadata


def infer_extension(content_type: str | None) -> str:
    if not content_type:
        return ".txt"
    lower = content_type.lower()
    if "json" in lower:
        return ".json"
    if "html" in lower:
        return ".html"
    if "xml" in lower:
        return ".xml"
    return ".txt"


def default_output_path(content_type: str | None) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_DIR / f"{timestamp}_response{infer_extension(content_type)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    config = load_config(args.config)
    validate_config(config)

    request, request_metadata = build_request(config)
    output_config = config.get("output", {})

    try:
        with urllib.request.urlopen(request) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type")
            response_text = raw_bytes.decode("utf-8", errors="replace")
            status = response.status
            response_headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} while sending request", file=sys.stderr)
        print(error_body, file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1

    output_path = (
        Path(output_config["path"])
        if output_config.get("path")
        else default_output_path(content_type)
    )
    pretty = bool(output_config.get("pretty", True))
    include_metadata = bool(output_config.get("includeMetadata", True))

    parsed_json: Any | None = None
    if content_type and "json" in content_type.lower():
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            parsed_json = None

    if include_metadata:
        payload: dict[str, Any] = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "request": request_metadata,
            "response": {
                "status": status,
                "headers": response_headers,
                "contentType": content_type,
            },
            "body": parsed_json if parsed_json is not None else response_text,
        }
        write_json(output_path, payload, pretty=pretty)
    elif parsed_json is not None:
        write_json(output_path, parsed_json, pretty=pretty)
    else:
        write_text(output_path, response_text)

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
