# Prompt for the other agent

Paste this (plus point them at this folder).

---

You are in a design discussion about **QMX Market Intelligence (MIS)** adoption of methods found in a full-read of the local MQL5 article library.

Read, in order:

1. `workroom/research/2026-09-15_mis-fullread-ideas/advisory-packet/00-README.md`
2. `01-LAWS.md`
3. `02-ADOPT.md`
4. `03-HOW-TO-ADOPT.md`

Laws in 01 are not negotiable. Article EAs that switch playbooks do **not** become MIS consumers.

Your job in the discussion:

- Propose **at most three** shadow-lane candidates from `02-ADOPT.md` for the first experiment wave (default suggestion: B2, A1, C1).
- Map each onto `shadow.py` + existing `regime_*` refuse-paths. No new library, no SQS change, no bot snapshot.
- If you want a snapshot field, say **which one field** and which sitting it would take. Do not propose a physics stack, online learning, or playbook switch.
- Challenge the integration LightGBM design (`quiet|normal|elevated|stressed`) only with a **door-task** experiment (see `04-EXPERIMENTS.md` E1/E3), not with article win-rates.

Do not reopen `workroom/research/2026-09-15_unbounded-market-intelligence/` for ideas; that pass was title/keyword. Use it only for code-baseline facts.

---
