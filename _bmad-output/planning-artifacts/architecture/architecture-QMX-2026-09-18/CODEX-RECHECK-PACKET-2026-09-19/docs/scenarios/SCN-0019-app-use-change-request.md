---
id: SCN-0019
title: App-use mints change-request; authoring plus operator applies; v1 untouched
type: scenario
status: ratified
component: COMP-QMA-DAEMON
depends_on: [COMP-QMA-DAEMON, COMP-QMA-WIRE, COMP-QMA-CORE]
decisions: [DEC-0421, DEC-0422, DEC-0442, DEC-0450]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md, _docwork/workflows-increment-brief.md, _docwork/riders/workflows-construction-kit-2026-09-19.md, docs/decisions/ADR-0024-workflows-construction-kit.md]
generated: 2026-09-19
verified: 2026-09-19
stale_after: 90d
---

# SCN-0019: App-use mints change-request; authoring plus operator applies; v1 untouched

This scenario pins J01: an installed app-use product session may mint a `change_request` staging artifact (with base hashes) after inspecting a run, but must not apply implementation edits. Only an authoring product session under an operator principal applies; the v1 instance, grants, and running jobs stay unchanged. [DEC-0421] [DEC-0422] [DEC-0442]

This document is a **specification of intended behavior**, not evidence that the code does this today. At `integration@270e992` `product_session` is absent; Operation descriptor / InvocationEnvelope / GrantRecord are absent. [DEC-0450]

## Given

An installed app instance v1 exists with GrantRecords for inspect ops. A `product_session` with profile `app-use` (immutable at create) is open; ids are `psess:` and are not QMA Session `sess:` ids. Cardinality is one product_session to many QMA Sessions. [DEC-0421]

Tool availability is the intersection of published ContributionHits, host grants, product-session GrantRecords, and health. Skills describe behavior; they do not grant. [DEC-0422]

App-use may inspect, invoke exposed operations, adjust permitted runtime inputs, and mint a change-request staging kind. It must not edit package source, install code, elevate grants, or retarget accounts. [DEC-0421]

## When

The user asks the app-use copilot to explain a run and request a filter change:

1. App-use mints a `change_request` staging artifact.
2. A new authoring session opens with scoped refs (not the private transcript).
3. Authoring validates; an operator principal applies (or refuses).
4. Path: app-use → change request → authoring → validation → v2; v1 stays. [DEC-0421] [DEC-0442]

## Then

**(1) Change-request payload is complete.** The staging artifact MUST include: source `psess:`, source `instance_id`/`config_revision`, target refs, **base hashes** of those refs, `context_revision` at mint, `request_hash`, typed patch, validation result (`conflict` \| `rebase-required` \| `valid`), and — after authoring apply — apply evidence. [DEC-0442]

**(2) App-use never applies.** App-use mints only. Applying is authoring + operator principal. `promote` remains L17 and is not this path. [DEC-0421] [DEC-0442]

**(3) v1 is untouched.** The v1 instance, its GrantRecords, and running jobs are unchanged by the mint. Installation/upgrade MUST NOT mutate an existing row’s `granted_ops` or retarget `app_instance_id` as a side effect of this handoff. [DEC-0421]

**(4) Authoring opens with scoped refs.** The new authoring session receives typed `selected_refs`, not the app-use private transcript and not layout/widget trees. [DEC-0421]

**(5) Prose is not authorization.** Skill text cannot grant `role.set_base` or widen tools; availability remains the grant intersection. [DEC-0422]

**(6) Mutations are CAS.** Select/grant mutations bump `context_revision` under compare-and-set on `expected_revision`. Duplicate `command_id` returns the prior durable result. Reconnect resumes queries/events; it does not replay unacked intent. Tab change writes nothing. [DEC-0421] [DEC-0442]

## Failure branches

**Branch A — app-use writes package source.** App-use edits implementation, installs code, or applies its own change-request. Forbidden. [DEC-0421] [DEC-0442]

**Branch B — grant widening or account retarget.** Mint or apply elevates grants, retargets accounts, or substitutes a different `app_instance_id` without explicit re-grant. Forbidden. [DEC-0421] [DEC-0422]

**Branch C — stale base hash applies.** Authoring applies against refs whose base hashes no longer match (without conflict/rebase). Forbidden: validation must surface `conflict` or `rebase-required`. [DEC-0442]

**Branch D — tab switch patches context.** A UI tab change is treated as a context or grant mutation. Forbidden: tabs write nothing; sessions own context. [DEC-0421]

**Branch E — claiming runtime present at 270e992.** Treating this scenario as proof that `product_session` or GrantRecord exist on the inspect SHA. Forbidden. [DEC-0450]

## Worked numbers

None. This is a registry-independent identity and authority-flow scenario. The load-bearing chain is app-use mint (with base hashes) → authoring + operator apply → v1 unchanged (DEC-0421, DEC-0442).
