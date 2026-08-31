# Reviewer gate — CURRENCY lens

**Target:** `_bmad-output/planning-artifacts/architecture/architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md`
**Lens:** currency — was every committed technology web-researched or reality-checked, or asserted from training data?
**Reviewed:** 2026-08-28. Every version below was fetched live today (FireCrawl) or read off the operator's own machine; each carries its source.
**Method:** each Stack row cross-checked against `research/*.md` first; any row no study verified was verified here against a primary source. Two rows were additionally reality-checked against the operator's installed software.

---

## Verdict

**CONDITIONAL PASS — one critical row must change before the spine goes to build.**

The spine's currency *discipline* is good: it dates its Stack table, it inherits parent rows at the parent's own verification date instead of restamping them, and it writes `[UNVERIFIED]` rather than inventing a pin. That honesty is the reason this review has few findings rather than many.

But the discipline has three leaks. (1) The one row the whole durable-state law rests on — SQLite via stdlib `sqlite3` — is stamped "verified 2026-08-28" and is **unsatisfiable on the operator's actual runtime**: CPython 3.14 bundles SQLite 3.50.4, below the 3.51.3 floor the row declares. Two rows of the same table contradict each other. (2) Four rows read `[UNVERIFIED]` when all four verify in one step, and two of those four are *contradicted by the spine's own companion studies* — the Hindsight study's "current" version is five minors stale and the OpenCodex study reported the locally installed version as if it were the published one. (3) The chosen wire transport is the only major decision in the spine with **no verified implementation behind it** — the study verified a live Python library for the option that was rejected, and none for the option that was adopted.

Nothing here overturns a design decision. Every finding is a Stack-table or clause-level correction the editor can apply.

---

## CRITICAL

### C-1 — The Stack table contradicts itself: CPython 3.14 cannot deliver SQLite 3.51.3

**Where:** Stack, rows "CPython (daemon runtime) | 3.14" and "SQLite in WAL mode, via stdlib `sqlite3` | 3.51.3 or newer (verified 2026-08-28)". Bears on AD-6 (one journal, one writer), Inherited row DEC-0114/DEC-0117, and the Structural Seed.

**What is wrong.** The row demands SQLite ≥ 3.51.3 *and* names stdlib `sqlite3` as the delivery mechanism. The stdlib module does not have a version of its own — it reports whatever SQLite library CPython was built against. For the 3.14 line that is **3.50.4**, which is below the declared floor.

Evidence, two independent confirmations:

