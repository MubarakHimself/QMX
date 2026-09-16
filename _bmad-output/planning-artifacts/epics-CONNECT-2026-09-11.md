---
stepsCompleted: [1, 2, 3, 4]
validated: true
inputDocuments:
  - _bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/ARCHITECTURE-SPINE.md
  - docs/decisions/ADR-0021-connect-fx-paper.md
  - workroom/research/2026-09-11_connect-docs-factory-result.md
  - _bmad-output/planning-artifacts/epics.md (Epics 24–28 only — extend, do not duplicate; Phase-1 1–23 and Epic 29–30 out of this increment)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (§7 out of scope; no CONNECT FR ladder of its own)
  - docs/components/trading-node.md (CONNECT FX paper 2026-09-11)
  - docs/components/qmf-venue.md (CONNECT FX paper 2026-09-11)
  - docs/components/ctrader.md (CONNECT FX paper 2026-09-11)
  - docs/contracts/ct-13-journal.yaml
  - docs/contracts/ct-18-venue-capabilities.yaml
  - docs/contracts/ct-19-venue-command.yaml
  - docs/contracts/ct-20-venue-event.yaml
  - docs/contracts/ct-21-venue-secret-session.yaml
  - docs/scenarios/SCN-0005-uncertain-venue-submission.md
  - docs/glossary.md (VenueClientPort, VenueClientKind)
  - docs/gap-report.md (GAP-0059, GAP-0060)
  - _docwork/feature_inventory.yaml (FEAT-0032)
  - _docwork/ledger.yaml (DEC-0263..DEC-0268)
  - _docwork/gaps.yaml (GAP-0059, GAP-0060)
  - integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 (brownfield defects this increment forbids)
excludedDocuments:
  - _bmad-output/planning-artifacts/epics.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md
  - UX design contract (no UI this increment)
delegation: "operator 2026-09-11 — autonomous run; operator absent; menus auto-continued; CONNECT increment only"
epicNumbering: "Epic 31 — reserved so CONNECT never collides with Phase-1 (1–23), trading-node (24–30), or QMA (40+)"
baseInventory: "integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 (git show, no checkout)"
feature: FEAT-0032
adr: ADR-0021
decisions: [DEC-0263, DEC-0264, DEC-0265, DEC-0266, DEC-0267, DEC-0268]
---

# QMX - Epic Breakdown

## Overview

This document is the epic and story breakdown for the **CONNECT FX paper**
increment (FEAT-0032): hexagonal port completion so QMX can CONNECT and
honestly FX paper-trade on the existing cTrader adapter.

It decomposes the ratified CONNECT corpus — architecture-CONNECT-2026-09-11
AD-1..AD-5, ADR-0021, DEC-0263..DEC-0268, CT-13/18/19/20/21 CONNECT usage
annotations, and the four brownfield connect bugs at
`integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` — into implementable
stories for the factory lanes.

The Phase-1 file (`epics.md`, Epics 1–23 and trading-node Epics 24–30) stays
untouched and is not superseded. QMA (`epics-QMA-2026-08-29.md`, Epic 40+)
stays untouched. **Epic numbering starts at Epic 31**, a reserved block so
CONNECT never collides with those files.

Requirement prefixes carry the C marker because these requirements derive from
the **ratified CONNECT docs corpus and child spine, not from PRD §5**. PRD §7
futures/options exclusion and the NODE/QMX parent invariants bind read-only.
Rules carried forward from `epics.md`: each FR's cited artifact is the epic
boundary and the source of its acceptance criteria; FR granularity is
deliberately coarser than story granularity — never size a lane by counting
FRs.

This increment **extends** node Epics 24–28. It does not duplicate completed
stories. Story 24.3 remains the sensing/decode substrate; Story 24.5 remains
command-identity and protection-at-placement; Story 26.5 remains Book-level
paper routing; Story 26.6 remains the four-verdict fold; Story 27.2 remains
governed intake; Story 28.2 remains live sensing-only until a live binding.
CONNECT stories **close** the FTR-01 blocks those stories left open and
**forbid** the sensing-only submit, fail-open else-branch, and tests-only
`connect_open_api` that brownfield still exhibits.

Preflight verdict (ADR-0021): **reuse COMP-QMN** and **reuse COMP-QMF-VENUE**.
No new component, no second port, no fourth `VenueClientKind`, no gateway
library. Ratification fixes the architecture only. Nothing in this document
grants implementation, credential, order, paper-mode, promotion, live-money or
destructive authority; that arrives only through the factory pipeline
(ADR-0021; DEC-0268).

