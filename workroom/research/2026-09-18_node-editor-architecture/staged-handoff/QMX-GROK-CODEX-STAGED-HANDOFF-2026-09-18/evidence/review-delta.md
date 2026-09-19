# QMX reconciliation audit — review and implementation-delta addendum

Date: 2026-09-17
Status: review and source-inspected addendum; not accepted architecture or implementation authority.

## 1. What was reviewed

The supplied `QMX-RECON-20260917-185012.zip` was extracted without executing its Python files or bytecode. The five top-level reports and four diagnostic Markdown reports were read. The original files and the earlier Grok handoff were not modified.

The review distinguishes:

- **Audit-reported:** claims and test outcomes in the supplied reports.
- **Independently source-inspected:** current GitHub branch metadata, the comparison between the audit's code revision and current remote `integration`, and selected source files.
- **Recommendation:** proposed direction for the next architecture session; not a claim about current functionality.

No tests, brokers, QMX services, GPUs, or user interfaces were run in this review. No local uncommitted work was accessible through GitHub.

## 2. Material correction: the omitted commits contain the recent QML expansion

The audit inspected:

- Planning: `main@b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3`.
- Implementation: local `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e`.

The audit candidly records that the implementation worktree was 32 commits behind its configured remote-tracking branch and was not fetched or switched.

The independent GitHub check resolved remote `integration` to:

`270e992995c2378ca63cf6343254ef8140a8c97e`

GitHub's commit comparison reported `ahead_by=32`, `behind_by=0`, with `8510c03` as the merge base. The supplied audit is therefore useful as a bounded audit of the older checkout, not a current absence inventory.

### Corrections to carry forward

| Audit-era claim or limitation | Current source evidence | Correct treatment |
|---|---|---|
| QML Stage 0 research types were not implemented at the inspected revision. | Added `qml/src/qml/research/` contains `stage0.py`, `vocab.py`, `projection.py`, `collapse.py`, and admission helpers. The inspected `stage0.py` declares hypothesis, dictionary-citation, role-binding, graph and research-format types. | Mark Stage 0 as source-present at `270e992`, not documented-only. Do not task Grok with recreating it. |
| Research persistence was prospective at the inspected revision. | Added `qml/src/qml/host/research_store.py` implements explicit hypothesis save, canonical-blob persistence and reads under `research_root`. | Treat storage as an existing implementation to assess for completeness, integration, integrity and recovery. Do not claim it was left out entirely. |
| Research-to-governed authoring needed investigation. | Added conformance helpers, changes to `registration.py`, and `qml/src/qml/host/graduation.py` provide mill-origin handling and lineage stamping. | Inspect and reuse the new path; source presence does not prove a composed QML-to-QMB-to-QMN lifecycle. |
| Older research-corpus knowledge handling was described as a stub. | The comparison includes seed-root binding, research-corpus plugin changes, knowledge-service changes and discovery additions. | Refresh these findings; do not repeat the old stub description without checking the new implementation. |
| Federated Library discovery was not covered by the older checkout. | Added `qma/daemon/discovery/federated.py`, research-surface discovery, and `qma/wire/federated_discovery.py` with schema/tests. The inspected service describes concatenating CT-44 knowledge search with QMB artifact search, not a unified storage layer. | Record the existing discovery functionality separately from proposed general capability discovery or mini-app discovery. |

Corresponding test source was added, including Stage 0, research-store, projection, vocabulary, mill-graduation and federated-discovery tests. Test **existence** is established by the changed-file list and selected test-file inspection. Their execution outcome is **not** established by this review or by the audit's 54-test run on the older revision.

The documentation's provisional status and the existence of code are separate facts. Code presence does not silently ratify ADR-0023; a provisional document does not prove absence of implementation.

## 3. What remains supported

The comparison's changed-file list contains QML and QMA research/knowledge/discovery work. It contains no QMB, QMN or QMF package changes. Accordingly, it does not remove the audit's central composition findings. Two specific boundaries were also checked directly at `270e992`:

