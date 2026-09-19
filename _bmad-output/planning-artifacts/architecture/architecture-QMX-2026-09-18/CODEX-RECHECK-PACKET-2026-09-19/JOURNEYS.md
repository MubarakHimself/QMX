---
name: Traced journeys and failure coverage
sitting: architecture-QMX-2026-09-18
status: proposed behaviour — Stage C reconciled; 85 Codex scenarios remain the independent catalog
---

# Journeys (Stage C)

Handoff J01–J24 preserved. Oracles below are what the **reconciled candidate** claims. Codex Pass-I 65 + Pass-II 20 remain independent requirements in `codex-challenge-20260919/SCENARIO-CATALOG.jsonl`. This file does not replace that catalog.

## Four proofs

| Proof | Journeys | Spine |
|---|---|---|
| Two honest trading compositions | J03, J03b, J10 | AD-11, AD-23, AD-14, AD-25 |
| Non-trading data/ML without fake bot | J06, J13 | AD-11 class 3, AD-12, AD-31 |
| App-use → change request → authoring v2 | J01, J02 | AD-8, AD-9, AD-29 |
| Install/reuse without core edits | J08, J09, J12, J24 | AD-2, AD-3, AD-10, AD-18, AD-30 |

## Representative traces

### J01 — App-use result → authoring v2

Given installed app instance v1 with GrantRecords for inspect ops  
When the user asks the app-use copilot to explain a run and request a filter change  
Then a change-request staging artifact is minted with base hashes, context revision, source instance/config, and request hash; v1 instance, grants and running jobs are unchanged  
And a new authoring session opens with scoped refs, not the private transcript  
And only authoring + operator principal applies; app-use never applies  
**Forbidden:** app-use writing package source; grant widening; account retarget; tab switch patching context  
**Fails if:** skill text grants `role.set_base`; stale base hash applies

### J03 — Default Book/BMS path (regression)

Given default Book/BMS compile path (regression tests exist)  
When the composition is validated, simulated, and (separately) deployed through existing QMN seats  
Then CT-22/CT-27 remain required; dummy Book is `INVALID_INPUT`  
**Forbidden:** weakening compile tests to admit ATC or ungoverned through `ResolvedRunConfig`

### J03b — Alternative Trading Composition (portfolio/risk/sizing swap)

Given an `AlternativeRunConfig` with a complete `PolicyPair` and **no** Book/BMS/bot keys  
When that composition is selected  
Then QML authoring, QMB backtest/optimize, optional MIS binding, and QMN **adopt it** (they do not remain Book-shaped)  
And validate/simulate write ATC journal rows (`composition_class: alternative`)  
And paper-then-live uses J10 fencing with an ATC `composition_fp` and a QMN token after L17  
**Forbidden:** dummy Book fp1; calling sensing/research/`UngovernedWorkConfig` this journey; hot-swap of live positions; two command owners on one account/venue/role

### J06 / J13 — Recipe without bot

Given a price CT-10 and a non-price CT-10  
When a `RecipeDefinition` as-of-joins them with no-lookahead policy  
Then a derived **release** fp1 is stored with CT-07 lineage to the stable `recipe_def_id`; no CT-33, no Book, no QMN deploy  
**Forbidden:** lookahead; silent provider swap; treating the release fp1 as the definition identity

### J08 / J24 — Install elsewhere

Given an exported pack that passed the independent secret scanner  
When installed on a second QMX with that installation’s credentials  
Then contributions appear as ContributionHits after enable; previous roster stays consistent on failure  
**Forbidden:** warning-and-continue missing deps; private path ids; self-asserted `exports_secrets: false` without a scan

### J10 — Sequential fenced handover

Given old `composition_fp` with typed positions/orders  
When operator requests replacement  
Then AD-25 states run to `fenced-activate` with a new command-owner epoch and token  
And UNKNOWN orders block (`unknown-blocked`)  
And a restarted predecessor without the current token is refused  
And rollback of software does not unwind fills

### J12 — Four composition modes

1. Consume artifact fp1  
2. Invoke exported op through AD-24 envelope  
3. Graph Template coordinates two apps  
4. Composite app cites contribution ids  
**Forbidden:** DOM driving; union of permissions; un-budgeted invocation cycles; latest-instance substitution

### J17 — Shared stream cancel and cutover

Given two consumers of one tick subscription with provider `source_id` distinct from `venue_id`  
When consumer A cancels  
Then consumer B continues; refcount decrements; phase replay|cutover|live remains explicit  
When replay reaches `cutover_watermark`  
Then phase becomes live atomically; replay provenance cannot authorize live commands

### J26 — Uncertain external effect (new, maps P1-OP-002)

Given an `external-egress` invocation whose acknowledgement is lost  
When the caller retries  
Then state is `unknown` until reconcile; the second attempt with the same `logical_invocation_id` does not duplicate the order/export/message

### J27 — Successor outbox after crash (new, maps P2-WF-009)

Given predecessor A completing with successor B  
When the daemon crashes between A’s terminal write and B’s dispatch ack  
Then restart replays the outbox and B runs exactly once logically

## High-risk failures (Codex first-unsupported transitions, now specified)

- Operation accepted → timeout/unknown → safe retry or reconcile (AD-24, J26)
- Task completion committed → successor eligibility persisted → dispatch once (AD-26, J27)
- Package bytes validated → migration/activation → roster atomically published or prior restored (AD-30)
- Discovery hit pinned → instance/config resolved → health/grant rechecked → invoke or tombstone (AD-30)
- Session mutation → revision conflict or durable result → reconnect without replaying intent (AD-29)
- Replay cursor reaches live watermark → atomic cutover → gap/late/backpressure evidence (AD-28, J17)
- Old command owner drained → residuals/orders reconciled → new fenced owner → old process restarts safely (AD-25, J10)
- Multi-store snapshot → ordered restore → orphan/external-effect reconciliation (AD-27)
- Dummy ResolvedRunConfig as “alternative system” (AD-11, J03b)
- Graph Template `A→B→C→A` (AD-6)
- GPU job returning without pinned weights (AD-15, AD-26 completeness)

CIS map: `inputs/opportunities-journeys.md` (80 seeds clustered; OP-NEW-01..18). Enabling vs later apps distinguished. Not a backlog. Independent catalog: 85 Codex IDs.
