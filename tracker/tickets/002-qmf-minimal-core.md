---
id: 002
title: QMF minimal core
label: wayfinder:grilling
status: closed
assignee: claude-session-2026-08-18
closed: 2026-08-18
blocked-by: [001]
---

## Question

What is QMF's minimal core — the named modules of V1, which existing libraries each wraps versus what gets built, and the boundaries between the five hat lanes — such that the factory can ship V1 in ~2–3 days? Claude drafts from the research synthesis (`workroom/research/00-qmf-synthesis-module-map.md`); Mubarak yes/no's the draft. Ask Mubarak to attach the original QML design doc if he has found it.

## Resolution (2026-08-18 evening)

**Naming note:** this ticket's title ("QMF minimal core") is historical. What it resolved into is the **QMF V1 blueprint** — the phrase "minimal core" is retired (operator, 2026-08-18) because the agreement now spans the full five-hat library roster; only `qmf-core` itself stays deliberately small.

QMF's minimal core is answered: **`qmf-core` accepted as the first brick** (exact money, exact time with three trading calendars, the nouns seeded for order-flow and equities, typed refusals, stamp machine, versioning — no loop, no broker, no backtest, no downloads), and the full **QMF library roster split by the five hats** is recorded in the spec (`workroom/artifacts/2026-08-17-qmf-v1-spec-DRAFT.md` §2b) with a status tag per library. Nothing agreed is outside QMF — only outside the first brick. The six frozen technical choices are confirmed at the documentation pass, not here. Next step per operator: export this session, run the documentation skill on QMF, factory codes from the docs. The trading node re-spec (ticket 004) follows, built on this session's output.

## Progress

