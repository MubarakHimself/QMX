---
id: 007
title: Reference repo deep study
label: wayfinder:research
status: closed
assignee: claude-session-2026-08-17
blocked-by: []
closed: 2026-08-17
---

## Question

What mental models should QMF borrow from the 25+ reference repos Mubarak supplied (see `workroom/reference/links.md`) — and, with that evidence, how do the kernel question (build vs adopt vs hybrid) and the backtesting architecture (agent-proof, Book-pluggable, industry-grade) actually resolve?

## Resolution

Waves 1+2 complete (22 agents total, 37 repos cloned, 13 study files, 113-idea ledger + 43-idea wave-2 supplement). Verdicts delivered: `workroom/reference/01-kernel-verdict.md` — BUILD the kernel (staged: skeleton+conformance suite first; honest cost 7–11k lines / 45–67 factory-days ±40%; Nautilus on a dated review trigger; **D1 amendment: LGPL permitted for unmodified separately-installed deps**; tiebreaker = a 3-factory-day adoption spike with a pre-agreed decision rule). `workroom/reference/02-backtesting-verdict.md` — Option 2: five QMF contracts first (Run/Result, metrics, FillAssumptions+fidelity, registration gate, Book seam), engine as thin assembly (~1,500 lines given the kernel); full vocabulary fix (SimVenue / Fill Engine / Run / Replay / Paper mode / Simulator=UI / Book Matrix / Program / Campaign); 14 rulings queued for Mubarak. Honest risk both briefs agree on: the retail-forex fill model has NO reference implementation anywhere — instrument it, expect v1 to be wrong visibly. Recovery comparison (old Examination Engine) in progress → `workroom/reference/04-recovery-comparison.md`.

## Progress

Workflow `wf_a53bf7ca-d42` running: 4 Sonnet cloners (shallow clones → `workroom/reference/repos/`, .git stripped, licences recorded) → 8 study agents (Nautilus deep, Jesse deep, backtest engines comparative, platform patterns, ML/research patterns, portfolio libs, bot frameworks, catalog maps) → 2 verdict briefs (`workroom/reference/01-kernel-verdict.md`, `workroom/reference/02-backtesting-verdict.md`) → merged idea ledger (`workroom/reference/00-idea-ledger.md`: idea | source | borrow | why | how QMF implements | licence). Ethics rule baked into every prompt: mental models only, no code transplantation, copyleft = design-study only. Mubarak's nudge to fold into the digest: each Book may carry its own testing mechanism — the same bot testable against different Books (scalping variants, prop-firm eval/funded) as a matrix.
