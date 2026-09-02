#!/usr/bin/env python3
"""Append-only recorder for the FairEconomy / ForexFactory weekly economic calendar.

The feed serves the CURRENT WEEK ONLY. Past weeks are not retrievable from any
free source, so every un-recorded week is permanently lost evidence. This script
stores the raw bytes exactly as received and never normalises, rewrites or
deletes anything.

Two-timestamp discipline:
  fetched_at_utc  = when WE knew it (recorded here, in the manifest and filename)
  event time      = lives inside the payload, untouched

Stdlib only. No third-party packages, ever.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# --- configuration -----------------------------------------------------------

# Verified live 2026-08-18: JSON 200 / 12,973 bytes / 96 events.
# nextweek, lastweek and thismonth variants all return 404 - this week is all
# there is. Source: research/06 s6.1 and research/10 s5.1.
SOURCES = [
    ("json", "https://nfs.faireconomy.media/ff_calendar_thisweek.json"),
    ("xml", "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"),
]

# A bare urllib request with no User-Agent has been observed returning HTTP 429.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QMX-calendar-recorder/1.0"

TIMEOUT_SECONDS = 45
RETRIES = 3
RETRY_BACKOFF_SECONDS = [20, 60]  # waits after attempt 1 and attempt 2

# Community-reported enforcement is ~2 downloads per 5 minutes across all
# formats. Two variants per run, spaced, twice a day, is well inside that.
GAP_BETWEEN_SOURCES_SECONDS = 8

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "calendar")
RAW_DIR = os.path.join(DATA_DIR, "raw")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.jsonl")
LOG_PATH = os.path.join(DATA_DIR, "recorder.log")


# --- helpers -----------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    """2026-08-18T09:30:12Z - the value stored in the manifest."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_utc(dt: datetime) -> str:
    """ISO 8601 basic format - colons are illegal in Windows filenames."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def log(message: str) -> None:
    line = f"{iso_utc(utc_now())} {message}"
    print(line)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def append_manifest(record: dict) -> None:
    """One JSON object per line. Append-only; existing lines are never touched."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")


def read_manifest() -> list:
    if not os.path.exists(MANIFEST_PATH):
        return []
    records = []
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue  # a corrupt line must never stop the recorder
    return records


def last_sha_for(url: str, records: list):
    """sha256 of the most recent successful snapshot of this url, or None."""
    for record in reversed(records):
        if record.get("url") == url and record.get("sha256"):
            return record["sha256"]
    return None


def fetch(url: str):
    """Return (http_status, body_bytes). Raises on final failure."""
    last_error = None
    for attempt in range(RETRIES):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return int(response.status), response.read()
        except urllib.error.HTTPError as error:
            last_error = error
            # 4xx other than 429 will not fix themselves; stop early.
            if error.code != 429 and error.code < 500:
                raise
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
        if attempt < len(RETRY_BACKOFF_SECONDS):
            wait = RETRY_BACKOFF_SECONDS[attempt]
            log(f"  retry in {wait}s after: {last_error}")
            time.sleep(wait)
    raise last_error


def unique_path(directory: str, base: str, extension: str) -> str:
    """Never overwrite: if the name is taken, add -1, -2, ..."""
    candidate = os.path.join(directory, f"{base}.{extension}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}-{counter}.{extension}")
        counter += 1
    return candidate


# --- main --------------------------------------------------------------------


def record_source(variant: str, url: str, known: list) -> bool:
    fetched_at = utc_now()
    record = {
        "fetched_at_utc": iso_utc(fetched_at),
        "url": url,
        "sha256": None,
        "bytes": 0,
        "http_status": None,
        "variant": variant,
    }

    try:
        status, body = fetch(url)
    except urllib.error.HTTPError as error:
        record["http_status"] = int(error.code)
        record["error"] = f"HTTP {error.code}"
        append_manifest(record)
        log(f"  {variant:<4} FAILED  HTTP {error.code}")
        return False
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
        append_manifest(record)
        log(f"  {variant:<4} FAILED  {record['error']}")
        return False

    digest = hashlib.sha256(body).hexdigest()
    record["sha256"] = digest
    record["bytes"] = len(body)
    record["http_status"] = status

    if digest == last_sha_for(url, known):
        record["unchanged"] = True
        append_manifest(record)
        log(f"  {variant:<4} unchanged  {len(body)} bytes  {digest[:12]}")
        return True

    directory = os.path.join(RAW_DIR, fetched_at.strftime("%Y"), fetched_at.strftime("%m"))
    os.makedirs(directory, exist_ok=True)
    path = unique_path(directory, f"fetch-{stamp_utc(fetched_at)}", variant)
    with open(path, "wb") as handle:  # raw bytes, byte for byte
        handle.write(body)

    record["unchanged"] = False
    record["path"] = os.path.relpath(path, BASE_DIR).replace("\\", "/")
    append_manifest(record)
    log(f"  {variant:<4} SAVED  {len(body)} bytes  {digest[:12]}  ->  {record['path']}")
    return True


def main() -> int:
    log("fetch start")
    known = read_manifest()
    successes = 0
    for index, (variant, url) in enumerate(SOURCES):
        if index:
            time.sleep(GAP_BETWEEN_SOURCES_SECONDS)  # be polite to the CDN
        if record_source(variant, url, known):
            successes += 1
            known = read_manifest()
    log(f"fetch done: {successes}/{len(SOURCES)} sources ok")
    return 0 if successes else 1


if __name__ == "__main__":
    sys.exit(main())
