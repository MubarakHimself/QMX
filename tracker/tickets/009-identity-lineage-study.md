---
id: 009
title: Identity & lineage deep study
label: wayfinder:research
status: closed
assignee: claude-session-2026-08-18
blocked-by: []
closed: 2026-08-18
---

## Question

What is the right identity/registration/lineage model for QMX's things — WITHOUT collapsing unlike things into one generic card? Operator verdict (2026-08-18): identity and graph-shaped lineage are right in principle; "one ID card for everything" is premature abstraction. Specifically: disambiguate "model" (ML / trading / analysis); respect that a Book is its own very specific schema (documented on GitBook, operator-in-the-loop deployment) and does NOT belong under a generic card; a bot may contain MULTIPLE confluences ("heavy bots"); crypto and prop-firm shapes may differ from forex; paper/live/benched states and continuous paper-recording for alpha-decay sensing must be representable; promotion is human-only. Ground the study in the real QMX corpus (GitBook Book schema, trading-node primer, lineage addendum, spec-draft vocabulary) and the 37-repo idea ledger — then propose a typed identity model (which kinds exist, what each carries, how lineage edges work) for operator review. Do not box in: the lineage graph shape must not presume a specific database.

## Resolution

Study delivered: `workroom/reference/07-identity-lineage-study.md` (416 lines; findings NOT adopted — operator ratification pending). Kind catalog: 7 families, ~23 kinds. The three-discipline correction to "one card": **fingerprint** (reproducible recipes — levels/triggers/confluences, content-addressed), **charter** (named things the operator stands behind — Books, BMS instances, operator-countersigned, amended by named decisions), **occurrence** (unrepeatable events — runs, live sessions; a live Tuesday cannot be re-derived, so it carries no content hash). Only the address format `kind + id` is universal. "Model" disambiguated into three kinds (ML artifact / trading thesis / analysis artifact) — bare word "model" proposed for the banned list. Bot = permanent career identity + per-revision fingerprints; variants are new bots linked `variant-of`; plain-Python bots carried via `definition: opaque`. Books: scalping-book-v2 is a NEW Book (never inherits v1's ledger). 16 typed edge kinds, 5 store-agnostic graph rules, smallest honest starting set of 6 kinds. Top open questions (operator): BENCHED moves from Book mode to the bot's roster seat (recommend yes); one bot in paper while its Book stays live (recommend yes); idea-origin required only at promotion gate, not registration (recommend yes — don't-box-in).
