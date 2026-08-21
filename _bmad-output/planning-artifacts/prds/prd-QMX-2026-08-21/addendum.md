# PRD Addendum — QMX Platform

Depth the operator contributed during discovery that belongs downstream
(architecture, solution design, phase planning) rather than in the PRD itself.

## Form-factor evolution (operator dictation, 2026-08-21)

- An earlier concept split the platform into a backend node plus a database.
  The current direction is a **local desktop application** (Bloomberg-terminal
  style) with the **trading node on a VPS** so trading runs continuously and
  independently of the operator's machine.
- Agent workers may run **locally or in server sandboxes**; Modal and E2B were
  named as the class of platform that could host them. This is a direction,
  not a decision — no evaluation has been run.

## CLI positioning

- The CLI is modeled on the **Lean CLI (QuantConnect)** and lives under the
  backtesting/experimentation library (QMB), not at platform level. The QMB
  spec corpus itself cites Lean as a reference.
- Its primary future consumer is **agents**, but the framework must not box
  itself into the CLI: plain Python remains a first-class door ("tomorrow, if
  we want to use normal Python, we can still use normal Python").

## Why the old-version PRD is excluded

- The old QMX had reached "entire platform finished" documentation depth. Its
  functional requirements are heavily deprecated — the agentic system most of
  all ("so many things are going to be scrapped") — and the old backtest
  engine was replaced wholesale by the QMB direction. Old architecture diagrams
  describe connections that no longer exist. Operator applied YAGNI explicitly.
- Everything that survived was already absorbed into `docs/` through the
  architecture sessions and documentation-factory runs, which the operator
  regards as the thoroughly reviewed body ("by the time something has reached
  docs, it has been thoroughly reviewed").

## Product framing analogy

- "We are building React and the React documentation before we build the
  website": QMF is the framework; QMB/QML are libraries on it; QMX the platform
  (terminal + node + agents) is the website that comes after. V1's goal is a
  **stable platform foundation**, not the terminal.

## Naming notes

- QM = **Quant Mind** (operator: "it's quant, not quantum"). The trading node
  is the Quant Mind trading node.
- Operator listed "QMB, QMF, QML, and QMA" as distinct — **QMA** as the
  agentic system's name was CONFIRMED by operator dictation 2026-08-21
  ("QMA is mostly the agentic system").

## Old-version lineage (operator dictation, 2026-08-21, second session)

Three generations precede the current corpus:

1. **`C:\Users\Mubarak\Documents\Claude\QMX-discussion`** — very, very old;
   planning-only retrievals after a laptop crash. Light-mine only; its agentic
   material especially is superseded.
2. **The GitBook** (`elios-1.gitbook.io/qmx`) — the intermediary; mostly the
   trading node plus the rewrite of risk management and position sizing.
   Don't over-read it beyond that role.
3. **`C:\Users\Mubarak\Documents\QMX`** — the later, better old version
   ("I took my sweet time with it"); had an even more stable trading-node
   design, but predates QMF entirely and much of it will change because the
   framework and libraries now come first.

The operator's instruction: mine and correlate these without making him read
them; the current docs/_docwork corpus stays the authority.

## Trading-node operational intensity (operator dictation, 2026-08-21)

The node phase carries the platform's heaviest ops load: MIS includes
machine-learning instances that need training, **shadow-rollout**
methodologies before promotion, and periodic retraining. This is the concrete
reason the DevOps lens is the primary success measure — deployment on a
server, monitoring, and one-person repairability must hold under that load.

## Reconciliation flag from GitBook sweep

- The live GitBook frames the QML layer conservatively (deterministic library,
  interfaces open under GAP-0013) while local `docs/` carries the richer
  absorbed QML bot-authoring increment (QL-1..QL-10, CT-33/34). The PRD treats
  GitBook as the stable governance baseline for risk/Book/BMS and `docs/` as
  authoritative for QML authoring — per constitution L2/L37 source-authority
  rules. Downstream docs should not assume the two already agree everywhere.
