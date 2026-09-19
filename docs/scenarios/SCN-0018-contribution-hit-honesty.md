---
id: SCN-0018
title: ContributionHit pin honesty — disable yields tombstone, never another version
type: scenario
status: ratified
component: COMP-QMA-WIRE
depends_on: [COMP-QMA-WIRE, COMP-QMA-DAEMON]
decisions: [DEC-0415, DEC-0422, DEC-0443, DEC-0449, DEC-0450]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md, _docwork/workflows-increment-brief.md, _docwork/riders/workflows-construction-kit-2026-09-19.md, docs/decisions/ADR-0024-workflows-construction-kit.md]
generated: 2026-09-19
verified: 2026-09-19
stale_after: 90d
---

# SCN-0018: ContributionHit pin honesty — disable yields tombstone, never another version

This scenario pins J08/J24 contribution discovery honesty: a live `ContributionHit` may be pinned, and after the contributing plugin is disabled or uninstalled the pin resolves to typed `unavailable` or `tombstone` — never to another package version, never to a stale fp1. A hit is not a grant. [DEC-0415] [DEC-0443] [DEC-0449]

This document is a **specification of intended behavior**, not evidence that the code does this today. At `integration@270e992` federated discovery is still `KnowledgeHit|ArtifactHit` only; `ContributionHit` is not on the wire. [DEC-0450]

## Given

Product discovery concatenates typed hits and is never a fourth store and never a door run. The frozen hit classes include `ContributionHit` with identity `{hit_class: contribution, plugin_id, point, qualified_id, package_id, package_version}` from live `published_contributions()`. That tuple is never fp1, never a registry kind, and never an `ArtifactHit.kind`. [DEC-0415] [DEC-0449]

An exported pack that passed the independent secret scanner is installed and enabled on a second QMX with that installation’s credentials. Pack `contributes` entries expand to `ContributionHit` at enable. Discovery listings distinguish published vs configured vs granted vs reachable vs healthy. [DEC-0415] [DEC-0443]

Pins store `(qualified_id, package_version, availability_revision)`, not a descriptor digest. Session-granted (`granted_ops`) is a separate AD-8 state from pack enablement. [DEC-0415] [DEC-0443]

## When

1. Discovery returns a live `ContributionHit` for a contributed operation.
2. A caller **pins** that hit as `(qualified_id, package_version, availability_revision)`.
3. The operator **disables** or **uninstalls** the contributing plugin (or the contribution otherwise leaves the live published roster).
4. A later invoke (or pin revalidation) targets the same pin tuple. [DEC-0443]

## Then

**(1) Hit is not a grant.** Publishing or discovering a `ContributionHit` does not authorize invoke. [DEC-0415] Tool availability still requires the intersection of published hits, host grants, product-session GrantRecords, and health. [DEC-0422]

**(2) Pin revalidation is mandatory.** Invoke revalidates the pin against the live published roster and availability revision. [DEC-0443]

**(3) Disable/uninstall → typed unavailable or tombstone.** Missing, disabled, or uninstalled plugin yields typed `unavailable` or `tombstone`. The pin does **not** silently resolve to another `package_version`, does not substitute a different contribution, and does not surface a stale fp1. [DEC-0415] [DEC-0443]

**(4) In-flight pinned runs keep their started bytes.** Uninstall names dependants; work already pinned to an instance keeps the bytes it started with. Side-by-side versions remain allowed; running work stays on the instance it started. [DEC-0443]

**(5) DEC-0389 remainder stands.** Occupancy none on the discovery path; no `hit_class: strats`; hypotheses stay off the Library facade; daemon never `import qmb`; QMB never opens daemon sqlite. [DEC-0449]

## Failure branches

**Branch A — silent version retarget.** After disable, a resolver returns a different `package_version` or another contribution for the same `qualified_id`. Forbidden: the design requires `unavailable`/`tombstone`, never another version. [DEC-0415] [DEC-0443]

**Branch B — hit treated as grant.** A skill, listing, or copilot prose treats a published `ContributionHit` as sufficient authority to invoke. Forbidden: a hit is not a grant. [DEC-0415]

**Branch C — ContributionHit as fp1 / registry kind.** A caller fingerprints the hit onto the Artifact rail or registers it as a Library kind. Forbidden: identity is the live published tuple only. [DEC-0415] [DEC-0449]

**Branch D — claiming implemented at 270e992.** Treating this scenario as proof that `ContributionHit` exists on the wire at the inspect SHA. Forbidden: wiring honesty records absence. [DEC-0450]

## Worked numbers

None. This is a registry-independent identity and control-flow scenario. The load-bearing chain is pin tuple `(qualified_id, package_version, availability_revision)` → disable/uninstall → `unavailable`/`tombstone`, never another version (DEC-0415, DEC-0443).
