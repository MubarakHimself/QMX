---
review: currency
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation, architecture-QMX-2026-08-19)
reviewer-method: live web search / PyPI JSON API cross-check against Stack table + factual claims
reviewed: 2026-08-19
---

# Currency & Reality-Check Review — ARCHITECTURE-SPINE.md

## Method

For every row in the Stack table, and for the named factual claims called out in scope
(cTrader rollover time, TA-Lib cp314 wheels, uv_build stability, poethepoet maintenance),
I queried live web search and/or PyPI's JSON API directly rather than relying on training
data. Where PyPI's JSON API response was large enough that a summarizing fetch looked
suspect (TA-Lib wheel list), I re-fetched with a narrower prompt and cross-checked against
an independent web search before accepting either answer as ground truth.

## Verdict

**Mostly current, with two version-pin errors and one un-flagged architectural risk.** Seven
of ten Stack rows check out exactly against live PyPI data; ruff's pin is three patch
releases stale relative to the table's own "verified 2026-08-19" claim, pyright's pin cites
a version the PyPI wrapper package does not yet serve, and the uv-workspace shared-venv
dependency-isolation gap (a real, documented uv behavior) is not addressed anywhere in AD-2/AD-3
even though it undercuts the "seven installable packages" framing.

## Findings

### CRITICAL
None. No claim in the Stack table or the named factual claims was found to be materially
false in a way that would break the plan if acted on as written.

### HIGH

**H1 — ruff pin is stale relative to its own "verified 2026-08-19" claim.**
Stack table row: `ruff | 0.16.0`. Live PyPI JSON (`info.version`) as of this review returns
**0.16.3**, released 2026-08-13 (0.16.1 on 2026-07-30, 0.16.2 on 2026-08-07, 0.16.3 on
2026-08-13). 0.16.0 itself shipped 2026-07-23. The spine's header claims the whole table was
"verified 2026-08-19" — six days after 0.16.3 shipped — so this isn't an aging-since-verification
problem, it's a table that undercounts by three patch releases on the date it claims to have
checked. Not fatal (ruff patch releases are additive rule/fix changes, not breaking), but it
means AD-3's "identical on every machine" claim is currently anchored to a version nobody
would get by running `uv add ruff` today. **Correct current value: ruff 0.16.3.**

### MEDIUM