Draft ready for the ~17:00 ratification pass: spec `workroom/artifacts/2026-08-17-qmf-v1-spec-DRAFT.md` (module rings, 12 decisions D1–D12 with recommendations, conventions, tonight's fence = Ring 0 + Ring 1 + conformance harness) and presentation artifact `workroom/artifacts/2026-08-17-qmf-minimal-core.html`. Resolve when Mubarak ratifies/amends D1–D9 and blesses the fence; then flip spec DRAFT → RATIFIED and he exports the pack to the documentation factory.

**Update (afternoon review):** D2 (own kernel) and D3 (simulator-as-adapter) are REOPENED pending ticket 007's verdict briefs — Mubarak wants the mature-platform evidence first, and "simulator" caused a vocabulary collision (he read it as an FX-Replay-style human chart-replay tool; the spec meant the backtest fill engine — rename at ratification). New operator ruling folded in: QMF never adopts third-party strategy-family libraries (SMC/ICT/etc.) — it is the toolbox for building our OWN versions of those ideologies. Ratification pass now happens after the repo-study returns.

## Session 2026-08-18 — locks discussion capture (operator verdicts + dictation)

**Lock verdicts:**
- **Lock 1 "the Dictionary" (qmf-core): ACCEPTED as first brick**, with every dictated input below folded in. The six freeze-choices (UTC-ns clock, (venue,symbol) identity, TA-Lib reference math, three backtest honesty levels, SR* bar, result-label tuple) remain PROPOSALS to be explicitly confirmed during the documentation pass — not yet frozen.
- **Lock 2: DENIED as bundled; the word "exam" is BANNED** (collides with the legacy Examination Engine and the Book-exam concept — bits still being recovered). Split: (a) broker CONNECTION contract = simple, proceeds (cTrader Open API, Python, no MQL ever); (b) the sim≡live parity checklist → input to ticket 008's backtesting session. Crypto venue plurality ("crypto is a mess, many ways to trade") = extensibility requirement on the venue seam.
- **Lock 3: identity + lineage ratified IN PRINCIPLE** (lineage is explicitly graph-shaped — Neo4j analogy, grows and compounds); **one-card-for-EVERYTHING DENIED as premature abstraction**: "model" is ambiguous (ML / trading / analysis model); a Book is very specific — own schema on GitBook, operator-in-the-loop deployment — and does NOT go under a generic card; a bot may contain MULTIPLE confluences ("heavy bots"; sky is the limit); crypto/prop-firm may need different shapes. Deep study against real QMX docs required before re-proposal → ticket 009.
- **Lock 4 (agent page): DEFERRED** — "we can't front-load an agent page without proper documentation; QMF is very incomplete." Revisit after the library and its docs exist.
- **Lock 5 (answer keys): NOT ratified** — rework grounded in actual QMX components first.
- **Backtesting: ALL of it** (incl. the overfitting-statistics discussion — old engine had Monte Carlo / walk-forward / PBO, "heavy and solid" but with wrong claims / over-engineered) **moves wholesale to ticket 008** — "too early for me to discuss backtesting"; agents run the backtests, so the design session must account for that. **Program/Campaign: OFF** — a prop firm is just a new Book; Book creation (incl. prop-firm Books) is an agentic-era activity under QMX itself.

**Operator dictation — architecture facts for the documentation factory:**
- Data lake: "handle it like a good data scientist" — agents get properly-split data BY DEFAULT (splits/discipline built into the access path so agents can't skip data-science technique).
- Indicators, three tiers: (1) HEAVY indicators (not millisecond-computable — regime models, volatility forecasts, correlation matrices, ML inference) live in the MIS — old-architecture ruling reaffirmed; (2) light bot/strategy-level indicators; (3) custom indicators built by experimentation (genetic algorithms proven viable).
- Data types must cover DOM / level-2/3 / order flow / tape. Old QML derived options-style gamma/theta LEVELS recomputed for forex (and later crypto) — a levels family to revisit. Crypto has many inefficiencies; deliberately deferred until QMX is a platform, then EXTEND QMX's crypto capabilities (never a separate version).
- Broker adapter: READ PROPER DOCUMENTATION (emphatic, repeated) — mostly the trading-node docs.
- Books & BMS: Book variants carry lineage/types (scalping-book variants; prop firms same logic); possibly MULTIPLE BMSs long-term (crypto may need standalone versions); current Book/BMS = "the stable version I could think of — if you want to enhance it, you propose"; the Book schema is already documented on GitBook — NEVER assume it.
- Trading-node depth warning: exit mechanisms are "a whole world" — fast invalidation, dynamic SL/TP system, correlation ledger; Book/BMS calculations have very many variables (some defined, some defaults, some editable, some locked) — "very surgical, don't take them for granted."
- Kill switch: news is PAIR-SCOPED — block only affected pairs while the system keeps trading everywhere else; globally we zoom out (multi-pair by design).
- Paper trading is a STANDING STATE, not a waiting room: bots paper-trade under documented conditions (kill switch fired, daily limit hit, prop-firm rules) and results are recorded continuously regardless — feeding ALPHA-DECAY sensing, which needs uninterrupted data points. Alpha decay is a huge concept; consider it throughout the system.
- Promotion: HUMAN-ONLY — Mubarak personally, as a daily activity; no agent promotes, ever; he may promote a Python-only bot (confirms guidelines-not-walls); promotion machinery needs little design — the lab and live are the two zones that matter.
- Metrics & reports: agent-facing; must show WHY a strategy fails — ideally which component; unbiased; triage = improve or cut loose; "see the inside of the strategy, not just pass/fail."
- Data layer (his repeated emphasis): ingestion ≠ processed collection ≠ processing method; trading journal; per-component collection (what do bots / Books / BMS / MIS / SQS / kill-switch each record — cadence, quantity, duration); automatic detection with operator-set ranges (non-technical operator wants if-this-then-that flags); right store per purpose (ArcticDB open question; lineage is graph-shaped).
- Process meta-ruling (repeated): Claude underestimates depth — triggers alone (e.g. multi-timeframe-analysis triggers) can be a two-day session inside QMX; bite off only what one session can truly handle; parallel sessions are his coverage mechanism.
