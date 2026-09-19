# Codex challenge handoff (Stage A freeze)

Candidate ID: `qmx-workflows-arch-2026-09-18-a`
Status: **AWAITING_CODEX_CHALLENGE**
Not ratified. Not implemented.

## What to attach

1. This folder’s freeze ZIP: `CODEX-CHALLENGE-INPUTS.zip` (same directory as this file, produced at freeze).
2. The full operator transcript `Explore-Node-Editor-Architecture.md` if it is not already inside the ZIP (size ~287 KB; include if the ZIP lists it).
3. Optional: `QMX-REFERENCE-RECON-20260918T082954Z` (already summarised in STACK-AND-EVALUATION.md and RECON-RETURN.md).

## Launch prompt (paste into a new Codex session)

```text
Read 12-CODEX-SCENARIO-AND-ARCHITECTURE-CHALLENGE.md and the attached
CODEX-CHALLENGE-HANDOFF.md plus ARCHITECTURE-CANDIDATE-MANIFEST.json.
Perform the independent two-pass scenario and architecture challenge.
Derive requirements-based cases BEFORE reading the proposed design,
then test it against BDD-style behaviours, state/failure sequences,
cross-app and cross-library interactions.

Use CIS and as many useful subagents as available. No arbitrary
case-count ceiling; report coverage and holes rather than cosmetic volume.

Preserve the pinned candidate hashes and current repository.
Do not implement or ratify the design. Return the challenge package
for Grok (CODEX-CHALLENGE-RETURN.md and the files listed in section 7
of 12-CODEX-SCENARIO-AND-ARCHITECTURE-CHALLENGE.md).
```

## What Codex must review

- `ARCHITECTURE-SPINE.md` (AD-1..AD-22)
- `REQUIREMENTS-ADDENDUM.md`, `CONTRACTS.md`, `JOURNEYS.md`
- `CONFLICT-REGISTER.md` (especially C-05 L36 hold)
- `RECON-RETURN.md` (freshness: docs `b8b4d21`, impl `270e992`)
- Internal reviews under `reviews/`
- Existing J01–J24 and OP seeds are **coverage floor**, not ceiling

## Independence rule

Pass I: freeze `INDEPENDENT-SCENARIO-BASELINE.md` before reading the spine.
Pass II: then challenge the actual ADs.

Treat mutmut as a test-strength principle, not a required run on the shared tree.

## Return to Grok with

`13-GROK-RESUME-AND-RECONCILE.md` plus Codex’s ZIP. Do not start Documentation Factory.
