#!/usr/bin/env python3
"""Append CONNECT change-mode YAML. Run once from project root. Idempotent by id."""
from pathlib import Path

ROOT = Path(r"C:/Users/Mubarak/Desktop/QMX")


def already(text: str, needle: str) -> bool:
    return needle in text


def append_if_missing(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if already(text, marker):
        print(f"skip {path.name}: {marker} already present")
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")
    print(f"appended {marker} -> {path.name}")


EXTR = r"""
  - id: EXT-2172
    type: decision
    summary: "CONNECT AD-1 FAIL-CLOSED LIVE SELECTION. Implementation is selected by the pair (world, VenueId), never by VenueId alone. world=replay selects REPLAY for every VenueId and refuses venue-connecting kinds. world=simulated refuses. world=live reads an explicit roster field VenueClientKind on that binding — not inferred from VenueId spelling. CTRADER is legal only when that field is ctrader. CONFORMANCE is legal only when the field is conformance or the VenueId value starts with conformance:. Absent field, unknown kind, or any other live VenueId is unsupported capability. The integration else-branch that assigns CTRADER is a connect bug, not TN-11."
    quote: "world = live reads an explicit roster field VenueClientKind on that binding — not inferred from VenueId spelling."
    cite: SRC-16:ARCHITECTURE-SPINE.md#ad-1
    topics: [connect, venue-selection, VenueClientKind, fail-closed]
    authority: rider
  - id: EXT-2173
    type: decision
    summary: "CONNECT AD-2 HONEST FX PAPER. An FX paper claim requires every element: vendor cTrader demo host; AccountRole.DEMO; world=live; the same live VenueClientPort implementation used for live; submit encode of every CT-19 kind the bound CT-18 declaration supports; position and balance read-back per CONNECT AD-4. LiveCTraderClient.submit returning unsupported capability after session and capabilities are ready is not paper. Live-capital bleeding is not an adapter skip. Spot FX is not deferred. No local matching engine. No Bot or Book twin. Soak remains TN-9. Connection count derived from the roster (DEC-0244)."
    quote: "an FX paper claim requires every element: vendor cTrader demo host; AccountRole.DEMO; world = live; the same live VenueClientPort implementation used for live"
    cite: SRC-16:ARCHITECTURE-SPINE.md#ad-2
    topics: [connect, fx-paper, soak, ct-19]
    authority: rider
  - id: EXT-2174
    type: decision
    summary: "CONNECT AD-3 ENCODE AND SESSION LOCUS. qmn.venue is the sole qmf-venue importer (DEC-0241). ProtoOA command encode for the five CT-19 kinds and connect_open_api complete the existing ConnectionManager in qmf-venue (DEC-0243 exemption already applied). Encode symbols live in qmf-venue; qmn.venue.live translates a Command onto those symbols and must not compile proto messages itself. After an open session and verified capabilities, LiveCTraderClient.submit hands a well-formed Command to that encode path; it does not refuse as Story 24.3 sensing-only. The production node calls connect_open_api; a tests-only caller is a connect bug. DEC-0242 stays recorded-not-applied. No CCXT, no Hummingbot, no Spotware SDK, no Twisted."
    quote: "ProtoOA command encode for the five CT-19 kinds and connect_open_api complete the existing ConnectionManager in qmf-venue"
    cite: SRC-16:ARCHITECTURE-SPINE.md#ad-3
    topics: [connect, encode, ConnectionManager, connect_open_api, DEC-0241]
    authority: rider
  - id: EXT-2175
    type: decision
    summary: "CONNECT AD-4 FTR-01 CLOSED. position-read-back and balance-read-back are CT-20 observation kinds (DEC-0247). They map through CT-20's versioned table onto CT-13 data quality. No eighth type. No second catalog. DEC-0247's word observation names the CT-20 kind, not a journal type. reconcile() returns the four-verdict Reconciliation over the declared lookback and no longer returns unsupported capability for those kinds. Adapters never synthesize the observations. [ASSUMPTION A3 — journal type is data quality.]"
    quote: "They map through CT-20's versioned (observation kind) to event-type table onto CT-13 data quality. No eighth type."
    cite: SRC-16:ARCHITECTURE-SPINE.md#ad-4
    topics: [connect, FTR-01, ct-20, ct-13, data-quality, DEC-0247]
    authority: rider
  - id: EXT-2176
    type: decision
    summary: "CONNECT AD-5 CRYPTO PLURALITY WITHOUT A FOURTH V1 KIND. A later non-cTrader live venue is a new CT-18 static declaration plus a new VenueClientPort implementation selected by (world, VenueId) through CONNECT AD-1. Same four contracts. Same qmn.venue import boundary. Adapter code lives in qmf-venue and imports only qmf-core. This increment does not mint a fourth VenueClientKind and does not pick an exchange. TN-11's three V1 implementations stand. TN-22 second broker is roster for the same protocol family; a new protocol is a later module (L22), never config onto the cTrader client."
    quote: "This increment does not mint a fourth VenueClientKind and does not pick an exchange."
    cite: SRC-16:ARCHITECTURE-SPINE.md#ad-5
    topics: [connect, plurality, L22, VenueClientKind, crypto]
    authority: rider
  - id: EXT-2177
    type: context
    summary: "CONNECT brownfield verified on integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 via git show (no checkout). Defects this spine forbids, not seed to copy: live submit sensing-only; FTR-01 blocks reconcile; unknown live VenueId defaults CTRADER; connect_open_api has no production caller; SessionTopology ClassVar=2; protobuf==7.36.0 in qmf-venue."
    quote: "Those are defects this spine forbids, not seed to copy."
    cite: SRC-16:ARCHITECTURE-SPINE.md#structural-seed
    topics: [connect, brownfield, integration]
    authority: rider
  - id: EXT-2178
    type: constraint
    summary: "CONNECT conflicts surfaced not overridden: (1) PRD section 7 trading-node runtime out of V1 vs NODE spine DEC-0259; (2) PRD section 7 forex-only vs crypto plurality — this increment stays forex; (3) TN-11 THREE V1 kinds vs L22 — CONNECT AD-5 scopes it; (4) DEC-0247 maps to observation vs CT-13 seven — CONNECT AD-4 interprets observation as CT-20 kind, journal = data quality; (5) code FTR-01 refuse vs docs DEC-0247 APPLIED — CONNECT AD-4 closes the code gap; (6) select_venue_client else CTRADER vs TN-11 — CONNECT AD-1; (7) connect_open_api tests-only vs TN-11 production transport — CONNECT AD-3."
    quote: "Conflicts surfaced not overridden"
    cite: SRC-16:.memlog.md
    topics: [connect, conflicts, PRD, DEC-0247]
    authority: rider
  - id: EXT-2179
    type: open
    summary: "CONNECT assumptions A1-A5 (cheap-veto): A1 this sitting is CONNECT + honest FX paper; crypto plurality is invariant not an in-sitting adapter pick. A2 2026-09-09 packet brownfield claims re-verified against git show. A3 journal mapping for position/balance read-back is CT-13 data quality. A4 protobuf pin stays ==7.36.0 despite 7.36.1 existing. A5 no PRD amendment in this sitting."
    quote: "[ASSUMPTION A3] Journal mapping for position/balance read-back is CT-13 data quality."
    cite: SRC-16:.memlog.md
    topics: [connect, assumptions, cheap-veto]
    authority: rider
  - id: EXT-2180
    type: open
    summary: "CONNECT Deferred table (non-blocking): crypto exchange pick and fourth VenueClientKind; PRD section 7 asset-class amendment; Book/BMS/sizing/crypto market-hours; MIS (GAP-0051); UI/Penpot; STRATS/loop-engineering; FTR-02 compound-command annotation; canonical live source parameterization off hardcoded ctrader; protobuf 7.36.1 bump; SessionTopology ClassVar=2 in code (DEC-0244 already binds); FX live binding/live money; realizing VenueClientPort inside qmf-venue (DEC-0242 RNA); intake of non-Dukascopy history."
    quote: "Crypto exchange pick and fourth VenueClientKind — AD-5 plurality law is enough; FX paper first"
    cite: SRC-16:ARCHITECTURE-SPINE.md#deferred
    topics: [connect, deferred, FTR-02]
    authority: rider
  - id: EXT-2181
    type: value
    summary: "CONNECT stack SEED verified 2026-09-11: CPython 3.14 inherited; protobuf runtime ==7.36.0 in qmf-venue only (7.36.1 exists 2026-08-31 and is not adopted here); cTrader Open API Protobuf TCP port 5035; hosts demo.ctraderapi.com and live.ctraderapi.com; proto artifact Spotware integer tag 91 compiled in-house; uv/qmn existing workspace member, no new distribution. Code owns the pin once it exists."
    quote: "protobuf runtime ==7.36.0 in qmf-venue only; 7.36.1 exists 2026-08-31 and is not adopted here"
    cite: SRC-16:ARCHITECTURE-SPINE.md#stack
    topics: [connect, protobuf, stack, ctrader-hosts]
    authority: rider
  - id: EXT-2182
    type: decision
    summary: "CONNECT spine finalized status:final 2026-09-11. Paradigm: hexagonal port completion (composition-root adapter). Child of architecture-QMX-2026-08-19 and architecture-NODE-2026-08-28. Preflight: reuse COMP-QMN + COMP-QMF-VENUE; no new component; no new port; no third library. Captain brief next skill is documentation-factory in a new session."
    quote: "Hexagonal port completion (composition-root adapter). The NODE paradigm stands: one systemd-supervised process is the only impure shell; qmn.venue.VenueClientPort is the only injectable venue seam."
    cite: SRC-16:ARCHITECTURE-SPINE.md#design-paradigm
    topics: [connect, spine-final, preflight, reuse]
    authority: rider
"""

LEDGER = r"""
  - id: DEC-0263
    title: "CONNECT AD-1 — Fail-closed live selection"
    statement: "Implementation of qmn.venue.VenueClientPort is selected by the pair (world, VenueId), never by VenueId alone (TN-11). world = replay selects REPLAY for every VenueId and the composition refuses any venue-connecting kind. world = simulated refuses. world = live reads an explicit roster field VenueClientKind on that binding — not inferred from VenueId spelling. CTRADER is legal only when that field is ctrader. CONFORMANCE is legal only when the field is conformance or the VenueId value starts with conformance: (the existing credential-free convention). Absent field, unknown kind, or any other live VenueId is unsupported capability. The integration else-branch that assigns CTRADER is a connect bug, not TN-11."
    status: ratified
    rationale: "Prevents an unknown live VenueId opening a cTrader client and two units inventing different live defaults. TN-2 compose and TN-11 pair selection stand; the live default-to-CTRADER is an implementation accident not that law. CONNECT sitting 2026-09-11, spine status final."
    sources: [EXT-2172, EXT-2177, EXT-2182]
    authority: rider
    component: COMP-QMN
    tags: [connect, venue-selection, fail-closed, VenueClientKind, tn-11]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md#ad-1"

  - id: DEC-0264
    title: "CONNECT AD-2 — Honest FX paper"
    statement: "An FX paper claim requires every element: vendor cTrader demo host; AccountRole.DEMO; world = live; the same live VenueClientPort implementation used for live; submit encode of every CT-19 kind the bound CT-18 declaration supports; position and balance read-back per DEC-0266. LiveCTraderClient.submit returning unsupported capability after session and capabilities are ready is not paper. Live-capital bleeding is not an adapter skip. Spot FX is not deferred. No local matching engine. No Bot or Book twin. Soak remains TN-9: the demo connection carries the order path; the live connection, when credentials exist, is sensing and recording only until a live binding. Connection count is derived from the roster (DEC-0244): a soak roster may name one (venue, environment) pair."
    status: ratified
    rationale: "Prevents sensing-only CONNECT being called paper and skipping spot FX because live capital is small. Paper remains Book-level (AD-35 / DEC-0149). CONNECT sitting 2026-09-11, spine status final."
    sources: [EXT-2173, EXT-2177, EXT-2182]
    authority: rider
    component: COMP-QMN
    tags: [connect, fx-paper, soak, ad-35, tn-9]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md#ad-2"

  - id: DEC-0265
    title: "CONNECT AD-3 — Encode and session locus"
    statement: "qmn.venue is the sole qmf-venue importer (DEC-0241). ProtoOA command encode for the five CT-19 kinds and connect_open_api complete the existing ConnectionManager in qmf-venue (DEC-0243 exemption already applied). Encode symbols live in qmf-venue; qmn.venue.live translates a Command onto those symbols and must not compile proto messages itself. qmn.venue also holds duty scheduling, the verification-suite runner, CT-18 fills, error-map rows, and the port implementation. After an open session and verified capabilities, LiveCTraderClient.submit hands a well-formed Command to that encode path; it does not refuse as Story 24.3 sensing-only. A CT-19 kind the bound CT-18 declaration supports that remains sensing-only is a connect bug. The production node calls connect_open_api; a tests-only caller is a connect bug. DEC-0242 stays recorded-not-applied. No CCXT, no Hummingbot, no Spotware SDK, no Twisted."
    status: ratified
    rationale: "Prevents a third venue-gateway library, a second connection manager, and command encode outside the sanctioned boundary. CONNECT sitting 2026-09-11, spine status final."
    sources: [EXT-2174, EXT-2177, EXT-2182]
    authority: rider
    component: COMP-QMF-VENUE
    tags: [connect, encode, ConnectionManager, connect_open_api, DEC-0241, DEC-0242, DEC-0243]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md#ad-3"

  - id: DEC-0266
    title: "CONNECT AD-4 — FTR-01 closed: position/balance read-back maps to CT-13 data quality"
    statement: "position-read-back and balance-read-back are CT-20 observation kinds (DEC-0247). They map through CT-20's versioned (observation kind) to event-type table onto CT-13 data quality. No eighth journal type. No second catalog. DEC-0247's word observation names the CT-20 kind, not a journal type — CT-13's seven (decision, order, fill, risk transition, promotion, data quality, control action) do not include observation; that wording collision is surfaced here and is not a license to mint. reconcile() returns the four-verdict Reconciliation over the declared lookback and no longer returns unsupported capability for those kinds. Adapters never synthesize the observations. Journal type data quality is CONNECT assumption A3, individually overturnable without unwinding DEC-0247."
    status: ratified
    rationale: "Prevents an eighth journal type, two units mapping position/balance onto different types, and soak drift checks that cannot run. Interprets DEC-0247; does not supersede it. CONNECT sitting 2026-09-11, spine status final."
    sources: [EXT-2175, EXT-2178, EXT-2179, EXT-2182]
    authority: rider
    component: COMP-QMF-VENUE
    tags: [connect, FTR-01, ct-20, ct-13, data-quality, DEC-0247, assumption-a3]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md#ad-4"

  - id: DEC-0267
    title: "CONNECT AD-5 — Crypto plurality without a fourth V1 kind"
    statement: "A later non-cTrader live venue is a new CT-18 static declaration plus a new VenueClientPort implementation selected by (world, VenueId) through DEC-0263. Same four contracts. Same qmn.venue import boundary. Adapter code lives in qmf-venue and imports only qmf-core. This increment does not mint a fourth VenueClientKind and does not pick an exchange. TN-11's three V1 implementations (CTRADER, REPLAY, CONFORMANCE) stand until a later increment amends them. TN-22 second broker is roster applies to the same protocol family; a new protocol is a later module (L22), never config onto the cTrader client."
    status: ratified
    rationale: "Prevents config-mapping a non-cTrader VenueId onto LiveCTraderClient, extracting a gateway library, and Book/BMS/sizing redesign under CONNECT. Conflict TN-11 THREE vs L22 is scoped, not overridden. CONNECT sitting 2026-09-11, spine status final."
    sources: [EXT-2176, EXT-2178, EXT-2180, EXT-2182]
    authority: rider
    component: COMP-QMN
    tags: [connect, plurality, L22, VenueClientKind, crypto]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md#ad-5"

  - id: DEC-0268
    title: "CONNECT FX-paper spine adopted in full (hexagonal port completion; reuse COMP-QMN and COMP-QMF-VENUE)"
    statement: "The 2026-09-11 CONNECT child feature spine (architecture-CONNECT-2026-09-11, status final) is adopted in full as DEC-0263 through DEC-0267. Paradigm is hexagonal port completion: one systemd-supervised process remains the only impure shell; qmn.venue.VenueClientPort remains the only injectable venue seam; this increment does not mint a second port, a second runtime, or a gateway library. Preflight verdict is reuse COMP-QMN (selection, paper routing, duty scheduling, verify, CT-18 fills, error-map, live client) and reuse COMP-QMF-VENUE (connect_open_api and ProtoOA encode on the existing ConnectionManager). No new component. No new contract id. No new dependency edge. Parents QMX AD-1..AD-41 and NODE TN-1..TN-25 bind read-only. Brownfield defects at integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 (else-branch CTRADER, sensing-only submit, FTR-01 refuse, tests-only connect_open_api) are connect bugs this spine forbids, not seed to copy. Conflicts are surfaced not overridden: PRD section 7 node-runtime OOS vs DEC-0259; PRD section 7 forex-only vs later crypto; DEC-0247 observation vs CT-13 seven (interpreted by DEC-0266); TN-11 THREE vs L22 (scoped by DEC-0267). Stack seed: protobuf==7.36.0 in qmf-venue only; 7.36.1 exists and is not adopted here; Open API 5035 on demo.ctraderapi.com and live.ctraderapi.com; proto tag 91 in-house. Implementation authorization arrives only through the factory pipeline. Cheap-veto assumptions A1-A5 ride this umbrella."
    status: ratified
    rationale: "Operator-directed documentation-factory change-mode absorption of a status:final architecture spine (2026-09-11). The sitting itself was operator-absent with tagged assumptions; those assumptions are the cheap-veto surface, not silent invention."
    sources: [EXT-2182, EXT-2177, EXT-2178, EXT-2179, EXT-2180, EXT-2181]
    authority: rider
    component: COMP-QMN
    tags: [connect, spine-adoption, preflight, reuse, cheap-veto]
    date: 2026-09-11
    spine_ref: "SRC-16:ARCHITECTURE-SPINE.md"
"""

GAPS = r"""
  - id: GAP-0059
    question: "FTR-02 compound-command annotation — when does a CT-19 compound/fan-out command get its parent-meet annotation, and is it required before single-kind FX paper encode ships?"
    needed_by: [COMP-QMF-VENUE, COMP-QMN]
    blocking: false
    recommendation: "Leave the existing compound-command block unchanged; single-kind FX paper encode does not require FTR-02. Revisit when a command that fans out to N venue submissions is in scope."
    status: deferred
    answer: null
    note: "CONNECT Deferred table 2026-09-11 (DEC-0268). Unchanged block; not required for single-kind FX paper encode."
    date: 2026-09-11
  - id: GAP-0060
    question: "When a fourth VenueClientKind exists, how is the canonical live source token parameterized off the hardcoded ctrader value?"
    needed_by: [COMP-QMN]
    blocking: false
    recommendation: "Hardcoded ctrader is correct while only CTRADER connects. Revisit when DEC-0267 mints a kind. Do not parameterize in the FX-paper increment."
    status: deferred
    answer: null
    note: "CONNECT Deferred table 2026-09-11 (DEC-0267, DEC-0268). Canonical live source stays ctrader this increment."
    date: 2026-09-11
"""

FEAT = r'''
  - id: FEAT-0032
    name: "CONNECT FX paper — fail-closed selection, ProtoOA encode, honest demo paper, FTR-01 closed"
    scope: >-
      In: complete the existing live cTrader VenueClientPort so QMX can CONNECT and honestly FX paper-trade
      — fail-closed live selection by the pair (world, VenueId) reading an explicit roster VenueClientKind
      (DEC-0263); honest FX paper as vendor cTrader demo host plus AccountRole.DEMO plus world=live plus
      the same live client plus submit encode of every CT-19 kind the bound CT-18 supports plus
      position/balance read-back (DEC-0264); ProtoOA encode of the five CT-19 kinds and production
      connect_open_api completing qmf-venue ConnectionManager, with qmn.venue the sole qmf-venue
      importer and qmn.venue.live translating Command onto qmf-venue encode symbols without compiling
      proto itself (DEC-0265); FTR-01 closed so position-read-back and balance-read-back are CT-20
      observation kinds mapped onto CT-13 data quality, reconcile() returning the four-verdict
      Reconciliation over the declared lookback (DEC-0266); crypto plurality law without minting a
      fourth V1 kind or picking an exchange (DEC-0267). Out: a new component, a second port, a third
      gateway library, CCXT/Hummingbot/Spotware SDK/Twisted, realizing VenueClientPort inside
      qmf-venue (DEC-0242 stays recorded-not-applied), a local matching engine, Bot/Book twins,
      Book/BMS/sizing/MIS redesign, UI/Penpot, STRATS/loop-engineering, FX live binding / live money,
      PRD section 7 asset-class amendment, protobuf 7.36.1 bump, FTR-02 compound-command annotation,
      canonical live-source parameterization. Done means the four brownfield connect bugs at
      integration@1b451a8 (else-branch CTRADER, sensing-only submit, FTR-01 refuse, tests-only
      connect_open_api) are forbidden by the knowledge base and the implementing stories have a
      cited contract and DEC; implementation authorization still arrives only through the factory
      pipeline.
    decisions: [DEC-0263, DEC-0264, DEC-0265, DEC-0266, DEC-0267, DEC-0268]
    components: [COMP-QMN, COMP-QMF-VENUE]
    blocked_by:
      - id: FEAT-0023
        reason: "CONNECT encode and selection read the CT-18 static declaration FEAT-0023 lands; unsupported capability is legal only where that declaration omits the kind"
      - id: FEAT-0024
        reason: "production connect_open_api and the ConnectionManager session FEAT-0024 lands are the session locus CONNECT AD-3 completes rather than forks"
      - id: FEAT-0026
        reason: "CT-19 five-kind submit and CT-20 reconciliation FEAT-0026 lands are the surface CONNECT closes FTR-01 on and whose sensing-only submit is a connect bug"
      - id: FEAT-0031
        reason: "selection, paper routing, duty scheduling, verify, and the node-minted VenueClientPort live in COMP-QMN as FEAT-0031; CONNECT completes that port in place and does not mint a second one"
    size: multi-pass
    status: planned
    notes: "Absorbed from architecture-CONNECT-2026-09-11 (status final) by the 2026-09-11 documentation-factory change-mode pass (ADR-0021, DEC-0268). Preflight verdict: reuse COMP-QMN and COMP-QMF-VENUE — no new component. Cheap-veto A1-A5 on DEC-0268. GAP-0059 (FTR-02) and GAP-0060 (canonical live source token) deferred non-blocking. Implementation authorization factory-pipeline-only."
'''

SRC16 = r"""
- id: SRC-16
  path: _bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/
  kind: rider
  role: primary
  status: harvested
  note: "2026-09-11 CONNECT FX-paper child feature architecture sitting (operator-absent; spine status final): ARCHITECTURE-SPINE.md (CONNECT AD-1..AD-5 plus Inherited Invariants, Corrections, Consistency Conventions, Stack, Structural Seed, Capability map, Deferred), .memlog.md (sitting open through spine finalized; assumptions A1-A5; conflicts surfaced not overridden), reviews/ (lint, rubric, adversarial, currency, reconcile-inputs). Citation surface for the CONNECT increment (EXT-2172..EXT-2182). Parents architecture-QMX-2026-08-19 and architecture-NODE-2026-08-28 bind read-only. Companion captain brief workroom/research/2026-09-11_connect-architecture-result.md and handoff workroom/research/2026-09-11_connect-architecture-handoff.md. The 2026-09-09 crypto-connect packet is INPUT not law."
"""

CHANGE_MODE = r"""
- date: '2026-09-11'
  change: "Absorb the 2026-09-11 CONNECT FX-paper architecture sitting (child feature spine CONNECT AD-1..AD-5 FINAL) into docs/ — reuse COMP-QMN and COMP-QMF-VENUE; no Stages 1-8 rebuild"
  sources: [SRC-16]
  provenance: "SRC-16 = architecture-CONNECT-2026-09-11/ (spine status final + .memlog.md + reviews/); captain brief workroom/research/2026-09-11_connect-architecture-result.md; handoff workroom/research/2026-09-11_connect-architecture-handoff.md. Brownfield integration@1b451a8 via the sitting's git show. Operator-directed change-mode absorption; sitting itself was operator-absent with tagged assumptions A1-A5 as cheap-veto."
  ledger: "DEC-0263..DEC-0268 minted (ratified, authority rider): CONNECT AD-1 fail-closed selection, AD-2 honest FX paper, AD-3 encode/session locus, AD-4 FTR-01 closed mapping to CT-13 data quality (interprets DEC-0247, does not supersede), AD-5 plurality without a fourth V1 kind, umbrella adoption + preflight reuse. EXT-2172..EXT-2182. No live DEC superseded."
  gaps: "GAP-0059 (FTR-02 compound-command annotation) and GAP-0060 (canonical live source parameterization) minted deferred non-blocking. A3 journal type data quality answered as DEC-0266 with cheap-veto. No blocking gap opened."
  adr: "ADR-0021 written (new); preflight verdict: reuse COMP-QMN and COMP-QMF-VENUE — no new component; ADR-0019 dated CONNECT follow-up"
  contracts: "CT-20 mapping rows for position-read-back and balance-read-back corrected from observation-as-journal-type to CT-13 data quality; CT-13/CT-18/CT-19/CT-21 CONNECT usage annotations; no new contract id"
  features: "FEAT-0032 minted (multi-pass, planned, blocked_by FEAT-0023/0024/0026/0031)"
  status: complete
  remaining: "GAP-0059/GAP-0060 deferred; cheap-veto A1-A5; next = bmad-create-epics-and-stories then factory lane — not this session"
"""


def main() -> None:
    append_if_missing(ROOT / "_docwork" / "extractions.yaml", "id: EXT-2172", EXTR)
    append_if_missing(ROOT / "_docwork" / "ledger.yaml", "id: DEC-0263", LEDGER)
    append_if_missing(ROOT / "_docwork" / "gaps.yaml", "id: GAP-0059", GAPS)

    inv = ROOT / "_docwork" / "feature_inventory.yaml"
    text = inv.read_text(encoding="utf-8")
    if "id: FEAT-0032" in text:
        print("skip feature_inventory: FEAT-0032 already present")
    else:
        needle = "  - id: FEAT-0040"
        if needle not in text:
            raise SystemExit("FEAT-0040 anchor missing")
        inv.write_text(text.replace(needle, FEAT.lstrip("\n") + needle, 1), encoding="utf-8")
        print("inserted FEAT-0032 before FEAT-0040")

    man = ROOT / "_docwork" / "manifest.yaml"
    mtext = man.read_text(encoding="utf-8")
    if "id: SRC-16" in mtext:
        print("skip manifest: SRC-16 already present")
    else:
        if not mtext.endswith("\n"):
            mtext += "\n"
        man.write_text(mtext + SRC16, encoding="utf-8")
        print("appended SRC-16")

    st = ROOT / "_docwork" / "stage_state.yaml"
    stext = st.read_text(encoding="utf-8")
    if "Absorb the 2026-09-11 CONNECT" in stext:
        print("skip stage_state: CONNECT entry already present")
    else:
        if not stext.endswith("\n"):
            stext += "\n"
        st.write_text(stext + CHANGE_MODE, encoding="utf-8")
        print("appended stage_state change_mode")


if __name__ == "__main__":
    main()