## Requirements Inventory

### Functional Requirements

**A. Fail-closed live selection (DEC-0263 / CONNECT AD-1)**

- FR-C01: `qmn.venue.port.select_venue_client` selects a `VenueClientPort` implementation by the pair `(world, VenueId)`, never by `VenueId` alone. `world = replay` selects `VenueClientKind.REPLAY` for every `VenueId` and the composition refuses any venue-connecting kind. `world = simulated` returns `unsupported capability`. `world = live` reads an **explicit roster field** `VenueClientKind` on that binding — not inferred from `VenueId` spelling. CTRADER is legal only when that field is `ctrader`. CONFORMANCE is legal only when that field is `conformance` or the `VenueId` value starts with `conformance:`. Absent field, unknown kind, or any other live `VenueId` is `unsupported capability`. The integration else-branch that assigns CTRADER (`port.py` at `1b451a8`) is a connect bug, not TN-11. (trading-node.md CONNECT AD-1; ADR-0021; FR-061 amendment)

**B. Honest FX paper (DEC-0264 / CONNECT AD-2)**

- FR-C02: An FX paper claim requires every element together: vendor cTrader demo host (`demo.ctraderapi.com`); `AccountRole.DEMO`; `world = live`; the same live `VenueClientPort` implementation used for live (`LiveCTraderClient`); submit encode of every CT-19 kind the bound CT-18 declaration supports; position and balance read-back per FR-C04. `LiveCTraderClient.submit` returning `unsupported capability` after session and capabilities are ready is not paper. Live-capital bleeding is not an adapter skip. Spot FX is not deferred. No local matching engine. No Bot or Book twin. Soak remains TN-9: the demo connection carries the order path; a live connection, when credentials exist, is sensing and recording only until a live binding. Connection count is derived from the roster (DEC-0244); a soak roster may name one `(venue, environment)` pair. (ADR-0021; FR-058/059 extended, not replaced)

**C. Encode and session locus (DEC-0265 / CONNECT AD-3)**

- FR-C03: `qmn.venue` remains the sole `qmf-venue` importer (DEC-0241). ProtoOA command encode for the five CT-19 kinds (`place_order`, `cancel_order`, `close_position`, `close_all`, `amend_protection`) and `connect_open_api` complete the existing `qmf.venue.connection.ConnectionManager` (DEC-0243 exemption already applied). Encode symbols live in `qmf-venue`; `qmn.venue.live` translates a `Command` onto those symbols and must not compile proto messages itself. After an open session and verified capabilities, `LiveCTraderClient.submit` hands a well-formed `Command` to that encode path; a CT-19 kind the bound CT-18 declaration supports that remains sensing-only is a connect bug. The production node calls `connect_open_api`; a tests-only caller is a connect bug. DEC-0242 stays recorded-not-applied. No CCXT, no Hummingbot, no Spotware SDK, no Twisted. (qmf-venue.md CONNECT; ADR-0021)

**D. FTR-01 closed (DEC-0266 / CONNECT AD-4)**

- FR-C04: `position-read-back` and `balance-read-back` are CT-20 observation kinds (DEC-0247). They map through CT-20's versioned (observation kind) → event-type table onto CT-13 `data quality`. No eighth journal type. No second catalog. DEC-0247's word "observation" names the CT-20 kind, not a journal type — CT-13's seven (`decision`, `order`, `fill`, `risk transition`, `promotion`, `data quality`, `control action`) do not include `observation`. `LiveCTraderClient.reconcile()` returns the four-verdict `Reconciliation` (`reconciled | drift | unknown | out-of-lookback`) over the declared lookback and no longer returns `unsupported capability` for those kinds. Adapters never synthesize the observations. Journal type `data quality` is CONNECT assumption A3, cheap-veto. This closes FTR-01 for Stories 24.3 and 27.2 without rewriting those stories. (CT-20 CONNECT usage; CT-13; FR-060 unblocked)

**E. Crypto plurality without a fourth V1 kind (DEC-0267 / CONNECT AD-5)**

