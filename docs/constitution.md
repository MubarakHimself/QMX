---
id: DOC-CONSTITUTION
title: QMF V1 Constitution
type: constitution
status: ratified
depends_on: []
decisions: [DEC-0001, DEC-0002, DEC-0003, DEC-0004, DEC-0006, DEC-0007, DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0022, DEC-0024, DEC-0030, DEC-0031, DEC-0041, DEC-0045, DEC-0046, DEC-0054, DEC-0060, DEC-0061, DEC-0074, DEC-0076, DEC-0080, DEC-0092, DEC-0096, DEC-0097, DEC-0113, DEC-0120, DEC-0122, DEC-0132, DEC-0133, DEC-0136, DEC-0137, DEC-0143, DEC-0150, DEC-0156, DEC-0157, DEC-0169, DEC-0171, DEC-0184, DEC-0191, DEC-0196, DEC-0197, DEC-0217, DEC-0221, DEC-0227, DEC-0231, DEC-0236, DEC-0241, DEC-0243, DEC-0252, DEC-0254, DEC-0256]
sources: [DEC-0001, DEC-0002, DEC-0003, DEC-0004, DEC-0006, DEC-0007, DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0022, DEC-0024, DEC-0030, DEC-0031, DEC-0041, DEC-0045, DEC-0046, DEC-0054, DEC-0060, DEC-0061, DEC-0074, DEC-0076, DEC-0080, DEC-0092, DEC-0096, DEC-0097, DEC-0113, DEC-0120, DEC-0122, DEC-0132, DEC-0133, DEC-0136, DEC-0137, DEC-0143, DEC-0150, DEC-0156, DEC-0157, DEC-0169, DEC-0171, DEC-0184, DEC-0191, DEC-0196, DEC-0197, DEC-0217, DEC-0221, DEC-0227, DEC-0231, DEC-0236, DEC-0241, DEC-0243, DEC-0252, DEC-0254, DEC-0256, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, _docwork/ledger.yaml]
generated: 2026-08-18
verified: 2026-08-29
stale_after: 1y
---

# QMF V1 Constitution

## Laws

**L1.** Current direct operator corrections and rulings govern QMF V1 when sources disagree. (DEC-0001)

**L2.** The GitBook supplies Book and BMS governance baselines; recovery and older QMX material supplies evidence only for semantics unchanged by later rulings. (DEC-0002)

**L3.** Research and study deliverables remain evidence until an operator ruling adopts them as QMF contracts. (DEC-0003)

**L4.** QMF must be documented and reviewed before trading-node implementation or code generation, and deep design must proceed one focused topic at a time. (DEC-0004)

**L5.** QMF code and documentation must be legible to human developers and coding agents. (DEC-0006)

**L6.** QMF libraries must not ship mock market data, fake Bots, or default strategies as product artifacts; controlled test fixtures remain permitted. (DEC-0007)

**L7.** QMF is a reusable toolbox of libraries and small modules from which QMX applications are built; QMF is not an application. (DEC-0008)

**L8.** Application loops, orchestration flows, scheduled lifecycles, and product UI remain outside the QMF foundation unless a later contract explicitly admits them. (DEC-0009) [Node exemption, 2026-08-29: AD-15's roster-wide async stance — the application owns all concurrency and threads, and a QMF async-conformance test bans async across the seven roster packages (that stance is carried as DEC-0113 in the qmf-venue spec, not as a numbered law here) — gains exactly ONE named exemption, admitted through this law's own explicit-admission clause by the TN-11 cTrader transport increment: `qmf.venue.connection`. That module's ConnectionManager holds the asyncio socket, the session and the single in-memory venue secret value on the loop the trading node injects (together with the Clock and the `SecretStore` the node injects); it owns no loop and schedules nothing itself, so "the application owns all concurrency" is preserved in substance while the socket lives where the transport does — the one DELEGATED impurity in the platform. If the parent refuses the exemption, the same transport increment lands in the node's `qmn.venue.ctrader` subpackage instead, and the epics may not choose between the two placements. (DEC-0243, DEC-0196)]

**L9.** QMF must remain usable through ordinary Python and suitable external libraries; uniformity is enforced at live-money and agent-harness boundaries. (DEC-0011)

