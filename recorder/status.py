#!/usr/bin/env python3
"""Status screen for the QMX economic-calendar recorder.

Answers, in one screen: is it still recording, how much have we got, is the
scheduled job alive, and what high-impact events are coming.

Stdlib only. Read-only - this script never writes to the archive.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "calendar")
RAW_DIR = os.path.join(DATA_DIR, "raw")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.jsonl")

TASK_NAMES = [
    "QMX-Calendar-Recorder",
    "QMX-Calendar-Recorder-AM",
    "QMX-Calendar-Recorder-PM",
]

WIDTH = 78
MAX_EVENT_ROWS = 14

# --- terminal capability ------------------------------------------------------

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass


def _unicode_ok() -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "─│┌".encode(encoding)
        return True
    except Exception:  # noqa: BLE001
        return False


def _colour_ok() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:  # noqa: BLE001
            return False
    return True


UNICODE = _unicode_ok()
COLOUR = _colour_ok()

BOX = {
    True: dict(h="─", v="│", tl="┌", tr="┐", bl="└",
               br="┘", lt="├", rt="┤"),
    False: dict(h="-", v="|", tl="+", tr="+", bl="+", br="+", lt="+", rt="+"),
}[UNICODE]


def c(text: str, code: str) -> str:
    return "\x1b[%sm%s\x1b[0m" % (code, text) if COLOUR else text


DIM, BOLD, GREEN, YELLOW, RED, CYAN = "2", "1", "32", "33", "31", "36"


def _visible_len(text: str) -> int:
    out, i = 0, 0
    while i < len(text):
        if text[i] == "\x1b":
            while i < len(text) and text[i] != "m":
                i += 1
            i += 1
            continue
        out += 1
        i += 1
    return out


def top(title: str) -> None:
    label = " %s " % title
    print(BOX["tl"] + label + BOX["h"] * (WIDTH - 2 - len(label)) + BOX["tr"])


def rule() -> None:
    print(BOX["lt"] + BOX["h"] * (WIDTH - 2) + BOX["rt"])


def bottom() -> None:
    print(BOX["bl"] + BOX["h"] * (WIDTH - 2) + BOX["br"])


def row(text: str = "") -> None:
    pad = WIDTH - 4 - _visible_len(text)
    print("%s %s%s %s" % (BOX["v"], text, " " * max(pad, 0), BOX["v"]))


def field(label: str, value: str) -> None:
    row("%s %s" % (c(label.ljust(18), DIM), value))


# --- data ---------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def human_age(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return "%ds ago" % seconds
    if seconds < 3600:
        return "%dm ago" % (seconds // 60)
    if seconds < 86400:
        return "%dh %dm ago" % (seconds // 3600, (seconds % 3600) // 60)
    return "%dd %dh ago" % (seconds // 86400, (seconds % 86400) // 3600)


def human_bytes(count: int) -> str:
    value = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return "%.0f %s" % (value, unit) if unit == "B" else "%.1f %s" % (value, unit)
        value /= 1024
    return "%d B" % count


def read_manifest() -> list:
    if not os.path.exists(MANIFEST_PATH):
        return []
    records = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except ValueError:
                    pass
    return records


def snapshot_files() -> list:
    found = []
    for root, _dirs, files in os.walk(RAW_DIR):
        for name in files:
            found.append(os.path.join(root, name))
    found.sort()
    return found


def newest_json_snapshot(files: list):
    candidates = [p for p in files if p.lower().endswith(".json")]
    return candidates[-1] if candidates else None


def query_task(name: str):
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", name, "/fo", "LIST", "/v"],
            capture_output=True, text=True, timeout=25,
        )
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0:
        return None
    info = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            info.setdefault(key.strip(), value.strip())
    return info


# --- sections -----------------------------------------------------------------


def section_archive(records: list, files: list) -> None:
    saved = [r for r in records if r.get("path")]
    unchanged = [r for r in records if r.get("unchanged")]
    failed = [r for r in records if r.get("error")]
    total_bytes = sum(os.path.getsize(p) for p in files) if files else 0

    last = records[-1] if records else None
    if last:
        when = parse_utc(last.get("fetched_at_utc", ""))
        if when:
            age_seconds = (utc_now() - when).total_seconds()
            colour = GREEN if age_seconds < 26 * 3600 else (YELLOW if age_seconds < 50 * 3600 else RED)
            field("Last fetch", "%s  %s" % (last["fetched_at_utc"], c("(" + human_age(age_seconds) + ")", colour)))
        else:
            field("Last fetch", str(last.get("fetched_at_utc")))
    else:
        field("Last fetch", c("never - archive is empty", RED))

    field("Snapshots on disk", "%d files, %s" % (len(files), human_bytes(total_bytes)))
    field("Manifest lines", "%d  (%s saved, %s unchanged, %s failed)"
          % (len(records), len(saved), len(unchanged),
             c(str(len(failed)), RED) if failed else "0"))

    first = records[0] if records else None
    if first:
        field("Recording since", str(first.get("fetched_at_utc")))


def section_schedule() -> None:
    found = False
    for name in TASK_NAMES:
        info = query_task(name)
        if not info:
            continue
        found = True
        status = info.get("Status", "?")
        next_run = info.get("Next Run Time", "?")
        last_run = info.get("Last Run Time", "?")
        last_result = info.get("Last Result", "?")
        ok = status.lower() in ("ready", "running")
        field("Task", "%s  %s" % (name, c(status, GREEN if ok else YELLOW)))
        field("  next run", next_run)
        field("  last run", "%s  (result %s)" % (last_run, last_result))
    if not found:
        field("Task", c("NOT FOUND - nothing is recording automatically", RED))


def section_events(path) -> None:
    if not path:
        row(c("No snapshot to read yet.", DIM))
        return
    try:
        with open(path, "rb") as handle:
            events = json.loads(handle.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001
        row(c("Could not parse %s: %s" % (os.path.basename(path), error), RED))
        return

    now = utc_now()
    upcoming = []
    for event in events:
        if str(event.get("impact", "")).lower() != "high":
            continue
        when = None
        try:
            when = datetime.fromisoformat(str(event.get("date", ""))).astimezone(timezone.utc)
        except Exception:  # noqa: BLE001
            pass
        if when and when >= now:
            upcoming.append((when, event))
    upcoming.sort(key=lambda pair: pair[0])

    high_total = sum(1 for e in events if str(e.get("impact", "")).lower() == "high")
    row("%s  %s"
        % (c(os.path.basename(path).ljust(30), DIM),
           c("%d events, %d high-impact, %d still ahead" % (len(events), high_total, len(upcoming)), DIM)))
    row()
    row(c("%-17s %-4s %-6s %s" % ("TIME (UTC)", "CCY", "IMPACT", "EVENT"), BOLD))

    if not upcoming:
        row(c("No high-impact events left in this week's feed.", DIM))
        return

    for when, event in upcoming[:MAX_EVENT_ROWS]:
        title = str(event.get("title", ""))[:47]
        row("%-17s %-4s %-6s %s"
            % (when.strftime("%Y-%m-%d %H:%M"),
               str(event.get("country", ""))[:4],
               c("HIGH", RED),
               title))
    if len(upcoming) > MAX_EVENT_ROWS:
        row(c("... and %d more" % (len(upcoming) - MAX_EVENT_ROWS), DIM))


def main() -> int:
    records = read_manifest()
    files = snapshot_files()

    print()
    top(c("QMX CALENDAR RECORDER", BOLD))
    row(c("FairEconomy / ForexFactory weekly feed - this-week-only, raw archive", DIM))
    rule()
    section_archive(records, files)
    rule()
    section_schedule()
    rule()
    section_events(newest_json_snapshot(files))
    bottom()
    print(c("  archive: %s" % DATA_DIR, DIM))
    print(c("  fetch now: py -3 \"%s\"" % os.path.join(BASE_DIR, "fetch_calendar.py"), DIM))
    print()
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
