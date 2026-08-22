# qmf-calendar-forex

The first market-hours calendar extension. Off-roster, on its own SemVer ladder, with tzdata pinned.

`qmf-calendar-forex` imports as `qmf.calendar_forex` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). As an off-roster extension it rides its own SemVer ladder, independent of roster lockstep; a tzdata pin change is at minimum a minor bump.

## Status

Story 4.1 — package scaffold with import-time tzdb verification. At import the
package forces `TZPATH` to its pinned `tzdata==2025.2` (IANA `2025b`), calls
`qmf.core.verify_tzdb_pin`, and on match exposes a ready `CalendarIdentity`
(`forex-17NY` / `v1` / verified tzdata version) for downstream fingerprints. On
mismatch it stores an `unavailable dependency` TypedRefusal and does not become
a usable provider. The CT-02 rollover / session-schedule surface arrives in later
stories. Build, lint, type-check, and test it through the workspace `poe` tasks —
never in isolation.

## SemVer and the tzdata pin

- Package version lives in this extension's `pyproject.toml` (`0.1.0` today).
- Runtime pin: `tzdata==2025.2` (IANA tzdb `2025b`). Changing that pin is **at
  least a minor** SemVer bump on **this** ladder; do not bump unless the pin
  actually changes.
