# Evidence manifest

Audit completed against local state at 2026-09-17T18:55:26+03:00. Existing repository and operational systems were read-only. Generated files, extracted transcript and disposable test/cache paths are confined to C:/Users/Mubarak/Downloads/QMX-RECON-20260917-185012.

## Revision and checkout manifest

| Item | Recorded state |
|---|---|
| Planning root | C:/Users/Mubarak/Desktop/QMX |
| Planning branch/HEAD | main at b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3 |
| Planning commit | 2026-09-16T21:58:21+03:00, “docs: CONNECT, workbench, and QML research planning plus corpus absorption.” |
| Planning dirty state | No tracked changes reported; many pre-existing untracked planning/research artifacts, including .tmp-epic-037.diff, _bmad-output/brainstorming, party-mode, UX working files, epansion_session and workroom/research notes. Audit did not edit or remove them. |
| Implementation worktree | C:/Users/Mubarak/Desktop/QMX/.worktrees/integration-inspect |
| Implementation branch/HEAD | integration at 8510c032496bb870824ecc5c4f807e8a4e4f167e |
| Implementation commit | 2026-09-15T13:32:20+03:00, “story S1: contain generation-gaps test reads against SKY-D325” |
| Implementation status | Clean; branch reported 32 commits behind origin/integration. No fetch/switch/rebase was performed. |
| Other linked worktrees | ui af66288; mql5-library 430fb7d; several epic/chunk worktrees including 270e992. None were modified. |
| Submodules | git submodule status failed because .gitmodules has no mapping for .worktrees/ui; no submodule conclusion was inferred. |
| Relevant processes | Node/Codex processes plus Hermes Python were observed. No process named qma or qmn was observed. Process-name inventory is not proof that no differently named service was running. |

The prompt's earlier main b8b4d21 pointer still matches planning HEAD. Its earlier code pointer 270e992 is not the inspected integration HEAD; the current dedicated integration worktree is 8510c03 and behind its remote. This branch mismatch limits claims about newest implementation.

## Authoritative and non-authoritative inputs

### Operator/session inputs

- C:/Users/Mubarak/Downloads/QMX-CODEX-RECONCILIATION-AUDIT-PROMPT.md — audit instructions, not architecture.
- session-input/Explore-Node-Editor-Architecture.md — complete 1,239-line discussion transcript.
- session-input/images/image-001.png — QMX dashboard/terminal reference.
- session-input/images/image-002.png — Taskade assistant/workspace/flow/app-preview reference.

### Current documentation authority

- docs/AGENTS.md
- docs/constitution.md
- docs/architecture/overview.md
- docs/architecture/dependencies.yaml
- docs/glossary.md
- docs/components and docs/contracts
- docs/decisions/ADR-0017, ADR-0018, ADR-0019, ADR-0020, ADR-0022 and ADR-0023
- docs/gap-report.md

Status distinctions retained:

- ADR-0022 Workbench is ratified/accepted.
- ADR-0023 QML research expansion is provisional; DEC-0380 alone is recorded as the ratified direct paradigm.
- The 2026-09-16 architecture spine and Documentation Factory handoff explicitly say proposed/not operator-accepted. They were inspected but not revised.
- “source-inspected” contract stamps are not treated as end-to-end proof.

### Prior handoff/seed

- workroom/research/2026-09-16_grok-handoffs/02-workflows-architecture-prompt.md
- _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/DOCUMENTATION-FACTORY-HANDOFF.md

These are non-authoritative drafts/prompts. The latter expressly says proposed and was not changed.

## Principal local evidence

| Claim | Source |
|---|---|
| QMF is a toolbox; QML/QMB/QMA/QMN are application consumers | docs/architecture/overview.md:16; docs/architecture/dependencies.yaml:100–210, 300–383 |
| Workbench chooses reuse and Book/BMS candidate variants | docs/decisions/ADR-0022-workbench-expansion.md:37–54 |
| Workbench knows QMA→QMB still needs connect/composed proof | ADR-0022:23, 46, 88 |
| QML Stage 0 package is provisional and absent in inspected code | docs/decisions/ADR-0023-qml-research-expansion.md:17–25; docs/components/qml.md:224 |
| QMB run config mandates Book/BMS | qmb/src/qmb/config/compiler.py:114–216, 381–468, 475–648 |
| QMB risk path mandates ReplayBinding/CT-23/CT-29 | qmb/src/qmb/execution/risk.py:38–171 |
| Book/BMS analysis is complete candidate, not generic policy | qmb/src/qmb/analysis/variants.py:169–230, 448–520 |
| QMB execution fidelity has real ports | qmb/src/qmb/execution/ports.py:906–1025 |
| QMN config layers are roster/BMS/Book/defaults | qmn/src/qmn/config/compiler.py:50–132, 349–421 |
| QMN venue port exists but selector is closed | qmn/src/qmn/venue/port.py:39–191; qmn/tests/test_qmn_venue_selection.py:80–245 |
| Multi-account has no global singleton | qmn/src/qmn/config/roster.py:129–225, 319–532 |
| Provider source is orthogonal to VenueId | qmf/data/ingest.py:123–190; qmf/data/observation.py:450–480 |
| Quote download port is swappable but quote-shaped | qmb/src/qmb/data/ports.py:1–123 |
| Current QMA Session is not a product app session | qma/core/ontology/records.py:168–180; qma/core/control/runtime.py:231–285 |
| Agent capabilities freeze at spawn | qma/daemon/capabilities/spawn.py:36–176 |
| Context compiler is replaceable but default is handle refs only | qma/core/ports/context.py:13–25; qma/daemon/context/compiler.py:13–22 |
| Memory provider is a desk-scoped seam; external backend deferred | qma/core/ports/memory.py:503–550 and refusal for GAP-0072 |
| UI/app contribution contract is deferred | docs/architecture/dependencies.yaml:343–350; docs/gap-report.md:248 (GAP-0081) |