1. `qmb/src/qmb/config/compiler.py` still defines `ResolvedRunConfig` with required `book_fp1`, `bms_fp1`, `book_fragment_fp1` and `bms_fragment_fp1` fields. This supports the finding about the audited full-run configuration path; it is not a claim that arbitrary research Python cannot run outside that path.
2. `qmn/src/qmn/venue/port.py` still declares `VenueClientKind` as `CTRADER`, `REPLAY`, and `CONFORMANCE`. A new account/broker using the supported adapter is distinct from adding another broker technology.

The following remain useful audit findings, scoped to the searched implementation:

- QMF contains reusable identities, values, provenance and registration mechanisms.
- QMB's execution-fidelity ports are not the same interface as replacing admission, sizing and portfolio policy.
- QMN combines operational hosting with the present trading rulebook; a more general host/policy boundary remains a design question.
- QMA's execution Session and permission primitives do not by themselves establish the proposed durable authoring and app-use product sessions.
- QMA plugin contributions do not constitute a complete mini-app installation/presentation contract.
- QMF Data's provenance capabilities do not by themselves establish typed heterogeneous facts and dataset-recipe support.
- No supplied evidence demonstrates the complete cross-library, user-facing lifecycle or an alternative non-Book system passing through it.

Absence findings remain bounded. New local branches, uncommitted work, and paths not inspected may change them.

## 4. Assessment of evidence quality

The audit reports **54 selected tests passed in 12.95 seconds**, covering Book/BMS variants, venue selection, capability narrowing, plugin context and CLI transport. The evidence manifest states the command, test files, Python environment and redirected temporary directories.

This review did not rerun those tests. The archive includes test fixtures and generated test artifacts; they do not independently establish every reported test outcome. No full pytest console transcript was found in the non-cache file inventory.

The audit correctly limits the test claim: it does not prove an end-to-end QML/QMB/QMN run, a functioning desktop host, a live/demo broker connection, GPU provisioning, app-session isolation, or whole-system recovery.

### Diagnostic files are working notes, not parallel final verdicts

The final top-level reports reconcile earlier diagnostic assertions. Some retained notes are inconsistent with the final report:

- `diagnostics/FRAMEWORK-PROBE.md` uses labels such as “demonstrated composed run (documentation)” and discusses alternatives still subject to Book resolution. Documentation is not a demonstrated run, and that constrained alternative is not the operator's non-Book target.
- `diagnostics/SESSIONS-WORKFLOWS-RESEARCH.md` refers to the recording QMB transport, whereas the final manifest and matrix record a real CLI transport test surface.
- `diagnostics/ADVERSARIAL-REVIEW.md` discusses qualifications requested before the final delivery. The final report incorporates many of them; do not reintroduce the preliminary wording.

Use the five top-level reports as the consolidated audit account, retain diagnostic notes as provenance, and resolve factual conflicts against pinned source and executed checks. This addendum supplies a freshness correction, not a new authority hierarchy for the project.

## 5. Recommended architectural direction

The useful distinction is not “modular versus non-modular.” It is:

**Reusable primitives and several extension points exist; the complete system composition remains tied to one specific trading design.**

The recommended investigation remains compatibility-preserving refactoring of those boundaries. Preserve the current Book/BMS implementation and its tests while establishing whether an honest interface can support a materially different system. Do not impose a parallel framework, duplicate data store, second memory authority, or new scheduler without a demonstrated ownership need.

A new package may ultimately be justified. That is different from deciding in advance that the whole feature needs a new general library. QMF remains the single framework; stable shared contracts and existing owners should be evaluated first.

A compatibility adapter is acceptable where it genuinely preserves semantics. Dummy Book/BMS fields that conceal a different policy's meaning are not evidence of extensibility.

Do not freeze the audit's suggested contract placement as accepted design. In particular, deciding whether product/package/session records belong in existing application owners or a new focused module requires dependency analysis; they should not automatically all be put in `qmf-core`.

## 6. Acceptance journeys that prevent another narrowly coupled design

These are proposed acceptance journeys for architecture and later authorized implementation, not an instruction to build every example now.

### A. Two genuinely different trading systems

Use the current Book/BMS composition and a different risk/sizing composition that does not need Book/BMS or MIS. Preserve each system's actual semantics through authoring, experiment, validation and deployment-configuration checks. Define what is comparable rather than forcing all measures into the old R vocabulary. Preserve current-system behaviour with appropriate regression evidence.

