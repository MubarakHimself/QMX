---
name: Traced journeys and failure coverage
sitting: architecture-QMX-2026-09-18
status: proposed behaviour — Stage B expands independently
---

# Journeys (Stage A)

Handoff J01–J24 preserved. Oracles below are what the **candidate architecture** claims. Stage B must derive its own list before reading this file.

## Four proofs

| Proof | Journeys | Spine |
|---|---|---|
| Two honest trading compositions | J03, J10 | AD-11, AD-14 |
| Non-trading data/ML without fake bot | J06, J13 | AD-11, AD-12 |
| App-use → change request → authoring v2 | J01, J02 | AD-8, AD-9 |
| Install/reuse without core edits | J08, J09, J12, J24 | AD-2, AD-3, AD-10, AD-18 |

## Representative traces

### J01 — App-use result → authoring v2

Given installed app instance v1 with granted inspect ops  
When the user asks the app-use copilot to explain a run and request a filter change  
Then a change-request staging artifact is minted; v1 instance, grants and running jobs are unchanged  
And a new authoring session opens with scoped refs, not the private transcript  
**Forbidden:** app-use writing package source; grant widening; account retarget  
**Fails if:** tab switch patches context; skill text grants `role.set_base`

### J03 — Two trading systems

Given default Book/BMS compile path (regression tests exist)  
And an alternative research composition with **no** Book fields  
When both are evaluated  
Then default path still requires CT-22/CT-27; alternative uses ungoverned/`analysis.rerun` of a **complete** other policy or stays non-evidence  
**Forbidden:** dummy Book fp1; projection used as rerun  
**Live without Book:** refused (AD-11) until L36 amendment

### J06 / J13 — Recipe without bot

Given a price CT-10 and a non-price CT-10  
When a recipe as-of-joins them with no-lookahead policy  
Then a derived release fp1 is stored with lineage; no CT-33, no Book, no QMN deploy  
**Forbidden:** lookahead; silent provider swap

### J08 / J24 — Install elsewhere

Given an exported pack without secrets/transcripts  
When installed on a second QMX with that installation’s credentials  
Then contributions appear as ContributionHits after enable; previous registry stays consistent on failure  
**Forbidden:** warning-and-continue missing deps; private path ids

### J10 — Sequential handover

Given old composition_fp with attributed positions  
When operator requests replacement  
Then default path is stopped/drained then activate; UNKNOWN commands block; rollback of software does not unwind fills

### J12 — Four composition modes

1. Consume artifact fp1  
2. Invoke exported op  
3. Graph Template coordinates two apps  
4. Composite app cites contribution ids  
**Forbidden:** DOM driving; union of permissions; un-budgeted invocation cycles

### J17 — Shared stream cancel

Given two consumers of one tick subscription  
When consumer A cancels  
Then consumer B continues; phase replay|live remains explicit

## High-risk failures (Stage A seed; Stage B expands)

- Upgrade dependency while old run waits (pin holds)
- App-use nested invoke becoming authoring
- Copied pack carrying credential refs as values
- Display-name change invalidating fp1
- GPU job returning without pinned weights
- Graph Template `A→B→C→A` (must refuse — AD-6)
- Daemon crash losing Task Graph (must persist — AD-7)
- Dummy ResolvedRunConfig as “alternative system”

CIS map: `inputs/opportunities-journeys.md` (80 seeds clustered; OP-NEW-01..18). Enabling vs later apps distinguished. Not a backlog.