All implementation paths above are relative to C:/Users/Mubarak/Desktop/QMX/.worktrees/integration-inspect unless prefixed docs/, which refers to the planning checkout.

## Diagnostic commands and outcomes

Safe read commands included:

- git rev-parse --show-toplevel; git branch --show-current; git rev-parse HEAD; git status --short --branch
- git worktree list --porcelain
- git submodule status
- git log -1 --format
- rg --files and rg -n over named docs/source/tests
- Get-Content with line numbering for cited files
- Get-Process filtered to python/qma/qmn/node/uvicorn/docker
- ZIP entry inventory and extraction to the audit directory

Targeted deterministic test:

    C:/Users/Mubarak/Desktop/QMX/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
      --basetemp C:/Users/Mubarak/Downloads/QMX-RECON-20260917-185012/diagnostics/pytest-tmp
      qmb/tests/test_analysis_book_bms_variants.py
      qmn/tests/test_qmn_venue_selection.py
      qmx-agents/packages/qma-daemon/tests/test_capability_narrowing_permissions.py
      qmx-agents/packages/qma-daemon/tests/test_plugin_context.py
      qmx-agents/packages/qma-daemon/tests/test_qmb_cli_transport.py

Environment: Python 3.14.6, pytest 9.1.1. PYTHONPATH referenced the inspected worktree's package source directories. Bytecode/temp output was redirected to the audit directory. Outcome: 54 passed in 12.95 seconds.

What this proves: the isolated Book/BMS candidate path, fixed venue selector behavior, capability narrowing, plugin context and CLI transport tests pass at 8510c03.

What it does not prove: a composed QML→QMB→QMA/QMN product run, UI behavior, a live/demo broker connection, alternative non-Book policy, app-session isolation, mini-app installation, remote/GPU execution or disaster recovery.

## External primary references

Retrieved 2026-09-17:

- JSON Render official repository: https://github.com/vercel-labs/json-render — Apache-2.0; repository describes a guarded component/action catalog, schema-constrained specs and multiple renderers. The catalog can be a presentation vocabulary; it is not execution, persistence or authorization.
- JSON Render catalog docs: https://json-render.dev/docs/catalog
- MCP Apps official overview: https://modelcontextprotocol.io/extensions/apps/overview — tool-linked ui:// resources, sandboxed iframe host, lifecycle/context/capability negotiation and host-proxied calls. This can inform a QMX app host protocol but cannot grant domain permissions.
- MCP Apps official API: https://apps.extensions.modelcontextprotocol.io/api/ — the inspected documentation identified ext-apps 1.1.2 in the API path; no QMX dependency is recommended or adopted by this audit.

Observed facts are limited to the official pages above. Fit recommendations are audit inference.

## Supporting diagnostics

- diagnostics/TRANSCRIPT-LEDGER-DRAFT.md — complete transcript extraction/ledger.
- diagnostics/FRAMEWORK-PROBE.md — bounded QMF/QML/QMB/QMN source trace.
- diagnostics/SESSIONS-WORKFLOWS-RESEARCH.md — bounded QMA/workflow and primary-source trace.
- diagnostics/ADVERSARIAL-REVIEW.md — independent challenge of the five reports. Its central verdict was substantively sound with wording qualifications; the requested qualifications about QMN host safety, proposal status, data payload scope, broker technology, product-session target semantics, workflow evidence and test boundaries were reconciled before delivery.
- diagnostics/pytest-tmp and diagnostics/pycache — disposable diagnostic side effects only.

## Untested and blocked claims

- No Reticle verdict: this was a read-only backend/architecture audit and no user-facing change was made. A running UI was not needed or proven.
- No live/demo connection, order submission, account mutation, paid API call, remote provision or training job was attempted.
- No full repository test suite was run; the audit used a risk-focused 54-test slice.
- No fetch means implementation newer than local integration 8510c03 was not inspected.
- No bounded pass established every public method or every document. Absence statements name the searched roots/terms and are not global proofs.
- No authoritative complete-system package contract was found. This is a bounded finding, not proof that no experimental branch contains one.
- Persistence primitives were inspected; an end-to-end cross-store backup/restore was not executed.
- The process inventory cannot rule out services under unrelated process names.

## Repository preservation

No repository source, canonical documentation, manifest, lockfile, setting, production data, branch, commit, stash, worktree or earlier handoff was changed. No architecture spine was created, updated or ratified.
