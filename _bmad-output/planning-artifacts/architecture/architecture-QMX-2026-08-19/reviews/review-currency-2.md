---
review: currency
target: ARCHITECTURE-SPINE.md, AD-15 through AD-21 only (QMF V1 Foundation, architecture-QMX-2026-08-19)
reviewer-method: live web search / official docs cross-check against the named data-stack claims (Parquet, DuckDB, SQLite, JSONL) and the AD-15 sync-first/async-at-edge stance
reviewed: 2026-08-20
---

# Currency & Reality-Check Review 2 — AD-15..AD-21 — ARCHITECTURE-SPINE.md

## Scope

This is a follow-up to `review-currency.md` (which covered AD-1..AD-14 and the Stack
table as a whole). This pass targets only the sections added 2026-08-20:
AD-15 (concurrency stance), AD-16 (registry/lineage), AD-17 (multiplicity), AD-18
(promotion skeleton), AD-19 (data rooms/stores), AD-20 (migrations/backup), AD-21
(splits/journal/adapters). Specific verification targets given by the task:

1. Parquet + DuckDB + SQLite + JSONL as a serverless local data stack — is DuckDB's
   native Parquet read still current, and is DuckDB itself current?
2. JSONL append files with rebuildable indexes as a lineage store at small-operation
   scale — sound current pattern?
3. Whether AD-15's sync-first/async-at-edge stance conflicts with how this named
   stack is actually used from Python today.

## Verdict