- FR-C05: A later non-cTrader live venue is a new CT-18 static declaration plus a new `VenueClientPort` implementation selected by `(world, VenueId)` through FR-C01. Same four contracts. Same `qmn.venue` import boundary. Adapter code lives in `qmf-venue` and imports only `qmf-core`. This increment does not mint a fourth `VenueClientKind` member and does not pick an exchange. TN-11's three V1 implementations (`ctrader`, `replay`, `conformance`) stand. TN-22 "second broker is roster" applies to the same protocol family; a new protocol is a later module (L22), never config-mapping a non-cTrader `VenueId` onto `LiveCTraderClient`. Canonical live source token stays hardcoded `ctrader` (GAP-0060 deferred). (constitution L22 CONNECT annotation; ADR-0021)

**F. Authority and deferred surface (DEC-0268 umbrella)**

- FR-C06: This increment reuses COMP-QMN and COMP-QMF-VENUE. It mints no new component, no second port, no gateway library, and no new contract id. CT-13/18/19/20/21 take CONNECT usage annotations only (already in `docs/`). Implementation, credentials, a live session, order submission, paper-mode transition, and go-live are factory-pipeline-only. FX live binding / live money stay TN-9: this increment makes paper honest, not live go-live. (ADR-0021 architecture-preflight)

- FR-C07: FTR-02 compound-command annotation remains blocked (GAP-0059 deferred, non-blocking). Single-kind FX paper encode does not require FTR-02. `CompoundCommand` submit continues to return the existing unsupported-capability block. Protobuf runtime stays `==7.36.0` in qmf-venue; 7.36.1 is not adopted. SessionTopology `ClassVar=2` is not this increment (DEC-0244 already binds roster-derived count). (GAP-0059; GAP-0060; stack)

### NonFunctional Requirements

CONNECT inherits NFR-04, NFR-05, NFR-09, NFR-11, NFR-12, NFR-14, NFR-15,
NFR-19, NFR-21 from `epics.md` unchanged. Increment-local NFRs:

- NFR-C01: Fail-closed selection — an unknown, absent, or illegal live `VenueClientKind` must not open a cTrader socket. (NFR-12; DEC-0263)
- NFR-C02: Secret values remain references above `ConnectionManager`; CONNECT adds no secret architecture and no fifth holder. (NFR-14; AD-26; CT-21)
- NFR-C03: Position/balance read-backs persist verbatim and journal as CT-13 `data quality` before interpretation; adapters never synthesize them. (NFR-15; DEC-0266)
- NFR-C04: Public formats stay the annotated CT-13/18/19/20/21 shapes; no eighth journal type; FTR-01 is closed by mapping, not by minting. (NFR-19)
- NFR-C05: Credential-free Tier 1 and double-backed Tier 2 stay green without live network use; Spotware token unlocks only separately tagged live acceptance and never serializes unrelated stories. (AR-75; AR-87)
- NFR-C06: CPython 3.14; protobuf `==7.36.0` in qmf-venue only; proto tag 91 in-house; Open API TCP 5035; hosts `demo.ctraderapi.com` and `live.ctraderapi.com`. (CONNECT Stack; AR-74)
- NFR-C07: The L30/`qmn.venue`-only import gate remains a tier-1 static check; `qmb`/`qml` keep the `qmf-venue` ban; QMA packages never import `qmf-venue`. (AR-73; DEC-0241)

### Additional Requirements

