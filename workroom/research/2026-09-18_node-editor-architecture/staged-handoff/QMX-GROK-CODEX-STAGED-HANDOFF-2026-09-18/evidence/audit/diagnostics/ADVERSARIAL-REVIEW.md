# Adversarial review of the five audit reports

Review date: 2026-09-17. Scope: reports under `QMX-RECON-20260917-185012`, compared with the cited main/integration evidence. No reports or repository files were modified.

## Verdict

The audit can ship with minor corrections/qualification; it should not ship literally unchanged. The central conclusion is sound: current QMB/QMN composition is Book/BMS-centered, while QMF intent is a reusable construction kit. No report falsely claims a composed QML→QMB→QMN proof. The corrections below prevent recommendations from being read as ratified architecture or universal host law.

## Findings

| Severity | Finding and required correction | Evidence |
|---|---|---|
| High | `RECON-RETURN.md:61` calls “protection” a universal QMN host law while `:59` correctly identifies KSA/SQS and Book/BMS runtime as current rulebook. Narrow the universal list to demonstrably host-level controls (identity/credential isolation, command idempotency, reconciliation/unknown outcome, refusal/state-transition safety). Mark protection/KSA as policy-dependent until the boundary is ruled. | `docs/components/trading-node.md:1-35,541-545`; `docs/AGENTS.md` DEC-0192/0193 |
| High | Recommendations in `RECON-RETURN.md:24,61,67,73` (“should become”, “needs”) are sensible architecture proposals but not ratified decisions. Add “proposal requiring architecture preflight/ADR” wherever a new system-policy, session-context, workflow, or QMF Data contract is suggested. | `docs/AGENTS.md` hard rules; ADR-0022 ratified, ADR-0023 provisional; `docs/gap-report.md` GAP-0051, GAP-0058, GAP-0061–0063 |
| Medium | `CAPABILITY-AND-COUPLING-MATRIX.md:24-26` says QMF Data has no general typed payload. This is accurate for the inspected implementation, but avoid implying QMF Data is incapable by design: describe the bounded absence as “not found in inspected source,” with additive/versioned extension as a candidate. | `qmf/data/observation.py:450-690`; `qmf/data/ingest.py:147-388`; report’s own evidence manifest |
| Medium | `CAPABILITY-AND-COUPLING-MATRIX.md:57` says the production venue selector is closed and another broker requires editing the selector owner. Correct, but distinguish “another cTrader broker/account” (configuration reuse) from “different broker technology” (selector/adapter extension). `RECON-RETURN.md:59` mostly does this; mirror that precision in the matrix. | `qmn/src/qmn/venue/port.py:39-191`; `qmn/tests/test_qmn_venue_selection.py:80-245`; `docs/architecture/dependencies.yaml:199-210` |
| Medium | Session findings are directionally correct, but `RECON-RETURN.md:43-45` describes desired app-use behavior (“should be bound”, “should expose”) next to current-state claims. Label those sentences as target semantics; current QMA only proves execution Session fields and spawn-time capability narrowing. | `qma/core/ontology/records.py:168-180`; `qma/core/control/runtime.py:231-285`; `qma/daemon/capabilities/spawn.py:36-176`; `docs/components/qma-core.md:59-73` |
| Medium | The reports correctly reject forcing all workflows through Missions (`RECON-RETURN.md:71-73`). Keep that as an intent/architecture constraint, not evidence that a general workflow contract should be added now; the proposed “small system/workflow description contract” needs a concrete second execution model and preflight. | `INTENT-AND-AUTHORITY-LEDGER.md:31,87`; `docs/components/qma-core.md` procedure/graph boundaries |
| Low | “QMN MIS source/tests exist” in `CAPABILITY-AND-COUPLING-MATRIX.md` is plausible from the integration tree, but the same row correctly says training/shadow authority is deferred. Keep “source/tests exist” separate from “MIS is production-ready”; do not let the row imply model validity or rollout readiness. | `qmn/mis`; `docs/gap-report.md` GAP-0051; `docs/components/trading-node.md:541` |
| Low | The audit’s “54 selected tests passed” is a claim about the prior audit run, not independently re-executed in this review. Preserve the distinction already present in `EVIDENCE-MANIFEST.md:107-109`: selected isolated tests passed; no live/demo, UI, alternative-policy, app-session or composed product proof. | `EVIDENCE-MANIFEST.md:107-109,132` |

## Specific anti-drift checks

- No evidence of universalizing Book/BMS in the reports; they explicitly call it a current composition/default and identify the operator correction that it is not the framework ceiling (`INTENT-AND-AUTHORITY-LEDGER.md:23,60,78`).
- No workflow-through-Mission drift; the reports explicitly preserve QMA’s agentic scope.
- No mini-app or UI implementation claim; mini-app/session/UI items are marked deferred or missing.
- No broker-selector readiness claim; the closed enum and different-technology limitation are stated.
- No app-session readiness claim; missing durable context/profile is stated.
- No false paper/live/demo equivalence; the reports preserve separate Book-level Paper mode, demo account, and QMN `paper|live` semantics.

After the wording qualifications above, the audit is safe to ship as a bounded reconciliation and diagnostic proposal. It must not be presented as an implementation authorization, architecture ratification, live-money readiness statement, or proof that an alternative system already runs end to end.