**The stack claims hold up as stated, and AD-15's sync/async split matches how these
libraries actually behave in Python today — but the Stack table's DuckDB pin (1.5.5)
is about to be overtaken by a breaking major release (v2.0, previewed 3 days before
this addendum's own date) that AD-20's migration discipline will need to absorb, and
that release's headline "asynchronous I/O" feature deserves one guardrail sentence so
it doesn't quietly creep into qmf-data later.** No claim found materially false.

## Findings

### CRITICAL
None.

### HIGH

**H1 — DuckDB v2.0 ("Cyanoptera") is imminent and unflagged; it is exactly the kind
of event AD-20 exists for.** Live search confirms: current DuckDB release is 1.5.5
(matches the Stack table, unchanged since `review-currency.md`), but DuckDB posted
"A Preview of DuckDB v2.0" on **2026-08-17** — three days before this addendum's own
`updated: 2026-08-20` date — announcing a release "this fall" with **a new default
storage format, a reworked C API, a new SQL parser, and "a small number of carefully
chosen breaking changes."** Prior DuckDB storage-format transitions have required an
EXPORT DATABASE (old) → IMPORT DATABASE (new) migration path; there is no guarantee
of in-place upward compatibility. AD-20 already mandates preflight → backup → dry-run
→ migrate → verify for exactly this scenario, so the *design* is sound and needs no
change — but nothing in the Stack table or AD-19/AD-20 text flags that the named
engine has a breaking major version landing within the document's own planning
horizon. Recommend a one-line note pinning "stay on 1.5.x through V1; v2.0 migration
is a deliberate, tested, AD-20-governed event, not an auto-upgrade."
Sources: https://duckdb.org/2026/08/17/duckdb-20-highlights ,
https://www.infoworld.com/article/4210635/duckdb-2-0-coming-this-fall-with-client-server-mode.html

### MEDIUM

**M1 — DuckDB Python remains fully synchronous today; v2.0's "async I/O" is an
engine-internal claim, not (yet) a documented async Python client surface.** Confirmed
live: DuckDB's native Python API has no built-in async support now — community bridges
(`aioduckdb`, `pyduckdb`) exist only as thread-pool wrappers (`asyncio.to_thread` /
a dedicated worker thread), not true async I/O. This means AD-15's "async APIs exist
only at the venue network edge, never in core or the libraries" is **currently
accurate** for how `qmf-data` would call DuckDB — a plain, blocking call, fully
consistent with the "application owns all concurrency" framing. DuckDB v2.0's
announced "asynchronous I/O" is described as decoupling I/O from query execution for
network-attached storage, not as a new async Python API — but the wording is close
enough to AD-15's boundary that a later sitting could mistake it for "DuckDB now hands
us async for free." Worth one sentence in AD-19 or AD-20 reserving the call: if/when
qmf-data adopts DuckDB v2.0, its Python call surface stays synchronous under AD-15
regardless of what the engine does internally.

**M2 — cTrader's Open API Python SDK is confirmed async via Twisted's reactor, not
asyncio — AD-15's venue-edge carve-out is correctly placed, but names no runtime.**
Live check confirms `ctrader-open-api` / OpenApiPy (current on PyPI, MIT, actively
maintained) is asynchronous specifically through **Twisted** deferreds and
`reactor.run()`, not Python's stdlib `asyncio`. AD-15's rule ("async APIs exist only
at the venue network edge") is validated as fitting the actual current venue tech —
but running a Twisted reactor alongside any asyncio-based code elsewhere in the same
process (e.g. if a future sitting picks asyncio for something else at the edge) needs
an explicit bridge (Twisted ships an asyncio-reactor installer for this). Not a defect
— the venue sitting is explicitly deferred (GAP-0035..0038) — but the spine's current
wording ("async APIs," unqualified) should not be read as "any async runtime is
interchangeable"; Twisted is the one actually in play.
Sources: https://pypi.org/project/ctrader_open_api/ ,
https://spotware.github.io/OpenApiPy/

### LOW

**L1 — SQLite's WAL concurrency model is an exact, current match for AD-15's
"one-writer-per-stream, unlimited readers" stance and AD-19's use of SQLite for
transactional metadata.** Confirmed live and unchanged: WAL mode gives unlimited
simultaneous readers and exactly one writer at a time, with readers never blocking
the writer and vice versa — this is SQLite's long-stable default behavior, not
something that has drifted. No correction needed; noting only that SQLite also offers
an opt-in "BEGIN CONCURRENT" multi-writer mode the spine doesn't use and doesn't need
— confirming the spine isn't relying on a default that has since changed underneath
it (it hasn't).

**L2 — DuckDB's native Parquet support and "no database server" framing both check
out current.** `read_parquet()` / bare-`.parquet` querying, projection pushdown,
filter pushdown, and zonemap-based row-group skipping are all confirmed current
DuckDB behavior (docs current as of this review). DuckDB v2.0's new optional
client/server "Quack protocol" mode is additive, not a replacement for embedded mode
— so AD-19's "no database server" stays true by construction even after a future
v2.0 upgrade, not by omission.

### JSONL lineage store — assessed, not a version claim
JSONL is a file-format convention, not a versioned dependency, so there is no
"staleness" axis to check the way there is for a pinned package. The pattern AD-16
describes — append-only JSONL edge records + rebuildable local indexes, no database
server — mirrors the standard event-sourcing / audit-log append-log pattern and is a
sound, current fit at the small-operation scale this spine targets (solo operator,
~40-bot node ceiling per AD-13). No live-web currency concern applies here; this is a
design-soundness judgment, not a fact-check, and it holds.

## Confirmed correct (no action needed)

| Claim | Confirmed |
| --- | --- |
| DuckDB 1.5.5 is current released version | Match — last published 2026-07-21, unchanged since `review-currency.md` |
| DuckDB reads Parquet natively (`read_parquet`, pushdown, zonemaps) | Match — current DuckDB docs |
| DuckDB Python client has no native async; async requires thread-bridging wrappers | Match — confirmed via DuckDB GitHub discussion #3560/#3559 and current wrapper packages |
| Python stdlib `sqlite3` has no native async; blocking by design | Match — confirmed, `aiosqlite` bridges via threading |
| SQLite WAL: unlimited readers, single writer, non-blocking both ways | Match — sqlite.org/wal.html, unchanged core semantics |
| `ctrader_open_api` / OpenApiPy is async via Twisted, not asyncio | Match — confirmed on PyPI and Spotware's own SDK docs |
| DuckDB and SQLite both remain embedded/serverless in their current released forms | Match |

## Notes on verification methodology

Searched DuckDB's own 2026-08-17 v2.0 preview post directly (not just secondary
summaries) since it postdates this addendum's stated `2026-08-20` update and could
plausibly have been missed by the spine's authors working from slightly earlier
knowledge. Cross-checked with an independent InfoWorld article dated the same window
to avoid over-trusting a single vendor blog post's framing of "breaking changes."
cTrader SDK async-runtime claim was checked against both PyPI's package description
and Spotware's own hosted SDK docs (`spotware.github.io/OpenApiPy`) rather than forum
posts, since the async mechanism (Twisted vs asyncio) is a concrete technical fact,
not an opinion.