- AR-C01: Code is specified against the read-only brownfield at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` (no checkout of `integration`). Defects this spine forbids, not seed to copy: (1) `select_venue_client` else-branch assigns `VenueClientKind.CTRADER`; (2) `LiveCTraderClient.submit` returns `unsupported capability` after session and capabilities are ready (Story 24.3 sensing-only); (3) `LiveCTraderClient.reconcile` and `qmn.data.mapping` refuse under FTR-01; (4) `connect_open_api` has no production caller. (ARCHITECTURE-SPINE Structural Seed)
- AR-C02: No starter template. No new distribution. Structural seed is inherited: `qmn/src/qmn/venue/`, `qmn/src/qmn/paper/`, `packages/qmf-venue/src/qmf/venue/connection.py`, `commands.py`, `events.py`. (CONNECT Structural Seed)
- AR-C03: Factory touch ownership — Epic 31 is serial after Epic 24 (same `qmn/venue` and `qmf-venue` transport surfaces). It may patch `select_venue_client` call sites in `qmn/config/roster.py` and `qmn/replay/session.py` only. It must not redesign Epic 25's config compiler, Epic 26 protection/ledger, Epic 27 secrets/backup, or Epic 28 milestone manifests. (epics.md factory table, extended)
- AR-C04: Story 24.1–24.10, 25.*, 26.*, 27.*, 28.* in `epics.md` remain the substrate. CONNECT stories cite them; they do not re-implement transport, conformance double, verification suite, command ordinal, UNKNOWN, amend atomicity, reconnect, Book paper routing, KSA, virtual ledger, secrets wizard, or the unattended week. (operator scope)
- AR-C05: Cheap-veto A1–A5 on DEC-0268 stand: A1 FX-first / crypto later; A2 brownfield SHA re-verified at `1b451a8`; A3 journal type is `data quality`; A4 protobuf pin stays `==7.36.0`; A5 no PRD amendment this sitting. A factory worker may not overturn them.
- AR-C06: Dead list honored: CCXT, Hummingbot, Spotware SDK, Twisted, local matching engine, Bot/Book twins, paper as sensing-only, unknown-live-VenueId-defaults-CTRADER, eighth journal type, realizing `VenueClientPort` inside `qmf-venue` (DEC-0242 RNA). (ADR-0021)
- AR-C07: Out of this increment (Deferred table): crypto exchange pick and fourth `VenueClientKind`; PRD §7 asset-class amendment; Book/BMS/sizing/crypto market-hours; MIS training (GAP-0051); UI/Penpot; STRATS/loop-engineering; FTR-02; canonical live-source parameterization; protobuf 7.36.1; SessionTopology ClassVar=2; FX live binding / live money; DEC-0242 realization; non-Dukascopy history intake. (CONNECT Deferred)
- AR-C08: Human/coordination gates stay local: Spotware sandbox token unlocks tagged live-session acceptance only; missing token does not block 31.1–31.6 credential-free gates. (AR-87)
- AR-C09: FTR-01 is **resolved for CONNECT intake** by DEC-0266. Stories 24.3 and 27.2 keep their historical FTR-01 ACs in `epics.md`; Story 31.5 is the implementing close. FTR-02 remains open (GAP-0059).
- AR-C10: SCN-0005 (uncertain venue submission) still binds: UNKNOWN blocks the command stream; sensing pipe stays open; CONNECT encode must not retry, assume an outcome, or flatten. (SCN-0005; DEC-0265)

### UX Design Requirements

No UX design contract applies. CONNECT has no UI, Penpot, or desktop-door work (TN-17 doors already bind; Phase 3). UX-DR list is empty.

### FR Coverage Map

- FR-C01: Epic 31 — fail-closed live selection (Story 31.1)
- FR-C02: Epic 31 — honest FX paper claim (Story 31.6; enabled by 31.2–31.5)
- FR-C03: Epic 31 — production `connect_open_api` (31.2), encode symbols (31.3), submit handoff (31.4)
- FR-C04: Epic 31 — FTR-01 closed mapping and four-verdict reconcile (Story 31.5)
- FR-C05: Epic 31 — no fourth kind / no crypto pick / no config-onto-cTrader (Stories 31.1 and 31.6)
- FR-C06: Epic 31 — reuse-only, no live-money authority (all stories; 31.6 live-binding AC)
- FR-C07: Epic 31 — FTR-02 remains blocked; protobuf pin (Stories 31.3, 31.4)
- Inherited FR-058 / FR-059: still Epic 26.5 / Epic 28 — CONNECT 31.6 extends the paper *claim*, does not replace routing or the soak week
- Inherited FR-060: still Epic 26.6 — CONNECT 31.5 unblocks the read-backs that fold consumes
- Inherited FR-061 / FR-062: still Epic 24 — CONNECT 31.1/31.4 close the fail-open and sensing-only defects those FRs already forbade in law

## Epic List

Weight tags route factory lanes: **H** heavy. CONNECT is one epic because
selection, session, encode, submit, and read-back churn the same core files
(`qmn/venue/port.py`, `qmn/venue/live.py`, `qmf.venue.connection`, mapping/
reconcile). Splitting would be file-churn without a feedback loop.

Wave: **N1b — CONNECT completion**, serial after Epic 24, before Epic 28's
honest-paper precondition. Parallel with Epics 25/26/27 only on disjoint
files (see factory touch ownership).

### Epic 31: Honest FX paper on the existing cTrader adapter (Wave N1b, H)

The operator can fail-closed-select a live venue, open a production cTrader
session, encode every CT-19 kind the bound CT-18 supports, read position and
balance back as CT-13 `data quality`, and claim FX paper on the vendor demo
host without a local matcher, a twin, or live money.

**FRs covered:** FR-C01, FR-C02, FR-C03, FR-C04, FR-C05, FR-C06, FR-C07

**Notes:** Extends Epics 24–28; does not rewrite them. Base
`integration@1b451a8`. Reuse COMP-QMN + COMP-QMF-VENUE. Grok epic-factory
lane, same as node Epics 24–30, once the operator starts that lane — this
sitting does not run it.

### Stories in epics.md that this increment extends (do not duplicate)

| Existing story | What it already delivered | What CONNECT must not redo | What CONNECT closes |
|---|---|---|---|
| 24.1 | Transport, `VenueClientPort`, conformance double, DEC-0243 exemption | New port, new loop, SDK | — |
| 24.2 | CT-18 verify-or-refuse | Verification suite rewrite | — |
| 24.3 | Live decode/record; FTR-01 left position/balance unaccepted; submit sensing-only | Decode/error-map | FTR-01 (31.5); sensing-only submit (31.4) |
| 24.5 | Command identity, protective-stop-at-placement, no retry | Ordinal / fingerprint / pacer | Wire handoff 24.5 assumed (31.4) |
| 24.6–24.9 | UNKNOWN, amend, reconnect, edge dispositions | Those paths | Encode must obey SCN-0005 (31.4) |
| 26.5 | Book PAPER → paired demo, `world=live`, no twins | Paper routing / demotion | Honest submit+read-back on that route (31.6) |
| 26.6 | Four-verdict fold + residuals | Fold arithmetic | Read-backs the fold consumes (31.5) |
| 27.2 | Intake; FTR-01 block on mapping | Bootstrap / Dukascopy | Mapping onto `data quality` (31.5) |
| 28.2 | Live roster entry is sensing-only until live binding | Soak deploy | Honest *demo* paper (31.6); live stays sensing-only |
| 28.8 | Unattended week, no profit gate | The week itself | 31.6 is a precondition of an honest paper claim |

## Epic 31: Honest FX paper on the existing cTrader adapter

The operator can fail-closed-select a live venue, open a production cTrader
session, encode every CT-19 kind the bound CT-18 supports, read position and
balance back as CT-13 `data quality`, and claim FX paper on the vendor demo
host without a local matcher, a twin, or live money. This is the first CONNECT
code lane. It uses the read-only inventory at
`integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` and never modifies the
`integration` branch.

**Factory touch ownership (while parallel with 25/26/27):** exclusive writable
surface is `qmn/src/qmn/venue/port.py`, `qmn/src/qmn/venue/live.py`
(open_session / submit / reconcile), ProtoOA encode symbols completing
`packages/qmf-venue/src/qmf/venue/connection.py` (and sibling encode module if
one is extracted under `qmf.venue`), `qmn/src/qmn/data/mapping.py` FTR-01 rows,
`qmn/src/qmn/reconcile/journal.py` mapping, plus the `select_venue_client`
call-site arguments in `qmn/config/roster.py` and `qmn/replay/session.py`.
Must not edit Epic 24 loop/orderpath, Epic 25 compiler/units, Epic 26
protection/ledger origination, Epic 27 secrets/backup, or Epic 28 manifests.

### Story 31.1: Fail-closed live selection by roster VenueClientKind

As a QMX operator,
I want live venue selection to read an explicit roster `VenueClientKind` and to refuse anything else,
So that an unknown live `VenueId` cannot open a cTrader socket.

**Traceability:** FR-C01, FR-C05, FR-C06, NFR-C01.

**Acceptance Criteria:**

**Given** `qmn.venue.port.select_venue_client` at `1b451a8` (else-branch assigns `VenueClientKind.CTRADER`)
**When** this story lands
**Then** implementation is selected by the pair `(world, VenueId)` plus the explicit roster field `VenueClientKind` on a live binding, never by `VenueId` spelling alone
**And** the else-branch that defaults CTRADER is gone. (FR-C01; DEC-0263)

**Given** `world = replay` and any `VenueId`
**When** selection runs
**Then** the result is `VenueClientKind.REPLAY` and the composition refuses to bind CTRADER or CONFORMANCE
**And** a roster `VenueClientKind` on a replay binding cannot override that. (TN-21; FR-061)

**Given** `world = simulated`
**When** selection runs
**Then** the result is `unsupported capability`
**And** no `VenueClientPort` is constructed. (DEC-0110)

**Given** `world = live` and roster field `VenueClientKind = ctrader`
**When** selection runs
**Then** the result is `VenueClientKind.CTRADER`
**And** CTRADER is illegal for any other field value. (FR-C01)

**Given** `world = live` and (`VenueClientKind = conformance` or `VenueId` value starts with `conformance:`)
**When** selection runs
**Then** the result is `VenueClientKind.CONFORMANCE`
**And** the `conformance:` prefix remains the credential-free convention. (TN-11)

**Given** `world = live` and the roster field is absent, empty, unknown, or any value other than `ctrader` | `conformance` (and the `VenueId` is not a `conformance:` prefix)
**When** selection runs
**Then** the result is `unsupported capability` with a typed refusal naming the field and the given value
**And** no cTrader client is constructed and no socket is opened. (NFR-C01)

**Given** a live `VenueId` whose spelling looks like a cTrader broker but whose roster field is not `ctrader`
**When** selection runs
**Then** it is `unsupported capability`
**And** no test infers kind from spelling. (FR-C05; AD-9)

**Given** `VenueClientKind`
**When** the enum is inspected
**Then** the members remain exactly `ctrader`, `replay`, `conformance`
**And** no fourth member is minted. (FR-C05; DEC-0267)

**Given** live-binding call sites (`qmn.config.roster` and any compose path that today calls `select_venue_client(world, venue_id)`)
**When** they compile a live binding
**Then** they pass the explicit roster field into selection
**And** this story does not redesign the Epic 25 config compiler. (AR-C03)

**Given** Tier 1 and isolated Tier 2
**When** they run from a clean install on the code-carrying branch
**Then** they pass with no external call
**And** Spotware token, VPS, and UI are not prerequisites. (NFR-C05)

### Story 31.2: Open production sessions through connect_open_api

As a node runtime,
I want the production live client to open cTrader sessions through `ConnectionManager.connect_open_api`,
So that CONNECT is a real node act rather than a tests-only helper.

**Traceability:** FR-C03, FR-C06, NFR-C02, NFR-C06.

**Acceptance Criteria:**

**Given** `ConnectionManager.connect_open_api` at `1b451a8` (defined, no production caller)
**When** `LiveCTraderClient.open_session` runs on the node's injected asyncio loop
**Then** it calls `connect_open_api` (direct asyncio TLS, Open API port 5035, proto tag 91, protobuf `==7.36.0`)
**And** it never creates a second event loop or a second connection manager. (FR-C03; DEC-0243; NFR-C06)

**Given** production (non-test) code under `qmn/`
**When** callers of `connect_open_api` are enumerated
**Then** `qmn.venue.live` is a caller
**And** a tests-only-only caller surface is a connect bug. (DEC-0265)

**Given** secrets
**When** the session opens
**Then** the client passes opaque credential references; `ConnectionManager` remains the sole in-memory value holder
**And** no secret value appears in config, logs, refusals, or fingerprints. (NFR-C02; CT-21)

**Given** the FEAT-0023 conformance double or the existing tests-only `ConnectionManager` constructor
**When** credential-free acceptance runs
**Then** session lifecycle still proves without network or token
**And** the tagged live-session smoke against `demo.ctraderapi.com` is separately gated by AR-C08. (NFR-C05)

**Given** `world = replay`
**When** compose runs
**Then** no venue-connecting client is constructed and `connect_open_api` is not invoked
**And** Story 31.1's replay refusal still holds. (TN-21)

**Given** DEC-0242
**When** package layout is inspected
**Then** `VenueClientPort` remains node-minted in `qmn.venue`
**And** it is not realized inside `qmf-venue`. (FR-C06)

### Story 31.3: Encode the five CT-19 kinds inside ConnectionManager

As a node developer,
I want ProtoOA encode symbols for the five CT-19 kinds to live in `qmf-venue`,
So that the live client can translate a `Command` without compiling proto itself.

**Traceability:** FR-C03, FR-C07, NFR-C06, AR-C06.

**Acceptance Criteria:**

**Given** the existing `ConnectionManager` and in-house proto tag 91
**When** encode symbols for `place_order`, `cancel_order`, `close_position`, `close_all`, and `amend_protection` land
**Then** they live in `qmf-venue` (on `ConnectionManager` or a sibling `qmf.venue` module imported only by `qmn.venue`)
**And** they emit ProtoOA messages for Open API 5035 without Spotware SDK, CCXT, Hummingbot, or Twisted. (FR-C03; AR-C06)

**Given** `qmn.venue.live`
**When** import and AST/static gates run
**Then** that module translates a `Command` onto those symbols and does not import generated proto modules or compile proto messages itself
**And** `qmn.venue` remains the sole `qmf-venue` importer. (DEC-0241; NFR-C07)

**Given** a `CompoundCommand`
**When** encode/submit is attempted
**Then** FTR-02 remains the existing unsupported-capability block (GAP-0059)
**And** this story does not annotate the compound all-rejected contract. (FR-C07)

**Given** money, price, and volume fields on a `Command`
**When** they are encoded
**Then** they cross only declared exact-integer scale boundaries (AD-7)
**And** a float crossing without a declared rounding rule is refused. (NFR-C04; FR-001 inheritance)

**Given** `packages/qmf-venue` dependencies
**When** the lockfile is inspected
**Then** protobuf remains `==7.36.0`
**And** 7.36.1 is not adopted. (NFR-C06; AR-C05 A4)

**Given** Tier 1 encode unit tests with fixtures (no network)
**When** they run
**Then** each of the five kinds produces a well-formed encode result or a typed refusal naming the missing CT-18 capability
**And** no test requires a Spotware token. (NFR-C05)

### Story 31.4: Hand a ready live submit to the encode path

As a QMX operator,
I want `LiveCTraderClient.submit` to encode a well-formed CT-19 command once session and capabilities are ready,
So that sensing-only CONNECT cannot be called paper.

**Traceability:** FR-C02, FR-C03, FR-C07, NFR-C01.

**Acceptance Criteria:**

**Given** `LiveCTraderClient.submit` at `1b451a8` (returns `unsupported capability` after session and capabilities are ready, reason "Story 24.3 sensing-only")
**When** this story lands
**Then** that sensing-only refusal is gone for every CT-19 kind the bound CT-18 declaration supports
**And** submit hands a well-formed `Command` to the Story 31.3 encode path. (FR-C03; DEC-0265)

**Given** session closed or capabilities unverified
**When** submit is called
**Then** it still returns `unavailable dependency` (retryability after `open_session` then `verify_capabilities`)
**And** it does not encode or open a socket to skip readiness. (Story 24.2 substrate)

**Given** a CT-19 kind the bound CT-18 declaration omits
**When** submit is called after readiness
**Then** `unsupported capability` remains legal
**And** that is the only remaining unsupported-capability submit for a single-kind `Command`. (FEAT-0023; FR-C03)

**Given** a `CompoundCommand`
**When** submit is called
**Then** the FTR-02 block remains
**And** no worker chooses a compound outcome. (FR-C07; GAP-0059)

**Given** command identity persisted by Story 24.5
**When** wire handoff occurs
**Then** no command is retried after handoff; UNKNOWN remains a state (SCN-0005); timeout is not translated into reject
**And** this story does not re-implement ordinals, fingerprints, or the pacer. (AR-C04; AR-C10)

**Given** `place_order` whose CT-18 profile cannot prove a venue-resident protective stop in the required form
**When** submit is attempted
**Then** the entry is refused before encode/handoff
**And** Story 24.5's unprotected-entry law still holds. (TN-6)

**Given** the conformance double
**When** the shared port suite runs submit for each supported kind
**Then** live client and double agree on refusal shape versus encode-handoff
**And** credentialed live submit remains a separately tagged acceptance. (NFR-C05)

### Story 31.5: Close FTR-01 and return four-verdict reconciliation

As a QMX operator,
I want position and balance read-backs journaled as CT-13 `data quality` and `reconcile()` to return a four-verdict `Reconciliation`,
So that soak drift checks can run without an eighth journal type.

**Traceability:** FR-C04, NFR-C03, NFR-C04, AR-C09.

**Acceptance Criteria:**

**Given** FTR-01 blocks at `1b451a8` (`LiveCTraderClient.reconcile` and `qmn.data.mapping` return `unsupported capability` with `ftr=FTR-01`)
**When** this story lands
**Then** those FTR-01 refusals for `position-read-back` and `balance-read-back` are gone
**And** Stories 24.3 and 27.2 in `epics.md` are not rewritten. (AR-C09; DEC-0266)

**Given** CT-20 observation kinds `position-read-back` and `balance-read-back`
**When** they are mapped onto CT-13
**Then** the versioned table maps them onto event type `data quality`
**And** CT-13's seven types are unchanged — no type named `observation`, no eighth type, no second catalog. (FR-C04; AR-C05 A3)

**Given** `LiveCTraderClient.reconcile()` after an open session
**When** it runs over the declared lookback (CT-18 do-not-default parameter)
**Then** it returns `Reconciliation` with verdict exactly `reconciled | drift | unknown | out-of-lookback`
**And** it no longer returns `unsupported capability` for those kinds. (FR-060 unblocked; DEC-0258)

**Given** inbound position or balance read-backs
**When** they are recorded
**Then** the verbatim wire evidence is persisted and journaled as `data quality` before interpretation
**And** the adapter never synthesizes the observations. (NFR-C03)

**Given** an attempt to mint a journal type `observation` or any type outside the seven
**When** mapping or journal append runs
**Then** it is refused
**And** DEC-0247's word "observation" is treated as the CT-20 kind name only. (NFR-C04)

**Given** quantity residual and cash residual
**When** they are reported
**Then** they remain Story 26.6's exact-integer pair; this story does not re-implement the fold
**And** venue equity is never subtracted from virtual-ledger equity. (AR-C04)

**Given** Tier 1 mapping and reconcile tests (double or fixtures)
**When** they run
**Then** both kinds journal as `data quality` and all four verdicts are constructible
**And** no network token is required. (NFR-C05)

### Story 31.6: Prove the honest FX paper claim without live money

As a QMX operator,
I want an executable definition of honest FX paper on the vendor demo host,
So that soak and later factory lanes cannot call sensing-only CONNECT "paper" and cannot skip spot FX.

**Traceability:** FR-C02, FR-C05, FR-C06, FR-C07, AR-C06, AR-C07.

**Acceptance Criteria:**

**Given** Stories 31.1–31.5
**When** an FX paper claim is asserted
**Then** every element is present: vendor host `demo.ctraderapi.com`; `AccountRole.DEMO`; `world = live`; `VenueClientKind = ctrader`; `LiveCTraderClient` (the same implementation used for live); submit encode of every CT-19 kind the bound CT-18 supports; position and balance read-back per Story 31.5
**And** absence of any element fails the claim. (FR-C02; DEC-0264)

**Given** Book PAPER routing from Story 26.5
**When** intents are routed
**Then** they still go to exactly one paired demo account with its own BMS and virtual ledger
**And** no Bot or Book twin and no local matching engine is minted. (FR-058; AR-C06)

**Given** a live-role roster entry with credentials (TN-9)
**When** it is composed
**Then** it remains sensing and recording only until a live binding — no live command stream, sequencer, or execution target
**And** this story grants no live-money, promotion, or go-live authority. (FR-C06; Story 28.2)

**Given** live-capital size or "spot FX later" as a proposed skip
**When** the adapter or paper claim is evaluated
**Then** neither is a legal skip
**And** spot FX stays in. (FR-C02; AR-C05 A1)

**Given** a non-cTrader `VenueId` or a proposed fourth `VenueClientKind`
**When** compose or selection runs
**Then** it is `unsupported capability` or out of scope — never config-mapped onto `LiveCTraderClient`
**And** no exchange is picked; GAP-0060 stays deferred (canonical source token remains `ctrader`). (FR-C05; FR-C07)

**Given** `qmb`, `qml`, and QMA packages
**When** import gates run
**Then** none import `qmf-venue`
**And** only `qmn.venue` does. (NFR-C07)

**Given** Epic 28 soak readiness
**When** a paper claim is a soak precondition
**Then** Story 31.6 green is required before the unattended week may call the demo path "paper"
**And** this story does not run the week, invent KSA values, or treat profit as evidence. (FR-059; AR-C07)

**Given** the dead list (CCXT, Hummingbot, Spotware SDK, Twisted, DEC-0242 realization, protobuf 7.36.1, FTR-02 close, UI, MIS, Book/BMS redesign)
**When** the diff is reviewed
**Then** none of those appear
**And** cheap-veto A1–A5 remain unoverturned. (AR-C05; AR-C06)

## Validation

- All seven CONNECT FRs map to Epic 31 stories; inherited FR-058/059/060/061/062 are cited not re-owned.
- UX-DR list empty — no UX input.
- No starter template — brownfield completion, Story 31.1 is fail-closed selection not a scaffold.
- One epic: same core files; split was considered and rejected (file-churn rule).
- Story order has no forward dependencies: 31.2 uses 31.1; 31.3 encode is independently testable after 31.2 session locus; 31.4 uses 31.3; 31.5 uses 31.2 session and does not need 31.4; 31.6 uses 31.1–31.5.
- Epic 31 functions without Epic 32 (there is none) and without rewriting Epics 24–28.
- Architecture compliance: reuse COMP-QMN + COMP-QMF-VENUE; AD-1..AD-5; DEC-0263..0268; dead list honored.
- `epics.md` and `epics-QMA-2026-08-29.md` were not written.