**L10.** QMX-owned domain contracts and strategy semantics must be implemented locally; permitted dependencies may be wrapped without transplanting a foreign platform contract. (DEC-0013)

**L11.** QMF is the framework umbrella; QML names the Bot-oriented library — now architected as the bot-authoring application-layer library built ON QMF (spine QL-1..QL-10, COMP-QML) — rather than the whole foundation. (DEC-0017, DEC-0184)

**L12.** The documentation target is the QMF V1 Blueprint, and qmf-core is only its first small foundational component. (DEC-0019)

**L13.** qmf-core is a framework-neutral definitions library and must contain no broker, event loop, backtest, download, or trading-node runtime. (DEC-0022)

**L14.** QMF V1 contains five libraries—qmf-core, qmf-registry, qmf-data, qmf-indicators, and qmf-structure—and two modules—Venue and Risk. (DEC-0024)

**L15.** Public QMF contracts must be versioned from their first release, and incompatible semantic changes must mint new versions instead of mutating old meaning. (DEC-0030)

**L16.** qmf-core must not assume Forex, cTrader, scalping, or a deployment environment; Forex is only the first seeded consumer. (DEC-0031)

**L17.** Only a human may promote a registered artifact into the live zone. (DEC-0041)

**L18.** qmf-data must retain complete raw evidence locally and maintain an off-machine backup. (DEC-0045)

**L19.** qmf-data must present research datasets through explicit train, validation, and untouched-test splits by default. (DEC-0046)

**L20.** Synthetic market data may stress infrastructure and failure handling but must not validate trading edge or replace real evidence. (DEC-0054)

**L21.** The first Venue integration must use the cTrader Open API from Python and must not use MQL. (DEC-0060)

**L22.** The Venue module must preserve a venue-neutral seam so later crypto and stock adapters do not change foundational contracts. (DEC-0061)

**L23.** SQS means Spread Quality Sensor and remains distinct from news controls. (DEC-0074)

**L24.** R is the original pre-trade risk unit referenced by `registry:original_risk_unit` and must not mean realized profit, account equity, or post-trade return. (DEC-0076)

**L25.** The recovered Scalping Book is one reusable Book pattern and must not become a global Book law. (DEC-0080)

**L26.** Future alpha-decay and benchmark mathematics must be designed from current definitions and must not be reconstructed from unrecoverable legacy formulas. (DEC-0092)

**L27.** Every factory-built QMF component must ship executable tests and reference usage that demonstrates its public contract. (DEC-0096)

**L28.** QMF must evolve through durable versioned extension rather than repeated foundational replacement. (DEC-0097)

**L29.** Provisional recommendations, provisional contracts, and unresolved GAPs grant neither implementation authority nor live-money authority; destructive or live action still requires a ratified contract and explicit human authority. (DEC-0003, DEC-0004, DEC-0041)

