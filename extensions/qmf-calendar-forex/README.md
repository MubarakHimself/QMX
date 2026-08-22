# qmf-calendar-forex

The first market-hours calendar extension. Off-roster, on its own SemVer ladder, with tzdata pinned.

`qmf-calendar-forex` imports as `qmf.calendar_forex` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). As an off-roster extension it rides its own SemVer ladder, independent of roster lockstep; a tzdata pin change is at minimum a minor bump.

## Status

Story 4.2 — forex-17NY CT-02 market-hours calendar provider on top of the Story 4.1
scaffold. At import the package forces `TZPATH` to its pinned `tzdata==2025.2`
(IANA `2025b`), calls `qmf.core.verify_tzdb_pin`, and on match exposes a ready
`CalendarIdentity` (`forex-17NY` / `v1` / verified tzdata version) plus
`Forex17NYCalendar` via `get_provider()`. The provider applies the
`registry:forex_rollover` rule (17:00 America/New_York), returns `TradingDate`
through `qmf.core.TradingDate.try_create`, models weekend gaps and the pinned
holiday set as `SessionWindow` data, refuses day-boundary and news questions as
out of authority, and fingerprints only through `qmf.core.fingerprint`. On tzdb
mismatch it stores an `unavailable dependency` TypedRefusal and does not become
a usable provider. Build, lint, type-check, and test it through the workspace
`poe` tasks — never in isolation.

## SemVer and the tzdata pin

- Package version lives in this extension's `pyproject.toml` (`0.1.0` today).
- Runtime pin: `tzdata==2025.2` (IANA tzdb `2025b`). Changing that pin is **at
  least a minor** SemVer bump on **this** ladder; do not bump unless the pin
  actually changes.
