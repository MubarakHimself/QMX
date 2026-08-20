---
review: currency
target: ARCHITECTURE-SPINE.md — AD-23 and the Stack table rows for TA-Lib and duckdb (QMF V1 Foundation, architecture-QMX-2026-08-19)
reviewer-method: live web search / official docs / GitHub source / PyPI JSON API cross-check against the AD-23 TA-Lib pin and streaming claim, and the AD-19/Stack duckdb pin
reviewed: 2026-08-20
---

# Currency & Reality-Check Review 3 — AD-23, Stack (TA-Lib, duckdb) — ARCHITECTURE-SPINE.md

## Scope

This is a follow-up to `review-currency.md` and `review-currency-2.md`. This pass
targets the newest increment: **AD-23** ("Canonical arithmetic: TA-Lib pinned,
upgrades gated") and the **Stack** table rows for `duckdb` and `TA-Lib (C library +
Python wrapper)`. Five specific claims were checked against the live web:

1. TA-Lib C library current version = 0.7.1; Python wrapper current version = 0.7.1
   with cp314 wheels for Windows + Linux.
2. TA-Lib's licence(s) — C library and Python wrapper — against AD-6's tiering
   (permissive MIT/BSD/Apache/PSF freely allowed; LGPL only unmodified/separately
   installed; GPL/AGPL prohibited).
3. Whether `talib.stream` is a true incremental/stateful streaming API, or a
   compute-latest-value convenience that still recomputes from the full window —
   this determines whether AD-23's "streaming implementations are QMX-owned where
   TA-Lib lacks a streaming form" claim is accurate.
4. Whether duckdb 1.5.5 is still current/latest stable, and whether the DuckDB v2.0
   storage-format break (AD-19) has shipped or is still preview.
5. Any signal TA-Lib is unmaintained/deprecated, or that a successor is now the
   industry standard.

## Verdict

**Every checked claim in AD-23 and the two Stack rows holds up as stated — version
pins, both licences, and the streaming characterization are all accurate as of
2026-08-20, and nothing has shipped or surfaced that supersedes them.** No claim
found materially false. One near-miss caught mid-review: an early automated fetch of
the PyPI JSON API mis-summarized cp314 wheel availability as absent; a direct
`curl` + manual JSON parse of the same endpoint corrected this — the wheels exist.
That correction is recorded below as a methodology note, not a spine finding.

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM
None — all five checks confirm the spine text as written. Findings below are
corroborating detail, not corrections.

### Verification detail

**F1 — TA-Lib C library version, confirmed 0.7.1, current.**
`github.com/TA-Lib/ta-lib/releases`: v0.7.1 released **2026-07-03** is the latest
release. Prior releases: v0.6.4 (2025-01-11), v0.6.3, v0.6.2, v0.6.1 (all Dec
2024–Jan 2025), then a long gap back to v0.4.0 (2007). AD-23's C-library pin (0.7.1)
matches the current release exactly.
Source: https://github.com/TA-Lib/ta-lib/releases

**F2 — TA-Lib Python wrapper version, confirmed 0.7.1, current, with cp314 wheels
for both Windows and Linux.**
PyPI (`pypi.org/project/TA-Lib/`) lists 0.7.1 (released 2026-07-16) as current.
Verified directly against the PyPI JSON API (`pypi.org/pypi/TA-Lib/json`, fetched via
`curl` and parsed with Python — not the summarizing WebFetch, see methodology note)
that build 0.7.1 ships 55 files including full cp314 coverage:
- Windows: `cp314-cp314-win32`, `cp314-cp314-win_amd64`, `cp314-cp314-win_arm64`
- Linux: `cp314-cp314-manylinux2014_x86_64...`, `cp314-cp314-manylinux2014_aarch64...`,
  `cp314-cp314-musllinux_1_2_x86_64`, `cp314-cp314-musllinux_1_2_aarch64`
- (also macOS x86_64/arm64, and full cp39–cp314 matrices on every platform)
Trove classifiers on the release confirm `Programming Language :: Python :: 3.14`
alongside 3.9–3.13. AD-23's Python-wrapper pin (0.7.1) and the implied cp314/Windows+
Linux availability are both accurate.
Sources: https://pypi.org/project/TA-Lib/ ,
https://pypi.org/pypi/TA-Lib/json

**F3 — Both licences are permissive; the pin is licence-legal under AD-6.**
- **C library** (`TA-Lib/ta-lib`, `LICENSE` at repo root, fetched raw from GitHub):
  **BSD 3-Clause ("New"/"Modified" BSD)** — standard three-clause text (copyright
  notice retention, binary-form reproduction, no-endorsement clause), "AS IS"
  disclaimer. Source:
  https://raw.githubusercontent.com/TA-Lib/ta-lib/main/LICENSE
- **Python wrapper** (`TA-Lib/ta-lib-python`, `LICENSE` at repo root, fetched raw
  from GitHub): **BSD 2-Clause ("Simplified"/"FreeBSD") License** — two-clause text
  (copyright notice retention in source and binary forms only, no endorsement
  clause), "AS IS" disclaimer. Source:
  https://raw.githubusercontent.com/TA-Lib/ta-lib-python/master/LICENSE
- The wrapper's `pyproject.toml` declares the licence via the modern PEP 639
  `license-files = ["LICENSE"]` field (pointing at the same BSD-2-Clause file) rather
  than a legacy `License ::` PyPI trove classifier or SPDX `license` string — which is
  why the PyPI JSON API's `info.license` / `info.license_expression` fields both read
  `None`. That is a metadata-format artifact, not an unlicensed/proprietary signal;
  the actual licence text is unambiguous BSD-2-Clause.
  Source: https://raw.githubusercontent.com/TA-Lib/ta-lib-python/master/pyproject.toml
- **Verdict against AD-6:** both BSD-3-Clause and BSD-2-Clause are enumerated in
  AD-6's permissive tier ("MIT/BSD/Apache/PSF") and are **freely allowed**, no
  LGPL/GPL/AGPL complication, no separate-installation requirement triggered. The
  pin is licence-legal.

**F4 — `talib.stream` is NOT a true incremental/stateful API; it is a
compute-latest-value convenience that recomputes from the full window every call.
AD-23's characterization is accurate.**
Checked three independent sources:
- The `ta-lib-python` README's own description: *"An experimental Streaming API was
  added that allows users to compute the latest value of an indicator. This can be
  faster than using the Function API, for example in an application that receives
  streaming data, and wants to know just the most recent updated indicator value."*
  This phrasing itself describes a "compute latest value" convenience, not a
  stateful incremental primitive — nothing in the README claims cross-call state
  retention.
- `talib/stream.py` (raw source, `TA-Lib/ta-lib-python@master`): each `stream.*`
  function is a thin dynamic binding —
  `globals()[func_name] = getattr(_ta_lib, "stream_%s" % func_name)` — delegating
  straight to compiled `stream_<FUNC>` entry points with no Python-level state object.
- `talib/_stream.pxi` (raw Cython source, same repo): the generated `stream_<FUNC>`
  implementations take the **full input array** on every call and invoke the
  underlying `TA_<FUNC>` C function over `0..length-1`, then return only the last
  computed scalar(s) — e.g. the `stream_ACCBANDS` body calls
  `lib.TA_ACCBANDS(<int>(length)-1, <int>(length)-1, high_data, low_data, close_data,
  ...)` and returns `outrealupperband, outrealmiddleband, outreallowerband`. There is
  no persisted internal state between invocations; each call is a fresh full-window
  computation that happens to only surface the tail value.
- Corroborating signal: a separate, unrelated third-party project (`nardew/talipp`,
  "incremental technical analysis library for python") exists specifically to offer
  genuine O(1)-per-tick incremental indicator updates — its existence as a distinct
  library is itself evidence that TA-Lib's own stream module does not already provide
  that property; if it did, a separate incremental library would have little reason
  to exist.
- **Conclusion:** AD-23's claim that "streaming implementations are QMX-owned...
  where TA-Lib lacks a streaming form" is factually accurate. `talib.stream` is
  useful as a convenience (and possibly as a cross-check oracle for QMX's own
  incremental implementations, per AD-22's equality law) but is not itself a
  stateful streaming primitive QMX could adopt in place of building one.
Sources: https://github.com/TA-Lib/ta-lib-python ,
https://raw.githubusercontent.com/TA-Lib/ta-lib-python/master/talib/stream.py ,
https://github.com/TA-Lib/ta-lib-python/blob/master/talib/_stream.pxi ,
https://github.com/nardew/talipp

**F5 — duckdb 1.5.5 confirmed current/latest stable; DuckDB v2.0's storage-format
break is still preview, not shipped, matching AD-19's exact wording.**
- `github.com/duckdb/duckdb/releases`: **v1.5.5**, released **2026-07-22**, is the
  latest stable release (bugfix release on the 1.5.x line; 1.4.5 also received a
  parallel bugfix release the same window). No v2.0 tag exists yet.
- `duckdb.org/2026/08/17/duckdb-20-highlights` ("A Preview of DuckDB v2.0"),
  published **2026-08-17** — matching AD-19's parenthetical "(previewed
  2026-08-17)" exactly — confirms v2.0 has **not shipped**: *"DuckDB v2.0 is coming
  this fall"* (fall 2026), explicitly framed as a preview with "some details may
  still shift before the release." It does ship "a new SQL parser, a new default
  storage format, a reworked C API, and a small number of carefully chosen breaking
  changes" — confirming AD-19's characterization of it as a coming storage-format
  break, correctly treated as not-yet-arrived.
- AD-19's stance (analytics engine only, rebuildable views, "engine majors pinned
  per release") is unaffected — the pin (1.5.5) and the deferred-break framing both
  hold.
Sources: https://github.com/duckdb/duckdb/releases ,
https://duckdb.org/2026/08/17/duckdb-20-highlights ,
https://www.infoworld.com/article/4210635/duckdb-2-0-coming-this-fall-with-client-server-mode.html

**F6 — No unmaintained/deprecated signal for TA-Lib; no successor has become the
industry standard.**
Web search turned up no deprecation notice, no maintenance-abandonment signal, no
"use X instead" consensus. TA-Lib shipped a substantive 0.7.1 release in July 2026
that fixed real correctness bugs (period=1 handling in MACD/MACDFIX/TRIX/ULTOSC —
AD-23's cited precedent is itself confirmed accurate: v0.7.1's release notes state a
period of 1 now consistently means "no smoothing," fixing previously "misaligned
output" for signalPeriod=1 and period=1 cases). Some adjacent/alternative projects
exist (e.g. `talipp` for incremental computation, a Medium post pitching a "faster
alternative to TA-Lib" for raw throughput) but none carries industry-standard
displacement signal — TA-Lib remains the de facto reference implementation these
alternatives position themselves against, which is consistent with AD-23's framing
of TA-Lib as the "canonical arithmetic reference."
Sources: https://github.com/TA-Lib/ta-lib/releases ,
https://pypi.org/project/TA-Lib/ ,
https://ta-lib.org/wrappers/

### Methodology note (not a spine finding)

One WebFetch call against `pypi.org/pypi/TA-Lib/json` (a ~350KB JSON payload)
returned a summarized answer claiming "no CP314 wheels are available" — directly
contradicted by a second WebFetch against the PyPI HTML page (which correctly listed
cp314 wheels) and later disproved conclusively by fetching the same JSON endpoint
with `curl` and parsing it directly in Python (see F2: 55 files, full cp314 matrix
present). The summarizing pass over a large JSON blob produced a false negative.
Recorded here so any future currency-review pass on this file trusts raw
parses/`curl` over WebFetch's summarized output when checking wheel/build-matrix
claims from large PyPI JSON payloads.

## Summary Table

| Claim (spine text) | Verified value | Status |
| --- | --- | --- |
| TA-Lib C library 0.7.1, current | 0.7.1 released 2026-07-03, is latest | Confirmed |
| TA-Lib Python wrapper 0.7.1, current, cp314 Win+Linux | 0.7.1 released 2026-07-16; cp314 wheels present for win32/win_amd64/win_arm64 + manylinux/musllinux x86_64/aarch64 | Confirmed |
| TA-Lib C licence permissive under AD-6 | BSD 3-Clause | Confirmed, freely allowed |
| TA-Lib Python wrapper licence permissive under AD-6 | BSD 2-Clause | Confirmed, freely allowed |
| "Streaming implementations are QMX-owned where TA-Lib lacks a streaming form" | `talib.stream` recomputes from full window per call, no cross-call state; not true incremental | Confirmed accurate |
| duckdb 1.5.5 current/latest stable | 1.5.5 released 2026-07-22, latest | Confirmed |
| DuckDB v2.0 storage break "previewed 2026-08-17" | Preview blog dated 2026-08-17; release targeted "fall 2026," not shipped | Confirmed accurate |
| TA-Lib 0.7.1 fixed MACD/MACDFIX/TRIX/ULTOSC period=1 outputs (AD-23 precedent) | Confirmed by v0.7.1 release notes | Confirmed |
| TA-Lib unmaintained / superseded by industry-standard successor | No such signal found | No, remains reference implementation |
