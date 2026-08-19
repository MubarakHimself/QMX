---
id: DOC-CONSTITUTION
title: QMF V1 Constitution
type: constitution
status: provisional
depends_on: []
decisions: [DEC-0001, DEC-0002, DEC-0003, DEC-0004, DEC-0006, DEC-0007, DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0022, DEC-0024, DEC-0030, DEC-0031, DEC-0041, DEC-0045, DEC-0046, DEC-0054, DEC-0060, DEC-0061, DEC-0074, DEC-0076, DEC-0080, DEC-0092, DEC-0096, DEC-0097]
sources: [DEC-0001, DEC-0002, DEC-0003, DEC-0004, DEC-0006, DEC-0007, DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0022, DEC-0024, DEC-0030, DEC-0031, DEC-0041, DEC-0045, DEC-0046, DEC-0054, DEC-0060, DEC-0061, DEC-0074, DEC-0076, DEC-0080, DEC-0092, DEC-0096, DEC-0097]
generated: 2026-08-18
verified: 2026-08-18
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

**L8.** Application loops, orchestration flows, scheduled lifecycles, and product UI remain outside the QMF foundation unless a later contract explicitly admits them. (DEC-0009)

**L9.** QMF must remain usable through ordinary Python and suitable external libraries; uniformity is enforced at live-money and agent-harness boundaries. (DEC-0011)

**L10.** QMX-owned domain contracts and strategy semantics must be implemented locally; permitted dependencies may be wrapped without transplanting a foreign platform contract. (DEC-0013)

**L11.** QMF is the framework umbrella; QML names the deferred Bot-oriented library rather than the whole foundation. (DEC-0017)

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
