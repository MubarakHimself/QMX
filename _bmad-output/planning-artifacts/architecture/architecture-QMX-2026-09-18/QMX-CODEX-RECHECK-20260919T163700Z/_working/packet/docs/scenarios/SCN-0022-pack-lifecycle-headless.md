---
id: SCN-0022
title: Pack lifecycle atomic roster, export scanner oracle, and headless door parity
type: scenario
status: ratified
component: COMP-QMA-DAEMON
depends_on: [COMP-QMA-DAEMON, COMP-QMA-WIRE, COMP-QMB]
decisions: [DEC-0423, DEC-0431, DEC-0434, DEC-0443, DEC-0450]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md, _docwork/workflows-increment-brief.md, _docwork/riders/workflows-construction-kit-2026-09-19.md, docs/decisions/ADR-0024-workflows-construction-kit.md]
generated: 2026-09-19
verified: 2026-09-19
stale_after: 90d
---

# SCN-0022: Pack lifecycle atomic roster, export scanner oracle, and headless door parity

This scenario pins J08/J12 pack and door honesty: pack lifecycle transitions journal with atomic roster publication; an independent export scanner is the oracle for secrets (manifest self-assertion is not evidence); QMB remains the only operator CLI; an unsupported door returns typed `unsupported_door`, never a newly minted `qma`/`qmn` CLI. [DEC-0431] [DEC-0434] [DEC-0443]

This document is a **specification of intended behavior**, not evidence that the code does this today. Class/test existence is not end-to-end demonstration; proposed connects are not implemented at `integration@270e992`. [DEC-0450]

## Given

A pack is versioned: manifest, contribution list, requested capabilities, compatibility range, migrations. Pack states: `downloaded` → `installed` → `validated` → `enabled` ⇄ `disabled` → `uninstalled`. Install / configure / enable / disable / validate / pin / rollback / dependency-removal / export / import are host operations. First-party trust in v1; custom packs are explicit operator enable. [DEC-0431] [DEC-0443]

Three pack states stay distinct from session authority: **installed** (bytes present) ≠ **enabled/activated** (roster on) ≠ **session-granted** (`granted_ops`). Published package ≠ activation on a trading account. [DEC-0443]

Supported-door sets are per `op_id`. Deep behaviour of an AD-3 operation is identical across that operation’s supported doors. QMB remains the only operator CLI; QMA and QMN ship no operator CLI — their operations use library and qma-wire adapters (and may be invoked through QMB-owned orchestration when the owner is QMB). [DEC-0434]

Four composition modes (J12) remain available without core edits: consume artifact fp1; invoke exported op through the envelope; Graph Template coordinates two apps; composite app cites contribution ids. [DEC-0423]

## When

1. A pack is installed, validated, and enabled (or a partial/failed path is attempted).
2. The pack is exported (or import is attempted on a second QMX).
3. An operation is invoked through a supported door and, separately, through an unsupported door.
4. A ContributionHit from an enabled pack is pinned, then the pack is disabled (honesty shared with SCN-0018). [DEC-0431] [DEC-0443] [DEC-0434]

## Then

**(1) Atomic roster publication.** Each lifecycle transition is journaled. Roster publication is atomic (stage, fsync, swap). Failed validation/migration restores the last usable roster. Partial install rolls back to the last usable roster. Missing dependency is a hard error at enable, not warning-and-continue. [DEC-0431] [DEC-0443]

**(2) Migrations are constrained.** Migrations follow QMA AD-21 (`down` or `forward_only` with operator confirmation). Uninstall names dependants; in-flight pinned runs keep the bytes they started with. Side-by-side versions allowed; running work stays pinned to the instance it started. [DEC-0443]

**(3) Export scanner is the oracle.** An independent export scanner must prove absence of secret values, private paths, and transcripts, and must rewrite remaining secrets to typed refs. Manifest `exports_secrets: false` without a passing scan is **not** evidence. Self-asserted cleanliness does not authorize export. [DEC-0431] [DEC-0443]

**(4) Headless door parity.** Behaviour of a supported operation is identical across its supported doors. Unsupported door → typed `unsupported_door`, never a newly minted `qma`/`qmn` CLI. A useful log/progress panel is not a general shell. [DEC-0434]

**(5) QMB is the only operator CLI.** QMA and QMN do not ship an operator command line. [DEC-0434]

**(6) Pin after disable.** Pin of a ContributionHit stores `(qualified_id, package_version, availability_revision)`. Invoke revalidates; disabled/uninstalled → `unavailable` or `tombstone`, never another version. [DEC-0443]

## Failure branches

**Branch A — warning-and-continue on missing deps.** Enable proceeds with advisory missing dependencies (Hermes-style). Forbidden: hard error at enable; previous roster stays consistent on failure. [DEC-0431] [DEC-0443]

**Branch B — self-asserted exports_secrets.** Manifest declares `exports_secrets: false` and export proceeds without a passing independent scan. Forbidden: scanner is the oracle. [DEC-0431] [DEC-0443]

**Branch C — private path ids / transcripts in export.** Export carries private lineage paths, transcripts, or raw secret values. Forbidden. [DEC-0431] [DEC-0443]

**Branch D — minting a qma/qmn CLI for unsupported door.** An unsupported door invents a new operator CLI instead of typed `unsupported_door`. Forbidden. [DEC-0434]

**Branch E — non-atomic roster / corrupt index.** Failed enable leaves a half-published roster. Forbidden: restore last usable roster. [DEC-0443]

**Branch F — claiming pack/outbox machines implemented at 270e992.** Treating this scenario as executed proof on the inspect SHA. Forbidden. [DEC-0450]

## Worked numbers

None. This is a registry-independent lifecycle and door-parity scenario. The load-bearing chain is journaled state transitions → atomic roster swap → independent export scan oracle; unsupported door → `unsupported_door`; QMB-only operator CLI (DEC-0431, DEC-0434, DEC-0443).