**L30.** QMF inter-library dependencies are default-deny: qmf-core depends on nothing, every package may depend on qmf-core, and no package may depend on any package other than qmf-core until an inter-library edge is ratified as a spine amendment; the one ratified edge is qmf-registry to qmf-data, and nothing imports qmf-venue or qmf-risk. (DEC-0120) [Scope annotation, 2026-08-21: this default-deny law is roster-scoped — it governs the seven roster packages internally, never applications built on the workspace. An application-layer product built ON QMF (COMP-QMB, COMP-QML) may import and consume qmf-risk (and any qmf-venue-free) contracts directly, with impure steps (registration writes, sandbox execution) riding its own composition root; qmb and qml still never import qmf-venue, and the sole sanctioned exception — the trading node — is recorded in the 2026-08-29 node annotation below (DEC-0241). This declared reconciliation note is recorded here at source, not settled silently by a child. (DEC-0171, DEC-0184; QMB precedent DEC-0169)] [Node annotation, 2026-08-29: the trading node (COMP-QMN, code name `qmn`) is the ONE sanctioned importer and wirer of qmf-venue. The writable boundary of that sanction is the node's `qmn.venue` subpackage: duty scheduling, the verification-suite runner, the CT-18 field fills and the error-map rows import qmf-venue there, while every other qmn module receives the node-minted `VenueClientPort` and the CT-19/CT-20 shapes only, and the L30 default-deny lint is written against that subpackage boundary. qmb and qml keep their ban; adding any other edge is a spine amendment. (DEC-0241, DEC-0196)]

**L31.** Everything downstream of QMF — the trading node, backtesting, the agentic system, and the product UI — must be built with QMF libraries and must not re-implement or bypass the framework's contracts. (DEC-0122)

**L32.** No QMF rule, contract, or vocabulary may name or privilege any trading school; school-specific concepts enter only as mechanically stated, school-neutral capability terms, and a school name may appear only as an illustration, never as vocabulary. (DEC-0132)

**L33.** Plain-Python authoring outside governed evidence is always legal; a working plain-Python experiment enters governed evidence only by graduating through the extension shape — a separate versioned package, explicitly registered at the composition root — with a lineage edge back to the originating research artifact. (DEC-0133)

**L34.** QMF components handle secret references, never values; secret values live only in the adapter's connection manager for a session's lifetime, and secrets never appear in repositories, configuration artifacts, journals, evidence, fingerprints, or logs. (DEC-0136) [Node annotation, 2026-08-29: this law governs secret VALUES in a live process — above the connection manager only references travel, still true on the node. Secret MATERIAL at rest is a separate ratified layer, not an exception to it: the VPS two-layer store keeps bootstrap credentials sealed by systemd-creds LoadCredentialEncrypted with an explicit `--with-key=host` key-encryption key and rotated session material as AEAD ciphertext under that KEK at `/var/lib/qmx/state`, while the CT-14 backup payload key is generated and escrowed on the workstation and delivered as a bootstrap credential, never VPS-minted. No plaintext secret ever reaches a repository, config artifact, journal, evidence, fingerprint, or log, so the reference-not-value discipline is preserved end to end. (DEC-0197, DEC-0227, DEC-0217, DEC-0252)]

**L35.** Every venue submission resolves to accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN; a timeout is never a rejection, an UNKNOWN blocks its command stream until an explicit recorded resolution, and no QMF component retries, assumes an outcome, or invents terminal state. (DEC-0137)

**L36.** Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market. Hierarchy: bot -> book -> BMS -> operator. This authority order is re-ratified 2026-08-20, and nothing in QMF may invert or shortcut it. (DEC-0143)

**L37.** For risk, position-sizing, and live-trading content the GitBook and trading-node documentation are authoritative; the QMX-discussion layer is barred as a source there, citable only for non-risk structural definitions under a named exemption stated at the point of use. (DEC-0156)

**L38.** Configurable means UI-editable at platform level: every configurable variable declares `ui-editable` or `uneditable` in its template, and recorded numbers attached to configurable variables are evidence, never ratified constants. (DEC-0157) [Node annotation, 2026-08-29: the closing clause is refined, not overturned — a recorded number is still evidence in the registry and never a ratified constant there. The registry schema gains a `value_status_required` field, but the per-value `value-status` (blank | provisional-evidence | ratified) lives on the RESOLVED config artifact, never on the registry row; a recorded number becomes ratified only by an operator countersign made through the powers channel, minting a new config version and refused without the variable's fp1 evidence citation, one variable per call. A blank or `provisional-evidence` value on a live-gating variable blocks `role = live` exactly as a blank does. (DEC-0254, DEC-0231, DEC-0256)]

**L39.** The exit-preservation invariant: no control action, of any authority, at any scope, may block a risk-reducing act or the recording of evidence; the blocking half of any control is entries only, and no control kind whose effect is a blanket command-pipe block may be minted. (DEC-0150) [Node annotation, 2026-08-29: on the trading node every block it can raise on a command stream is entries-only — it refuses `place_order` and risk-increasing `amend_protection` and nothing else, and a block that cannot be applied entry-side only is not minted, so this law's ban on minting a blanket command-pipe block stands. The ONE exception is the parent's own, not a node-minted control: AD-27's per-command UNKNOWN block, AD-36's one non-control block, refuses EVERY command on that `(VenueId, account)` stream — protection commands included — because dispatching a `close_position` into a stream whose last submission's fate is unknown is how a position gets double-closed; a refused protective act never evaporates but stands as an AD-36 protection intent journaled before dispatch and re-decided when the block clears, cleared only by `resolve_unknown` and never by a reconciliation verdict. (DEC-0191, DEC-0221, DEC-0236)]
