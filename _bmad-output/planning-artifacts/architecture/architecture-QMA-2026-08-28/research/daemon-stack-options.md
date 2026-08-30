# daemon-stack-options — reference study

Study (not one reference): the QMX daemon's **language**, **persistence/event model**, **wire contract**.
All web facts checked **2026-08-28** via FireCrawl against primary sources. Filter = QMX Constitution
(single-operator, deterministic infra, QMX owns contracts, daemon authoritative, append-only + read-time
folds) + L31/DEC-0122: the agentic system is **built WITH the qmf-* Python libraries** (money/time types,
`fp1` fingerprints, typed refusals, registry records, `correlation_id`) and must not re-implement them.

## The six questions

**1. Target mental model.** One authoritative long-running daemon process owns durable runtime state and
agent execution; the UI is a detachable client (Constitution #4). Three seams must not leak: the daemon
*language* (which decides whether qmf contracts cross a process/language boundary), the *persistence/event
model* (append-only journal + folds, no mutable stored state), and the *wire contract* (language-neutral,
versioned, commands + queries + durable event stream — transcript #6/#9).

**2. Concrete structures** — real names/keys per dimension are in (a)/(b)/(c) below.

**3. Failure modes these options solve.** (i) Cross-language contract drift — a non-Python daemon must
re-serialize qmf-core frozen dataclasses and re-implement `fp1`, the exact thing DEC-0122 forbids.
(ii) Multi-writer store corruption. (iii) UI coupling stopping agents (Constitution #4). (iv) A separately
built UI breaking on an unversioned wire. (v) Float/identity drift if the money path crosses a boundary
that is not a named qmf conversion boundary.

**4. Reuse conceptually.** JSON-RPC 2.0 request/response/notification envelope; MCP `initialize`
capability-negotiation + dated versioning; append-and-fold persistence (SQLite WAL / JSONL); asyncio
process supervision + cancellation.

**5. Reject.** A TypeScript daemon; PostgreSQL or DuckDB as the journal store; protobuf as the *primary*
identity/wire; and the marketplace/A2A/multi-tenant machinery the TS references carry (inherited fashion).

**6. Contract QMX should own.** A **versioned QMX Daemon Wire Contract** (semver + additive-only events +
attach handshake) that carries qmf typed refusals as JSON-RPC error objects and `correlation_id` as the
JSON-RPC `id`; a **Python 3.14 asyncio daemon** that composes qmf-* at the composition root; persistence
through qmf-data's injected sinks (JSONL append journals + SQLite/WAL metadata), no database server.

---

## (a) Daemon language

**Option A — Python 3.14 asyncio daemon (LEAN).**
Python 3.14 released **2025-10-07** (docs.python.org/3.14/whatsnew/3.14.html). Ships what a supervising
daemon needs: `asyncio.create_subprocess_exec` + `TaskGroup` + `asyncio.timeout` for job workers and
cancellation; **new in 3.14** asyncio introspection (`python -m asyncio ps PID` / `pstree PID`) for a
running daemon; `concurrent.interpreters` (PEP 734 — GIL-free isolated interpreters, true parallelism) and
a `forkserver` start method for worker isolation; free-threaded build available. (docs.python.org, checked
2026-08-28.) Composes qmf-* natively at the root — money/time/`fp1`/typed-refusal/`correlation_id` never
cross a language boundary. Factory already runs Python 3.14 + uv + ruff + pyright + pytest (3,900 tests).

**Option B — TypeScript/Node daemon.**
The transcript's pull: Pi, Prime, bb, Cordis, OpenCodex are TS, and the Claude TS SDK exposes more
lifecycle hooks. **Verified** (code.claude.com/docs/en/agent-sdk/python vs /typescript, 2026-08-28): the
Python SDK `HookEvent` = 7 events {PreToolUse, PostToolUse, Notification, UserPromptSubmit, Stop,
SubagentStop, PreCompact}; the **TypeScript** `HookEvent` union adds PostToolUseFailure, PostToolBatch,
PostCompact, PermissionRequest, PermissionDenied, Setup, TeammateIdle, TaskCreated, TaskCompleted,
Elicitation, ElicitationResult, ConfigChange, DirectoryAdded, WorktreeCreate, WorktreeRemove,
InstructionsLoaded, CwdChanged, FileChanged, SessionStart, SessionEnd. Transcript claim CONFIRMED (and
understated). **But** this gap only bites if the daemon *embeds the Claude SDK to drive Claude workers*;
QMX's own daemon hooks are QMX-authored in any language, and a Claude Code worker can run as a subprocess
behind a QMX-owned provider adapter (Constitution #3). Cost of B: every qmf contract crosses a boundary →
schema export from Python dataclasses (msgspec/pydantic JSON Schema, or protobuf) + re-implemented `fp1`,
or IPC to a Python sidecar — pure DEC-0122 violation. **[INHERITED FASHION]** "TS because the references
are TS."

**Option C — Hybrid: Python daemon + language-specific *workers*.**
`connectrpc/connect-py` (PyPI `connectrpc`, active — commit 2026-08-24; ASGI/WSGI server, sync+async
clients, Connect/gRPC/gRPC-Web, streaming, conformance-verified) proves Python can *serve* a polyglot wire
today, so a Rust UI and an occasional TS/Node worker (the Claude TS SDK, if ever needed) attach as clients
behind the same contract — the daemon stays Python. This is the escape hatch, not the base.

**Lean: Python 3.14** — DEC-0122 is dispositive; the sole TS advantage (SDK lifecycle hooks) is a worker
concern, solvable by adapter, and QMX authors its own hooks regardless.

---

## (b) Persistence / event model

QMX convention: append-only evidence, read-time folds, **no database server** (qmf-registry DEC-0114;
stack DEC-0117); qmf-data already ratifies JSONL evidence journals (append+fsync, size-rotated, one
`fp1`-canonical object per line) and SQLite for transactional metadata behind CT-11, each behind a
QMF-owned contract.

**Option A — SQLite (WAL) + JSONL append journals behind qmf-data sinks (LEAN).**
`PRAGMA journal_mode=WAL` (sqlite.org/wal.html, 2026-08-28): readers don't block the writer and the writer
doesn't block readers; **exactly one writer at a time**; all processes on the **same host** (shared-memory
wal-index — no network FS); multi-process readers supported. Current release ≥ **3.51.3** (2026-03-13,
which fixed the rare multi-writer "WAL-reset" corruption bug present 3.7.0–3.51.2). Single-writer is a
*feature* here: it matches qmf's one-`WriterId`-per-stream discipline, and folds are reads. `sqlite3` is
Python 3.14 stdlib.

**Option B — PostgreSQL 18.**
Current major **18** (18.6; first released 2025-09-25, supported to 2030-11-14; 19 in beta —
postgresql.org/support/versioning, 2026-08-28). Real MVCC, many concurrent writers — but it is a
**database server**: violates DEC-0114/DEC-0117 and the single-operator/single-host reality. **[INHERITED
FASHION]** multi-tenant write concurrency. Reject for V1.

**Option C — DuckDB for journals.**
duckdb.org/docs/current/connect/concurrency (2026-08-28): one read-write process **or** many read-only;
multi-writer only as threads inside one process (MVCC + optimistic CC, "rerun on conflict"); cross-process
writes only via the **Quack** remote protocol (beta @1.5.2, mature ~v2.0 fall 2026) or DuckLake+Postgres.
Unsuitable for a multi-process OLTP journal — confirms the stack ruling that DuckDB holds **rebuildable
analytics views only** (fold outputs), never evidence.

**Event-sourcing library note.** `eventsourcing` v9.5.5 (2026-08-19, pypi.org/project/eventsourcing;
Application/Aggregate/domain-event/snapshot; SQLite + PostgreSQL backends) is a clean conceptual mirror of
append+fold — but qmf-registry (CT-06 records, CT-07 JSONL lineage edges) + qmf-data (CT-11 append-store)
**already own** those contracts. Do NOT add it as a dependency; borrow only the vocabulary.

**Lean: SQLite/WAL + JSONL through qmf-data's injected `ObservationSink`/`JournalSink`/`RecordSink`.**
The daemon is the single writer process; the UI and folds are readers. No new store engine, no server.

---

## (c) Wire contract

**Option A — JSON-RPC 2.0 envelope over WebSocket (commands+queries) + durable event stream (LEAN).**
JSON-RPC 2.0 (jsonrpc.org/specification; origin 2010-03-26, updated 2013-01-04, checked 2026-08-28):
transport-agnostic (in-process, sockets, HTTP, message passing); Request `{jsonrpc:"2.0",method,params,id}`,
Response `{jsonrpc,result|error,id}`, Notification (no `id`), Batch; error object `{code,message,data}`
with −32768..−32000 reserved. Fit to QMX: `id` **is** the request↔response correlator (maps to
`correlation_id`); Notifications are the push channel (the durable event stream = replay of the append-only
journal — session replay is already an architectural capability); typed refusals serialize straight into
the `error` object; JSON aligns with qmf's `fp1` canonical-JSON. One WebSocket carries bidirectional
commands+events; add plain HTTP GET for point queries.

**Option B — gRPC / Connect (runner-up).**
connectrpc.com + `connect-py` (above): schema-first protobuf, HTTP/1.1+HTTP/2, first-class streaming,
typed codegen for Rust (UI) + TS + Python from one `.proto`. Strong for a versioned polyglot contract, and
a Python server exists **today**. Reject as *primary* for V1: protobuf's binary/field-number identity
clashes with `fp1` canonical-JSON identity, and it imposes a proto + buf codegen toolchain. Keep as the
fallback if binary throughput or strict streaming ever dominates.

**Option C — MCP-style transport.**
MCP spec current revision **2026-07-28** (modelcontextprotocol.io, 2026-08-28): JSON-RPC over two standard
transports — **stdio** (newline-delimited JSON-RPC over a client-launched subprocess) and **Streamable
HTTP** (HTTP POST to one endpoint; replies as a JSON object or a request-scoped **SSE** stream); custom
transports allowed over any bidirectional stream (reuse stdio framing over TCP/Unix sockets); `initialize`
handshake negotiates capabilities + protocol version, with a documented backward-compat matrix. QMX's role:
this is the model for the **attach handshake + versioning**, and MCP is a *tool adapter inside the tool
registry* (transcript #58) — not the daemon's own contract.

**Schema-first + versioning strategy (borrow across A/C).** Describe commands/queries with **JSON Schema**
(+ OpenAPI for the HTTP query surface, **AsyncAPI** for the event stream); version the contract with
**semver**; make events **additive-only** (never redefine — mirrors qmf's contract-format-version law);
negotiate **capabilities on attach** (MCP `initialize` shape) so an old UI and a new daemon interoperate.
Event stream: **WebSocket** for the bidirectional daemon socket; **SSE** acceptable only for a one-way
fan-out client.

**Lean: JSON-RPC 2.0 over WebSocket + HTTP-GET queries, JSON-Schema-described, semver + additive events +
`initialize`-style capability negotiation.** Language-neutral for Rust UI ↔ Python daemon, and identity-
consistent with `fp1`.

---

## Cross-cutting: inherited fashion to drop (single-operator, single-host)
- TS daemon "because the references are TS" (Pi/Prime/bb/Cordis/OpenCodex).
- The Claude TS SDK's 20+ lifecycle hooks — built for a general multi-tenant IDE; QMX fires only the few
  its own authored loops need.
- gRPC/protobuf polyglot codegen, extension marketplaces, external A2A transports — public-marketplace /
  multi-tenant machinery.
- Postgres / DuckLake / Quack multi-writer coordination — multi-tenant scale.

## Open (this study cannot settle)
- Whether any worker must literally be the Claude **TS** SDK (the only real TS pull) — a roster decision.
- Event-stream durability mechanics (retention/replay window) — lands in the qmf-data journal-trim ruling
  ("set only after measured volume", DEC-0117).
- Exact schema tool (raw JSON Schema vs OpenAPI+AsyncAPI vs Connect `.proto`) — pick when the UI contract
  session runs (transcript defers UI to its own session).

## Sources (all checked 2026-08-28)
- docs.python.org/3.14/whatsnew/3.14.html — Python 3.14 (2025-10-07), asyncio introspection,
  concurrent.interpreters, forkserver.
- code.claude.com/docs/en/agent-sdk/python and /typescript — HookEvent surfaces (7 vs ~26).
- github.com/connectrpc/connect-py + connectrpc.com/docs/python — Python Connect/gRPC server.
- sqlite.org/wal.html — WAL concurrency (single writer, same host), 3.51.3 fix.
- postgresql.org/support/versioning — PostgreSQL 18.6 current major.
- duckdb.org/docs/current/connect/concurrency — single-writer-process; Quack beta.
- pypi.org/project/eventsourcing — v9.5.5 (2026-08-19), SQLite+Postgres.
- jsonrpc.org/specification — JSON-RPC 2.0 (2010/2013).
- modelcontextprotocol.io/specification/2026-07-28/basic/transports — stdio + Streamable HTTP(SSE),
  initialize handshake, versioning.