Exercise one exported operation directly and through a workflow. Validate a distinct demo-account deployment configuration without submitting live orders. Test a sequential stopped/flat handover first; separately test refusals for incompatible or uncertain shared-account transitions.

### B. A non-trading data/ML workflow

Combine a historical price dataset with a non-price dataset, preserving their timestamps, versions, source identities and transformations. Produce a dataset, model or report without requiring a bot, Book/BMS, QML graduation or QMN deployment. This is essential to preserve the operator's data, sentiment and general ML experimentation scope.

### C. App-use to authoring handoff

An app-use session inspects an exact app/run/version and invokes permitted operations. It creates a change-request artifact, not an in-place source edit. A separate authoring session uses that artifact to create and test v2. Both sessions preserve their own context and capabilities. Navigation, reconnects, shared memory and app-supplied instructions cannot silently change their authority or account targets.

### D. Reuse without core edits

An exported capability is reused by another workflow/app and installed in another authorized QMX installation with that installation's own credentials. Test version compatibility, dependency removal, partial installation, logs, cancellation, failure and recovery. Rich UI styling is not required for the backend contract proof.

The first trading proof is not a cap on the platform. Nor should one successful path be called complete coverage of streaming, GPU execution, browser use, skill evaluation or multi-broker lifecycle requirements.

## 7. Next step for Grok

Proceed to architecture using the full transcript, the supplied audit, and this addendum. Do not ask the operator to repeat the intent discussion.

Start with a **focused revision reconciliation**, not another broad audit of the stale checkout:

1. Resolve the actual local worktrees, current remote refs and any concurrent changes. Preserve them.
2. Inspect the 32-commit delta and any later work. Refresh affected QML/QMA findings and run suitable bounded tests from the selected revision when permitted.
3. Record each finding as retained, superseded, partially addressed or unverified. Preserve the audit's original evidence revision rather than rewriting its history.
4. Continue with the cross-library architecture and explicit owner/contract decisions, using the existing Stage 0, research persistence and discovery work rather than rebuilding it.
5. Preserve the operator's two copilot profiles, QMF construction-kit intent, default-versus-alternative system distinction, Portfolio Manager terminology and explicit multi-account/provider/environment scope.
6. Treat CIS opportunities as seeds and scenario tests, not a mandate to implement everything. Preserve traceability to later user journeys.
7. Keep architecture, Documentation Factory, epics/stories and production implementation as distinct stages under the original session plan.

The enabling system is the deliverable. The final package count, workflow representation and UI technology remain recommendations to justify, not preselected answers.

## 8. Source manifest

### Supplied report sources

- `QMX-RECON-20260917-185012/RECON-RETURN.md`
- `QMX-RECON-20260917-185012/CAPABILITY-AND-COUPLING-MATRIX.md`
- `QMX-RECON-20260917-185012/INTENT-AND-AUTHORITY-LEDGER.md`
- `QMX-RECON-20260917-185012/SCENARIO-TRACES-AND-RISKS.md`
- `QMX-RECON-20260917-185012/EVIDENCE-MANIFEST.md`
- The four retained diagnostic Markdown files.

### Independent GitHub reads

- Branch: https://api.github.com/repos/MubarakHimself/QMX/branches/integration
- Compare, retrieved through the GitHub compare-commits connector action: https://github.com/MubarakHimself/QMX/compare/8510c032496bb870824ecc5c4f807e8a4e4f167e...270e992995c2378ca63cf6343254ef8140a8c97e
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qml/src/qml/research/stage0.py (source lines 1–180)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qml/src/qml/host/research_store.py (source lines 1–160)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qml/src/qml/host/graduation.py (complete file)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qmx-agents/packages/qma-daemon/src/qma/daemon/discovery/federated.py (source lines 1–110)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qml/tests/test_mill_graduation.py (source lines 1–100; not executed)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qmb/src/qmb/config/compiler.py (source lines 114–220)
- https://github.com/MubarakHimself/QMX/blob/270e992995c2378ca63cf6343254ef8140a8c97e/qmn/src/qmn/venue/port.py (source lines 34–85)

This is a selected-source delta review, not a complete review of every changed line or an operational certification.