- Primary, upstream: CPython's `3.14` branch pins `sqlite-3.50.4.0` in its Windows build externals — https://raw.githubusercontent.com/python/cpython/3.14/PCbuild/get_externals.bat (fetched 2026-08-28). This is branch-level, so it holds across the whole 3.14.x Windows line, 3.14.7 included.
- Reality check, this machine: `python -c "import sqlite3; print(sqlite3.sqlite_version)"` → **3.50.4**, on CPython 3.14.6 (the operator's installed interpreter).

**Why the floor was chosen, and why it matters.** `research/daemon-stack-options.md#(b)` picked 3.51.3 because it "fixed the rare multi-writer *WAL-reset* corruption bug present 3.7.0–3.51.2". That is a **corruption** bug in exactly the store AD-6 makes the sole durable append target. So the row is not cosmetic: an implementer who takes it literally either writes a startup assertion that fails on the operator's own interpreter, or silently ships two minors under a floor chosen to avoid journal corruption.

**The resolution is already in the spine — it is just not connected to the row.** The bug requires *concurrent writers*. AD-6's sole-writer invariant ("no process other than the daemon opens the journal, the SQLite file or the artifact store") makes it non-triggering by construction. That is a legitimate answer; it is simply nowhere stated, so the table currently reads as a broken pin rather than a governed one.

For reference, the current upstream SQLite release is **3.53.4 (2026-07-24)** — https://www.sqlite.org/changes.html — so 3.51.3 was never the "current" version either; it was a floor, and the row's phrasing ("or newer") obscures that.

**Fix (editor):** replace the row with the two facts and the governing invariant, e.g.

> | SQLite in WAL mode, via stdlib `sqlite3` | **3.50.4** — the version CPython 3.14 bundles (verified 2026-08-28: cpython `3.14` `PCbuild/get_externals.bat`; local `sqlite3.sqlite_version` on 3.14.6). Upstream current is 3.53.4. The 3.51.3 WAL-reset corruption fix is **not** present; it is not required, because that bug needs concurrent writers and AD-6's sole-writer invariant forbids them. |

and add one sentence to AD-6: *the daemon asserts `sqlite3.sqlite_version` at startup and records it; if the sole-writer invariant is ever relaxed, the floor becomes 3.51.3 and the daemon must be given a newer library (a CPython build bundling ≥3.51.3, or `pysqlite3-binary`) before that change lands.* This turns a contradiction into a stated, tested constraint and pre-empts the exact future change that would silently reintroduce the risk.

---

## HIGH

### H-1 — The wire transport is the only major decision with no verified implementation

**Where:** AD-5; Stack ("JSON-RPC (wire transport) | 2.0"); `research/daemon-stack-options.md#(c)`.

AD-5 commits hard: "Transport is JSON-RPC 2.0 over WebSocket with HTTP GET for queries, an MCP-style `initialize` handshake … and JSON-Schema-described message families." The Stack table pins the **specification** (JSON-RPC 2.0 — correct, stable since 2013, cannot go stale) but names **no WebSocket server, no HTTP server, and no JSON-Schema validator**, and no study verified one.

The asymmetry is what makes this a currency finding rather than a scoping one: the study *did* verify a live, maintained, conformance-tested Python implementation (`connectrpc/connect-py`, commit 2026-08-24) — but for **Option B, which was rejected**. The adopted Option A has a verified *spec* and an unverified *stack*. The spine therefore commits a versioned public contract, which the UI session will bind against, to an implementation nobody checked exists or supports Python 3.14.

It does exist and it does — but the spine should say so rather than leave the table silent:

- `websockets` **17.1**, released **2026-08-26**, `Requires-Python >=3.11` (so 3.14-clean) — https://pypi.org/project/websockets/ (verified 2026-08-28).

**Fix (editor):** add a Stack row for the WebSocket implementation with the pin above, and add a row for the JSON-Schema validator reading `[UNPINNED — implementation choice at build time]` (the options sheet already records "exact schema tool … pick when the UI contract session runs", so this is consistent, but the table should carry the gap explicitly instead of omitting it).

### H-2 — Hindsight: the companion study's "current version" is five minors stale, and AD-18 states its dependency too narrowly

**Where:** Stack ("Hindsight (deferred first memory backend) | [UNVERIFIED]"); AD-18; Deferred row "External memory backend".

`research/memory-providers.md` states, as verified on 2026-08-28: "Docker image tag **0.4.9** current". Live check the same day:

- Latest release **v0.9.2, 2026-08-25** (v0.9.1 2026-08-14, v0.9.0 2026-08-07, v0.8.0 2026-06-08) — https://github.com/vectorize-io/hindsight/releases (verified 2026-08-28).

Five minor versions in roughly three months, on a project the spine names as its first memory backend. Two consequences:

1. **AD-18 asserts a dependency that is now broader than stated.** The rule says "its Postgres and pgvector dependency arrives isolated inside that provider". The current README lists PostgreSQL + pgvector **or Oracle AI Database 23ai** — https://github.com/vectorize-io/hindsight (verified 2026-08-28). The clause is written as a fact about the product, and that fact has already moved.
2. **The port design was mapped 1:1 against 0.4.9.** The study's "why it fits nearly 1:1" mapping (propose→`retain`, `max_tokens`, `types`, `tags_match`, `prefer_observations`, `PATCH state=invalidated`, observation `history`) was read off a surface five minors old. `qma-core`'s MemoryProvider contract is QMX-owned and does not *depend* on that mapping — which is what bounds this finding below critical — but the claim that admission is cheap does.

Severity is further bounded because AD-18 defers admission entirely (`recall` is unavailable until a provider is admitted; candidates stage in the AD-22 store). Nothing in v1 ships against this. It is still a companion study carrying a wrong current-version claim that the spine cites.

**Fix (editor):** fill the Stack row — `v0.9.2 (2026-08-25, github.com/vectorize-io/hindsight/releases, verified 2026-08-28); MIT; Linux/macOS/Windows x86_64` — soften AD-18's clause to "*a Postgres+pgvector or Oracle 23ai store, isolated inside that provider and never touching the QMA journal*", and add to the Deferred revisit condition: *the port↔Hindsight mapping was verified against 0.4.9; re-verify the whole surface at admission.*

### H-3 — OpenCodex: the study reported the locally installed version as the current one

**Where:** Stack ("OpenCodex (first ModelDeployment implementation) | [UNVERIFIED]"); AD-15.

`research/opencodex-model-proxy.md` gives "v2.31.0" citing the repo README "checked 2026-08-28". Live check today:

- npm `@bitkyc08/opencodex` latest is **2.34.0**, published **2026-08-27** (`npm view @bitkyc08/opencodex version dist-tags.latest time.modified`, run 2026-08-28).
- The operator's installed CLI is **2.31.0** (`ocx --version`, run 2026-08-28).

So 2.31.0 was the *local install*, three minors behind the published release, reported as the current version. The distinction matters for AD-15 specifically, because that rule leans on behavior observed in the live local install (combos, `accountPoolStrategy: quota`, `stickyLimit`, the capability maps) — those are properties of 2.31.0, not necessarily of 2.34.0.

**Fix (editor):** fill the row carrying **both** numbers and their meanings — `2.34.0 published (npmjs.com/package/@bitkyc08/opencodex, 2026-08-27); 2.31.0 installed locally (verified 2026-08-28) — AD-15's observed routing behavior is the local install's` — so the gap is visible rather than collapsed into one number.

### H-4 — Docker and OpenTelemetry read `[UNVERIFIED]` but verify in one step, and Docker is already on the operator's machine

**Where:** Stack rows "Docker (default worker isolation) | [UNVERIFIED]" and "OpenTelemetry exporter (behind the export port) | [UNVERIFIED]". Docker is load-bearing — AD-17 makes Docker-per-worker the default isolation and AD-25 puts workers in Docker on the workstation, so it is not a peripheral row.

- **Docker Engine 29.7.2, released 2026-08-05** — https://docs.docker.com/engine/release-notes/29/ (verified 2026-08-28); major 29 first released 2025-11-10 and in support (endoflife.date/docker-engine).
- **Reality check, this machine:** `docker --version` → **29.6.1** (build 8900f1d) — installed, one patch behind current. The daemon was not running at review time (`npipe:////./pipe/dockerDesktopLinuxEngine` not found), which is a Docker Desktop state, not a defect.
- **OpenTelemetry Python SDK 1.44.0, released 2026-07-16** — https://pypi.org/project/opentelemetry-sdk/ (verified 2026-08-28). AD-23 keeps this behind the export port as a swappable adapter, so it is an adapter pin, not a core dependency — which is the right shape and worth keeping explicit in the row.

**Fix (editor):** fill both rows with the versions and URLs above; note on the Docker row that the workstation host is Docker Desktop for Windows (the WSL2 backend) rather than a bare Engine install, since AD-25 puts the default worker isolation on Windows 11.

---

## MEDIUM

### M-1 — Two inherited toolchain rows are stale; the parent's own rule says re-verify at each gate

The parent spine's Stack heading reads "verified 2026-08-19/2026-08-20, **re-verified at each reviewer gate**". This is a reviewer gate, and the currency lens is the one that owes it. Re-verified today against PyPI:

| Row | Spine says | Live 2026-08-28 | Status |
| --- | --- | --- | --- |
| uv | 0.12.5 | **0.12.7** (2026-08-27) | stale — https://pypi.org/project/uv/ |
| ruff | 0.16.3 | **0.16.5** (2026-08-27) | stale — https://pypi.org/project/ruff/ |
| pyright | 1.1.411 | 1.1.411 (2026-06-24) | current — https://pypi.org/project/pyright/ |
| pytest | 9.1.1 | 9.1.1 (2026-06-19) | current — https://pypi.org/project/pytest/ |
| poethepoet | 0.48.0 | 0.48.0 (2026-07-05) | current — https://pypi.org/project/poethepoet/ |
| duckdb | 1.5.5 | 1.5.5 (2026-07-22) | current — https://pypi.org/project/duckdb/ |
| CPython | 3.14 | 3.14.7 current — https://www.python.org/downloads/ | current |

Both stale rows moved by patches on 2026-08-27, i.e. the day before this spine was written — this is drift, not neglect. Low consequence (lint and lockfile tooling), but the parent's re-verification rule is explicit and the fix is free.

**Fix (editor):** bump uv → 0.12.7 and ruff → 0.16.5, and mark the unchanged rows "(re-verified 2026-08-28)" so the next gate can see which rows were actually checked rather than copied.

### M-2 — pgvector is named in a committed rule but appears in no Stack row and carries no version

AD-18 names pgvector explicitly ("its Postgres and pgvector dependency arrives isolated inside that provider"). It has no Stack row, no version, and no study verified it. Current:

- pgvector **0.8.6, 2026-07-29** (0.8.5 2026-07-08) — https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md (verified 2026-08-28); builds against PostgreSQL 13–18.

The spine should not silently name a dependency that no row governs — the parent's own convention is that every runtime dependency lands in the AD-6 register with name, licence and why.

**Fix (editor):** either add a Stack row pinned as above and marked "arrives only with the deferred memory provider", or state in AD-18 that Postgres and pgvector versions are pinned at provider admission and are deliberately absent from the v1 Stack table. Either is fine; silence is not.

---

## LOW

### L-1 — An open `[UNVERIFIED]` from the options sheet was never carried into the spine

`research/options-sheet.md` open item 1: two companion studies give **7 vs 10** in-process hook events for the Claude Agent Python SDK, both citing the same source checked the same day (`claude-agent-sdk-hooks.md#Verified fact A` says 10; `daemon-stack-options.md#(a)` says 7). The sheet says the discrepancy "must be resolved before any Claude-worker adapter is specified".

The spine specifies no Claude-worker adapter and AD-10's hook set is entirely QMA-authored, so nothing today depends on the number — correctly, this did not need to block the spine. But the spine is silent, so the flag dies here rather than travelling to the session that will need it (AD-15's Deployment adapters, AD-17's worker templates).

**Fix (editor):** one Deferred row — *Claude-worker adapter: two companion studies disagree on the Python SDK's in-process hook surface (7 vs 10, same source, same day); resolve before the adapter is specified.*

### L-2 — Confirmed current, no action (recorded so the next gate need not re-check)

- **JSON-RPC 2.0** — origin 2010-03-26, last updated 2013-01-04. Stable; a spec that cannot go stale. Row is correct as written.
- **Model Context Protocol, revision 2026-07-28** — confirmed still current: `modelcontextprotocol.io/specification/latest` resolves to `/specification/2026-07-28` (verified 2026-08-28). Row is correct. Worth noting for AD-16 that MCP revisions are **dated, not semver**, so the adapter pins a revision date — the spine already writes it that way.
- **Python 3.14 feature claims** in AD-4 (`TaskGroup`, `asyncio.timeout`, asyncio introspection, `concurrent.interpreters`/PEP 734, `forkserver`) were verified in `daemon-stack-options.md` against docs.python.org for the 3.14 release; no drift found.

---

## Summary table

| # | Severity | Finding | Editor can apply alone |
| --- | --- | --- | --- |
| C-1 | critical | CPython 3.14 bundles SQLite 3.50.4; the Stack row demands ≥3.51.3 via stdlib `sqlite3` — unsatisfiable, on the row all durable state rests on | yes |
| H-1 | high | AD-5's chosen transport has no implementation pinned or verified; the study verified one only for the rejected option | yes |
| H-2 | high | Hindsight study's "current 0.4.9" is five minors stale (v0.9.2); AD-18 states its store dependency too narrowly | yes |
| H-3 | high | OpenCodex study reported the local install (2.31.0) as current; published is 2.34.0 | yes |
| H-4 | high | Docker and OTel rows read `[UNVERIFIED]`; both verify in one step and Docker is already installed locally | yes |
| M-1 | medium | uv 0.12.5→0.12.7 and ruff 0.16.3→0.16.5 stale; parent's rule requires re-verification at each gate | yes |
| M-2 | medium | pgvector named in AD-18, governed by no Stack row and no version | yes |
| L-1 | low | The options sheet's unresolved 7-vs-10 hook-count `[UNVERIFIED]` never reached the spine's Deferred table | yes |

All eight are Stack-table or clause-level corrections. None requires an operator ruling: C-1's resolution stance (accept the sole-writer mitigation rather than adding a SQLite dependency) is already law in AD-6 and only needs to be written next to the row it governs.
