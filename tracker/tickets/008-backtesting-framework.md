---
id: 008
title: Backtesting framework (staged funnel)
label: wayfinder:grilling
status: open
assignee:
blocked-by: []
---

## Question

Design QMF's backtesting **framework** (never "engine") as its own full session, on Mubarak's staged-funnel idea: cheap screen → research test → robustness test → execution/replay → full Book/BMS simulation — where early stages exist only to decide whether a strategy earns more compute, and outcomes route as pass→promote / pass+opportunity→enhance / fail+known-issue→repair-component / fail+unexplained→archive. Execution is ON-DEMAND in agent sandboxes/VPSs (bare-metal Ryzen 9 planned), never centralized on the workstation.

## Inputs (evidence, none pre-ratified)

- Mubarak's GPT brainstorm conversation (he will attach the markdown — REQUEST IT at session start)
- `workroom/reference/02-backtesting-verdict.md` (rev2) and `workroom/reference/04-recovery-comparison.md` — treat as research inputs; blocks C/D of the 2026-08-17 artifact were explicitly NOT ratified
- His constraints: intraday scalping profile (swap largely irrelevant; IC Markets swap-free account), synthetic data = experimentation/stress only (99% historical), spread modeled within measured ranges, SQS reverse-engineered into backtest conditions
- Vocabulary sensitivities: no "fake counterparty" framing; plain words + diagrams; **"exam" is banned** (collides with the legacy Examination Engine / Book-exam concept)

## Additional inputs (2026-08-18 locks session)

- The sim≡live parity idea (one shared checklist both the practice venue and the real cTrader connection must pass, written before either implementation) was pitched as "Lock 2" and DENIED as bundled — the connection half proceeds separately as simple work; the parity half belongs HERE and must be re-presented with more depth ("dig deep or present a better version — I'm not buying it now").
- The full overfitting-statistics discussion also lands here wholesale ("too early for me to discuss backtesting"). Operator's read of the old engine: Monte Carlo + walk-forward + PBO made it "heavy and solid" but with wrong claims / over-engineered; the true goal is overfitting prevention AND letting agents run tests correctly on their own — agents, not Mubarak, execute backtests, so the design must make the right thing the easy thing for an agent.
- Legacy "exam" concept for context (recovered meaning, do not reuse the word): a bot was tested against the things that make its Book that Book — the Book supplies the conditions. Partial overlap with the parity checklist, not the same thing.
- Books connection: each Book may carry its own testing mechanism (bot × Book matrix, standing map ruling) — the funnel design must accommodate per-Book test conditions.