**M1 — pyright pin cites a version the PyPI package doesn't yet serve.**
Stack table row: `pyright | 1.1.412 (strict)`. PyPI's JSON API (`info.version`) returns
**1.1.411**, released 2026-06-25 — the same value independently confirmed via a direct
PyPI page fetch and via web search. A secondary search surfaced a reference to 1.1.412 being
merged into basedpyright v1.39.10's changelog, and an earlier search pass reported an
npm-side `pyright` package at 1.1.412 "published 19 hours ago" — so 1.1.412 plausibly exists
upstream (VS Code/Pylance-side release cadence typically leads the PyPI CLI wrapper by hours
to a day or two). But `uv add pyright` / `pip install pyright` — what QMF's own toolchain
(AD-3: `poe types`) would actually invoke — currently installs 1.1.411, not 1.1.412. The
Stack table conflates the npm-facing release with the PyPI package the project depends on.
**Correct current value for what QMF will actually install: pyright 1.1.411** (1.1.412 may
land on PyPI within days, but wasn't there as of this review).

**M2 — uv workspace's shared-venv dependency isolation gap is not addressed by AD-2/AD-3.**
AD-2 frames the workspace as "seven installable packages." Live research (uv workspace
docs, GitHub issue discussion, and independent write-ups) confirms a known, documented
behavior: a uv workspace syncs all member packages into **one shared virtualenv**, so any
workspace member can `import` a package that only a *sibling* package declares as a
dependency — pyright strict and ruff will not flag this, because the import genuinely
resolves at type-check and lint time (it's present in the shared environment). The failure
only surfaces later, when a package is installed standalone outside the workspace (e.g. a
factory sandbox that installs only `qmf-indicators`, or a downstream consumer). This is a
real risk specifically for AD-2's "sandboxes forced to install the whole framework"
prevention goal and AD-6's zero-dependency-core guarantee for `qmf-core` — nothing in AD-3's
quality-toolchain rule (ruff + pyright strict + pytest) catches an accidental cross-package
import leak. Not a version-currency defect, but it is exactly the kind of "asserted, not
reality-checked" gap the review was scoped to catch, since the spine implicitly assumes
pyright-strict-workspace-wide gives per-package dependency isolation, and it does not.
Recommend an explicit mitigation line (e.g., periodic standalone-install smoke test per
package, already half-covered by AD-4 tier-3 "build all packages, clean-install smoke" —
worth cross-referencing explicitly).

### LOW

**L1 — poethepoet: confirmed actively maintained, but the Stack table doesn't pin a version.**
The task's premise ("poethepoet was flagged unconfirmed earlier") is resolved: live PyPI
history shows poethepoet is healthy and actively released — 0.48.0 (2026-07-05), 0.47.1
(2026-07-01), 0.47.0 (2026-06-27), 0.46.0 (2026-05-15), roughly monthly cadence through all
of 2026, most recently about six weeks before this spine's date. It is not at abandonment
risk. However, unlike every other Stack row, poethepoet's row reads `current (task runner)`
with no version number — every other tool has a specific pinned figure. For a document whose
whole point is version-pin discipline (AD-5's lockstep-versioning ethos), this row should
name **0.48.0** (or whatever is pinned in the actual lockfile) rather than the word "current."

**L2 — pandas 3.0 is a young major version (informational only, not an error).**
Pandas 3.0.0 shipped 2026-01-21, about seven months before this spine — a major version with
documented breaking changes vs. the 2.x series (pandas' own docs recommend upgrading to 2.3
cleanly first before jumping to 3.0). For QMF this is low-risk since the codebase is
greenfield with no legacy pandas 2.x code to migrate, but third-party libraries in the
ecosystem may lag 3.0 compatibility for a while yet. Worth a one-line awareness note if any
future sitting pulls in a pandas-adjacent dependency (e.g. a data-science-adjacent library)
that hasn't caught up. The pinned value itself, **3.0.5** (released 2026-07-22), is correct
and current.

## Confirmed correct (no action needed)

Checked directly against PyPI's JSON API and/or python.org release pages, all as of this
review:

| Stack row | Spine value | Confirmed live value | Status |
| --- | --- | --- | --- |
| CPython | 3.14.7 | 3.14.7 (released 2026-08-05, 7th maintenance release) | Match |
| uv | 0.12.5 | 0.12.5 (released 2026-08-14, PyPI `info.version`) | Match |
| uv_build | stable per uv 0.12.x | PyPI classifies `uv-build` as Development Status :: 5 - Production/Stable | Match |
| numpy | 2.5.2 | 2.5.2 (PyPI `info.version`), released 2026-08-09 | Match |
| pandas | 3.0.5 | 3.0.5 (PyPI `info.version`), released 2026-07-22 | Match |
| pyarrow | 25.0.1 | 25.0.1 (PyPI `info.version`), released ~2026-08-10 | Match |
| duckdb | 1.5.5 | 1.5.5 (PyPI `info.version`; DuckDB's own release post confirms it as the sixth 1.5-series patch) | Match |
| pytest | 9.1.1 | 9.1.1 (PyPI `info.version`), released 2026-06-19 | Match |
| TA-Lib | 0.7.1, cp314 wheels | 0.7.1 confirmed latest; cp314 wheels confirmed present for Windows, Linux (manylinux/musllinux), and macOS, uploaded 2026-07-16 — verified via a direct PyPI files-page fetch after an initial JSON-API fetch wrongly suggested no cp314 wheels existed (that answer was a truncation artifact from summarizing a very large wheel-list payload, not a real absence) | Match — claim is true |
| cTrader 17:00 America/New_York daily-bar rollover | stated as "verified = cTrader's own boundary" | Corroborated independently via cTrader community forum discussion (17:00 EST/EDT close = 21:00–22:00 UTC depending on DST). The project's own `ctrader-time-research.md` already honestly flags this as sourced from a 2013 official Spotware announcement + 2019 staff reaffirmation on community forums, not an Open-API-specific primary doc page — that caveat is accurate and appropriately humble; no upgrade needed | Match, already well-caveated by the project itself |

Also spot-checked: GitHub's `actions/setup-python` and `astral-sh/setup-uv` both support
Python 3.14 (including free-threaded `3.14t`) on `windows-latest` and `ubuntu-latest` matrix
targets, substantiating AD-1's CI-gated tier-1 OS claim — though I did not pin this to the
exact `setup-python@v6` tag cited in `.memlog.md` (that memlog line is a working note, not
part of the spine itself, so it's out of strict scope here).

## Notes on verification methodology

One transient false lead is worth recording: a direct fetch of `pypi.org/pypi/TA-Lib/json`
initially returned "no cp314 wheels, only 3.9–3.13" — this was wrong, caused by the fetch
tool's summarizer truncating a very long wheel-file list before reaching the cp314 entries.
A second, narrower fetch of the PyPI files page and a corroborating web search both confirmed
cp314 wheels do exist. Flagging this because it's a concrete example of why single-pass API
fetches on packages with large release payloads (TA-Lib ships ~40+ wheel files per version)
need a second, differently-scoped check before being trusted — the same caution likely applies
to any future currency review of a package with a similarly large wheel matrix (e.g. duckdb,
pyarrow).
