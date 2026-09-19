# CONNECT architecture sitting — operator-absent handoff

Captain: Hermes default. You are the **Architect hat** in a **fresh session**. Load `bmad-architecture` and run it. Operator will not answer. Do not block on questions — record `[ASSUMPTION]` and continue.

## What this sitting is

Child **feature** architecture increment so QMX can **CONNECT** and **FX paper-trade**. Stop when the spine is `status: final` (or the skill’s equivalent done state). **Do not** run documentation-factory, epics, or Grok factory in this session.

## Use sub-agents

This skill + `_docwork` + `integration` code is too heavy for one context. Delegate bounded reads (qmn.venue, CT-18..21, node epics 24–28, PRD §7). You orchestrate. Children must not run BMAD skills.

## Binding rulings (do not reopen)

- No third venue-gateway library. `qmn.venue` is the sole `qmf-venue` importer (DEC-0241).
- Live selector today defaults unknown live VenueId → CTRADER. That is a connect bug; unknown must refuse.
- `LiveCTraderClient.submit` is sensing-only. FTR-01 blocks position/balance read-back. Honest FX **paper** = vendor demo + `world=live` + **submit encode** + read-back mapping.
- FX paper first. Crypto adapter is plurality (same port, new CT-18), not Book/BMS redesign.
- Spot FX is **not** skipped for adaptation. Live-capital bleeding is not an adapter skip.
- Risk / crypto Book / sizing / MIS redesign are **out of this sitting**.
- UI / Penpot out. STRATS / loop-engineering out.
- No `bmad-sprint-planning`, no `bmad-build`.
- Brownfield: `integration` (inspect via `git show`; do not checkout if it disrupts). Existing packet: `workroom/research/2026-09-09_crypto-connect-and-history.md`.
- Parent spines: QMX 2026-08-19, NODE 2026-08-28. Inherit; do not re-derive.

## Output

Architecture run folder under `_bmad-output/planning-artifacts/architecture/architecture-CONNECT-<date>/` with `ARCHITECTURE-SPINE.md` + memlog. End with a 20-line captain brief at `workroom/research/2026-09-11_connect-architecture-result.md` (path, status, conflicts, next skill = documentation-factory in a **new** session).
