# qmf-calendar-forex

The first market-hours calendar extension. Off-roster, on its own SemVer ladder, with tzdata pinned.

`qmf-calendar-forex` imports as `qmf.calendar_forex` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). As an off-roster extension it rides its own SemVer ladder, independent of roster lockstep; a tzdata pin change is at minimum a minor bump.

## Status

Story 4.3 — explicit composition-root registration, identity participation, and
authority-boundary conformance on top of the Story 4.1/4.2 provider. At import the
package forces `TZPATH` to its pinned `tzdata==2025.2` (IANA `2025b`), calls
`qmf.core.verify_tzdb_pin`, and on match exposes a ready `CalendarIdentity`
(`forex-17NY` / `v1` / verified tzdata version) plus `Forex17NYCalendar` via
`get_provider()`. Applications wire the calendar by calling the named
`register_forex_17ny()` surface at the composition root — never by ambient package
scanning, entry points, or `pkgutil`. Distribution identity + version ride into
downstream fingerprints (via `qmf.core.fingerprint`) alongside the rule set and
IANA tzdata; binding (venues/accounts) is separate and never enters identity. A
tzdata pin change yields a new `CalendarIdentity`; `describe_tzdata_pin_lineage`
describes the supersedes edge for the composition root to record (no
`qmf-registry` dependency). Shared nouns stay in `qmf-core` (FM-5). Build, lint,
type-check, and test it through the workspace `poe` tasks — never in isolation.

## Composition-root registration

```python
from qmf.calendar_forex import CalendarBinding, register_forex_17ny

registration = register_forex_17ny(
    binding=CalendarBinding(venue_ids=("venue-a",), account_ids=("acct-1",)),
)
# registration.fp1_identity() / .artifact_fingerprint() — binding excluded
```

Reference usage: `examples/registration_usage.py`.

## SemVer and the tzdata pin

- Package version lives in this extension's `pyproject.toml` (`0.1.0` today) and
  as `qmf.calendar_forex.__version__` / `DISTRIBUTION_NAME`.
- Per AD-2, distribution identity + version are identity fields of every artifact
  this extension produces (downstream fingerprints via `register_forex_17ny`).
- Runtime pin: `tzdata==2025.2` (IANA tzdb `2025b`). Changing that pin is **at
  least a minor** SemVer bump on **this** ladder; do not bump unless the pin
  actually changes.
