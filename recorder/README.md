# recorder

Standalone, stdlib-only recorder for the FairEconomy/ForexFactory economic calendar
(`https://nfs.faireconomy.media/ff_calendar_thisweek.{json,xml}`). The feed serves the
current week only — an un-recorded week is permanently lost. No project imports, no pip
dependencies; do not couple anything here to platform code.

    fetch_calendar.py            fetch + append-only store (raw bytes, never normalised)
    status.py                    operator status screen (read-only)
    data/calendar/raw/YYYY/MM/   fetch-<UTC-timestamp>.{json,xml} snapshots (gitignored)
    data/calendar/manifest.jsonl one line per fetch: fetched_at_utc, url, sha256, bytes, http_status
    data/calendar/recorder.log   run log

Check status: `py -3 status.py`. Fetch now: `py -3 fetch_calendar.py`.
Scheduled task: `QMX-Calendar-Recorder` (daily 06:00, repeats every 12h → 06:00 + 18:00 local).
All stored timestamps are UTC. Identical payloads are deduped by sha256, not rewritten.
Feed is rate-limited (~2 downloads / 5 min across all formats) — do not poll faster.
