# Source preservation and evidence selection

Package prepared: 2026-09-17.

The new documents in the package are an assistant-authored consolidation of the conversation and a proposed Grok assignment. They are not an additional code audit, a verbatim transcript, a ratified architecture or proof of operational readiness.

## Original sources preserved

- `original-workflows-architecture-prompt.md`: unchanged source of the initial architecture-only session and downstream handoff boundaries.
- `codex-audit-instructions.md`: unchanged audit prompt, preserved as historical instructions for understanding the returned evidence. Its audit-only stop rule is **not** the current Grok assignment.
- `audit/`: five consolidated reports plus four diagnostic Markdown notes extracted byte-for-byte from the user-supplied audit ZIP.
- `review-delta.md`: unchanged later source-inspection review and audit-baseline correction.
- `earlier-session-snapshot.md` and `images/`: unchanged earlier transcript/image material carried in the audit ZIP. This snapshot is historical and must not replace the newly exported transcript attached by the operator.
- `../reference-images/`: copies of the user-supplied mounted UI references; no images were generated or edited for this handoff.

## Audit archive selection

Original filename: `QMX-RECON-20260917-185012.zip`

Original archive size: 11341689 bytes.

Original archive SHA-256: `1d00609a54b8a9900b622ca359b2f2fe324bac4119d8387d8296916f4d054aed`.

Archive entries: 1128, of which 1060 are files.

Copied source entries: 12. Copied authored audit reports: 9.

The original ZIP is not duplicated inside this package. Python bytecode/cache and disposable pytest fixture/generated-state material are deliberately excluded from the selected evidence copy. No archive Python or bytecode was executed. This does not create or reproduce an executed test log; the 54-test outcome remains the audit's reported result with its stated scope. The original audit ZIP remains unchanged in the conversation.

`SOURCE-SELECTION.json` records each copied archive entry and hash. `../MANIFEST.json` hashes every packaged file (except itself).

## Freshness and authority

Read `../03-EVIDENCE-BASELINE-AND-DELTA.md` and `review-delta.md` together with the audit. Newer source presence corrects old absence claims; it does not silently ratify proposed documentation. Some diagnostic working notes were qualified by the final reports.

No new external source checking or code execution took place in the final packaging step. The reference-study plan is a queue for Grok to research afresh, not a claim that those products were newly tested here.

The operator's new full transcript is a separate attachment. No transcript of missing turns has been fabricated.
