---
id: ADR-0021
title: CONNECT FX paper — hexagonal port completion on the existing cTrader adapter
type: adr
status: ratified
component: COMP-QMN
depends_on: [COMP-QMF-VENUE, COMP-CTRADER]
decisions: [DEC-0263, DEC-0264, DEC-0265, DEC-0266, DEC-0267, DEC-0268]
sources: [_bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/.memlog.md, _bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/reviews/reconcile-inputs.md, workroom/research/2026-09-11_connect-architecture-result.md, workroom/research/2026-09-11_connect-architecture-handoff.md, docs/decisions/ADR-0019-trading-node.md, docs/components/trading-node.md, docs/components/qmf-venue.md, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-13-journal.yaml, _docwork/ledger.yaml]
generated: 2026-09-11
verified: 2026-09-11
stale_after: 1y
---

# ADR-0021: CONNECT FX paper — hexagonal port completion on the existing cTrader adapter

Date: 2026-09-11. Status: accepted.

## Context

QMX already has a trading node (`COMP-QMN`) that mints `qmn.venue.VenueClientPort` with three V1 implementations selected by the pair `(world, VenueId)`, and a venue module (`COMP-QMF-VENUE`) whose `ConnectionManager` is the sole session owner (DEC-0196, DEC-0241, DEC-0242, DEC-0243). Brownfield at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` still has four connect defects the NODE spine already forbids in law but that the code still exhibits: unknown live `VenueId` defaults to CTRADER; `LiveCTraderClient.submit` is sensing-only after session and capabilities are ready; FTR-01 blocks position/balance read-back as `unsupported capability`; `connect_open_api` has no production caller (CONNECT AD-1 through AD-4; DEC-0263, DEC-0264, DEC-0265, DEC-0266).

The 2026-09-11 CONNECT architecture sitting produced a child feature spine (`architecture-CONNECT-2026-09-11/ARCHITECTURE-SPINE.md`, status: final) so QMX can CONNECT and honestly FX paper-trade on the existing cTrader adapter. Parents QMX AD-1..AD-41 and NODE TN-1..TN-25 bind read-only. Crypto is plurality on the same port, not an adapter pick and not a Book/BMS sitting. Risk, sizing, MIS, UI, STRATS, and loop-engineering are out of this increment (DEC-0267, DEC-0268).

This ADR records the documentation-factory absorption of that spine. It does not authorize implementation, credentials, a live session, order submission, paper-mode transition, or go-live — those arrive only through the factory pipeline (DEC-0268).

## Options considered

1. **New venue-gateway library / fourth V1 kind / crypto adapter this increment** — a second port, a CCXT/Hummingbot/Spotware-SDK/Twisted client, or a new `VenueClientKind` member. Rejected because: DEC-0241 and L30 already name `qmn.venue` as the sole `qmf-venue` importer; DEC-0013 forbids build-with-theirs; CONNECT AD-5 keeps TN-11's three V1 implementations until a later increment amends them (DEC-0265, DEC-0267).
2. **Realize `VenueClientPort` inside `qmf-venue` while connecting** — rejected because: DEC-0242 stays recorded-not-applied; this increment does not apply that parent amendment (DEC-0265, DEC-0268).
3. **Local matching engine or Bot/Book twin for paper** — rejected because: AD-35 paper is Book-level on the paired demo; CONNECT AD-2 forbids twins and a local matcher (DEC-0264, DEC-0149).
4. **Reuse the existing port and complete the live cTrader implementation in place** — chosen. Hexagonal port completion: one node-minted `VenueClientPort`, fail-closed selection, production `connect_open_api`, CT-19 submit encode, CT-20 position/balance read-back (DEC-0263, DEC-0264, DEC-0265, DEC-0266, DEC-0268).

## Decision

The CONNECT spine AD-1..AD-5 is adopted in full as DEC-0263 through DEC-0267. The umbrella is DEC-0268.

- **CONNECT AD-1 / DEC-0263 — fail-closed live selection.** Implementation is selected by the pair `(world, VenueId)`, never by `VenueId` alone. `world = replay` selects REPLAY for every `VenueId` and the composition refuses any venue-connecting kind. `world = simulated` refuses. `world = live` reads an explicit roster field `VenueClientKind` on that binding — not inferred from `VenueId` spelling. CTRADER is legal only when that field is `ctrader`. CONFORMANCE is legal only when the field is `conformance` or the `VenueId` value starts with `conformance:`. Absent field, unknown kind, or any other live `VenueId` is `unsupported capability`. The integration else-branch that assigns CTRADER is a connect bug, not TN-11.
- **CONNECT AD-2 / DEC-0264 — honest FX paper.** An FX paper claim requires every element: vendor cTrader demo host; `AccountRole.DEMO`; `world = live`; the same live `VenueClientPort` implementation used for live; submit encode of every CT-19 kind the bound CT-18 declaration supports; position and balance read-back per CONNECT AD-4. `LiveCTraderClient.submit` returning `unsupported capability` after session and capabilities are ready is not paper. Live-capital bleeding is not an adapter skip. Spot FX is not deferred. No local matching engine. No Bot or Book twin. Soak remains TN-9. Connection count is derived from the roster (DEC-0244).
- **CONNECT AD-3 / DEC-0265 — encode and session locus.** `qmn.venue` is the sole `qmf-venue` importer (DEC-0241). ProtoOA command encode for the five CT-19 kinds and `connect_open_api` complete the existing `ConnectionManager` in `qmf-venue` (DEC-0243 exemption already applied). Encode symbols live in `qmf-venue`; `qmn.venue.live` translates a `Command` onto those symbols and must not compile proto messages itself. After an open session and verified capabilities, `LiveCTraderClient.submit` hands a well-formed `Command` to that encode path; it does not refuse as Story 24.3 sensing-only. The production node calls `connect_open_api`; a tests-only caller is a connect bug. DEC-0242 stays recorded-not-applied. No CCXT, no Hummingbot, no Spotware SDK, no Twisted.
- **CONNECT AD-4 / DEC-0266 — FTR-01 closed; read-back mapping.** `position-read-back` and `balance-read-back` are CT-20 observation kinds (DEC-0247). They map through CT-20's versioned (observation kind) to event-type table onto CT-13 `data quality`. No eighth journal type. No second catalog. DEC-0247's word "observation" names the CT-20 kind, not a journal type — CT-13's seven do not include observation. `reconcile()` returns the four-verdict `Reconciliation` over the declared lookback and no longer returns `unsupported capability` for those kinds. Adapters never synthesize the observations. Journal type `data quality` is CONNECT assumption A3, cheap-veto (DEC-0266, DEC-0268).
- **CONNECT AD-5 / DEC-0267 — crypto plurality without a fourth V1 kind.** A later non-cTrader live venue is a new CT-18 static declaration plus a new `VenueClientPort` implementation selected by `(world, VenueId)` through CONNECT AD-1. Same four contracts. Same `qmn.venue` import boundary. Adapter code lives in `qmf-venue` and imports only `qmf-core`. This increment does not mint a fourth `VenueClientKind` and does not pick an exchange. TN-22 "second broker is roster" applies to the same protocol family; a new protocol is a later module (L22), never "config onto the cTrader client".

Conflicts are surfaced, not overridden: PRD section 7 node-runtime out-of-V1 vs DEC-0259; PRD section 7 forex-only vs later crypto plurality; DEC-0247 "observation" vs CT-13's seven (interpreted as CT-20 kind, journal = `data quality`); TN-11 three V1 kinds vs L22 (scoped by CONNECT AD-5) (DEC-0268).

## Architecture-preflight verdict

**reuse COMP-QMN** for live client selection (`qmn.venue.port`), FX paper routing (`qmn.paper`), duty scheduling, verification-suite runner, CT-18 fills, error-map rows, and the port implementation (`qmn.venue.live`). **reuse COMP-QMF-VENUE** for `connect_open_api` and ProtoOA command encode on the existing `ConnectionManager`. **reuse COMP-CTRADER** as the external facts boundary (hosts, proto tag 91, Open API 5035) — not an implementation home.

Candidates refused by id:

- **new COMP / third gateway library** — DEC-0241 and L30 already name the importer; DEC-0013 forbids CCXT/SDK.
- **new `VenueClientKind` member** — CONNECT AD-5; TN-11's three V1 implementations stand (DEC-0267).
- **realize the port inside `qmf-venue`** — DEC-0242 recorded-not-applied (DEC-0265).
- **COMP-QMB / COMP-QML** — they keep the `qmf-venue` ban (DEC-0241).
- **COMP-QMA-CORE / COMP-QMA-WIRE / COMP-QMA-DAEMON** — money-path barrier; no `qmf-venue` import (DEC-0341, DEC-0347).
- **COMP-QMF-RISK / Book / BMS** — out of sitting; paper stays AD-35 Book-level (DEC-0264).

Dead list honored: CCXT, Hummingbot, Spotware SDK, Twisted, local matching engine, Bot/Book twins, paper as sensing-only, unknown-live-VenueId-defaults-CTRADER (DEC-0263, DEC-0264, DEC-0265).

No existing component's authority shrinks. No new dependency edge. No new contract id. CT-13/CT-18/CT-19/CT-20/CT-21 take CONNECT usage annotations only.

## Consequences

Easier: factory units can complete FX paper on the existing adapter without minting a fourth kind or a gateway library; soak drift checks can run because FTR-01 closes; unknown live `VenueId` cannot open a cTrader socket.

Harder: live selection must carry an explicit roster `VenueClientKind`; encode must live in `qmf-venue` symbols; production must call `connect_open_api`; CT-20 mapping rows for the two read-back kinds journal as CT-13 `data quality`, never as a journal type named observation.

Foreclosed: config-mapping a non-cTrader `VenueId` onto `LiveCTraderClient`; extracting a third library; skipping spot FX; calling sensing-only CONNECT "paper"; minting an eighth journal type.

Blast radius (change mode): `COMP-QMN`, `COMP-QMF-VENUE`, `COMP-CTRADER`, and every doc declaring a dependency on them. Primary edits: this ADR, `docs/components/trading-node.md`, `docs/components/qmf-venue.md`, `docs/components/ctrader.md`, CT-13/CT-18/CT-19/CT-20/CT-21, constitution L21/L22/L30 annotations, architecture overview and stack, glossary, gap report, traceability, index, AGENTS.md, changelog, SCN-0005, and `_docwork/` (ledger DEC-0263..DEC-0268, gaps GAP-0059/GAP-0060, feature FEAT-0032, SRC-16). Feature `FEAT-0032` is the implementing slice; implementation authorization remains factory-pipeline-only.

Cheap-veto (CONNECT assumptions A1–A5): A1 FX-first / crypto later; A2 brownfield SHA re-verified at `1b451a8`; A3 journal type is `data quality`; A4 protobuf pin stays `==7.36.0` despite 7.36.1 existing; A5 no PRD amendment this sitting (DEC-0268).
