# QMX QA Fix Ledger

Objective and method: `FIX-GOAL.md`. Resume from the first row not marked `PROVEN`; re-read the card, its consolidated finding rows, and the relevant epic L6 review before editing.

## Baseline (2026-08-27)

- `uv sync --group dev`: passed.
- `uv run poe test`: passed — 3,899 passed, 14 skipped, 86.97% coverage, 487.10 seconds.
- `uv run poe check`: failed — `fmt-check` reported 13 files requiring formatting; the sequence stopped before the scanner stages.
- Separate QA gate added: `qa-verify = "pytest qa/tests -q"` (not part of the default `test` task).

| card id | finding ids | status | commit sha | proving test(s) | notes |
|---|---|---|---|---|---|
| FC-01 | QMX-F001, QMX-F002 | PROVEN | `0ae38ec` | `qa/tests/epic_10/test_h_control_action.py` (13 passed); qmf-risk unit suite (613 passed); Epic-10 QA (108 passed) | Act discriminator now reaches mint, scope, arbitration, and execution-target enforcement. Risk-reducing acts bypass `BLOCKS_PAPER`; entries remain blockable. No ADR was edited because this run permits only the CT-17 docs edit. |
| FC-02 | QMX-F003 | PROVEN | `f1bfb4b` | T23-PIN-03 + `qmb/tests/test_data_generate.py` (62 passed) | Outer replay clock/world is validated before nested config merge. Full Epic-23 QA remains red only at FC-10/FC-13 pins. |
| FC-03 | QMX-F004 | PROVEN | `06ef7a2` | Epic-18 L2/L3 money pins + exact read-back; affected tests (563 passed, 6 skipped) | CT-15 quote money is rebuilt through the CT-10 factory and persisted at the requested side's exact integer/scale. Epic-18 residual reds are FC-14 plus QMX-F107 (UNPROVEN/out of backlog). |
| FC-04 | QMX-F010 | PROVEN | `86945bd` | Partial-spawn real-disk pins (2 passed); targeted orchestrator tests (40 passed); Epic-15 QA (50 passed); QMB suite (1,039 passed, 10 skipped) | Batch spawn doors accept a ledger sink; every live sibling reaped after partial failure is killed and accounted exactly once as aborted with `reaped/abandoned`. |
| FC-05 | QMX-F005 | PROVEN | `bd7d4b3` | `qa/tests/epic_12/test_l3_example_bot.py` wiring-absence pin (3 passed); full qml suite + epic 11/12 QA (357 passed, 1 skipped) | OR-06 removal: `install_bot_definition_kind` + `register_bot_definition` deleted from qml (bot.py, both `__init__` exports) with a defined-unwired marker on `bot_definition_kind_contract`. All three examples stopped driving mints; test_examples stdout pins re-pointed; qml unit tests and epic-11 F1/F7 re-pointed to host-root `RegistrationRecord`/`Registrar` direct use (AD-25). ruff/pyright/format green on qml. |
| FC-06 | QMX-F006 | in-progress | — | `qa/tests/epic_03` sealed-window read-path quantifier | TO-BE-WRITTEN. |
| FC-07 | QMX-F007, QMX-F008, QMX-F009 | in-progress | — | `qa/tests/epic_06` L1-002 transport-raise tests | — |
| FC-08 | QMX-F012 | in-progress | — | `qa/tests/epic_22` T22-PIN-01 + log-return arm | — |
| FC-09 | QMX-F011 | todo | — | `qa/tests/epic_21` T21-PIN-01 | — |
| FC-10 | QMX-F013 | todo | — | `qa/tests/epic_23` T23-PIN-02 | Tighten exact factor and lineage first. |
| FC-11 | QMX-F014, QMX-F087 (R20 half) | todo | — | `qa/tests/epic_19` CT-32 embedded chart-series artifact | TO-BE-WRITTEN; re-point adjudicated assertions. |
| FC-12 | QMX-F015 | todo | — | `qa/tests/epic_17` end-to-end cost-port recorder | TO-BE-WRITTEN. |
| FC-13 | QMX-F016, QMX-F017 | todo | — | `qa/tests/epic_16` T-16.5-gap/T-16.5-a; `qa/tests/epic_23` T23-PIN-01 | OR-08/09 derived parity. |
| FC-14 | QMX-F018 | todo | — | ambient scanner + affected Epic-18 QA tests | — |
| FC-15 | QMX-F019 | todo | — | affected Epic QA fp1 implementation tests | — |
| FC-16 | QMX-F020 | todo | — | affected qmf-venue observation event-type QA test | OR-03 typed refusal. |
| FC-17 | QMX-F021, QMX-F035 (shared root) | todo | — | qml wheel/isolated-build and affected Epic-11 QA tests | OR-04: move impure host code. |
| FC-18 | QMX-F022 | todo | — | `qa/tests/epic_18` data-list CT-10 observation tests | — |
| FC-19 | QMX-F109 | todo | — | affected SecretRef construction QA tests | — |
| FC-20 | QMX-F023, QMX-F024 | todo | — | `qa/tests/epic_08`; `qa/tests/epic_22` T22-PIN-02; qmf-risk six-field gate | Strengthen all three registers to six-field checks. |
| FC-21 | QMX-F025 | todo | — | `qa/tests/epic_08` qmf-venue examples gate | — |
| FC-22 | QMX-F026 | todo | — | `qa/tests/epic_01` E1-C11 including CT-03 | TO-BE-WRITTEN/re-pointed. |
| FC-23 | QMX-F027 | todo | — | `qa/tests/epic_05` backup/restore adapter-refusal tests | OR-05 boundary categories. |
| FC-24 | QMX-F028 | todo | — | `qa/tests/epic_11` unknown top-level field pin | — |
| FC-25 | QMX-F029 | todo | — | `qa/tests/epic_17` composition-version bound-port-set test | Re-point constant-version assertion. |
| FC-26 | QMX-F031 | todo | — | `qa/tests/epic_19` composite-expression guard pin | — |
| FC-27 | QMX-F032 | todo | — | `qa/tests/epic_19` unrostered veto door/reason pins | TO-BE-WRITTEN/re-pointed. |
| FC-28 | QMX-F033 | todo | — | `qa/tests/epic_07` widened undeclared-import scanner | TO-BE-WRITTEN. |
| FC-29 | QMX-F034 | todo | — | `qa/tests/epic_18` ETA presence/monotonicity | TO-BE-WRITTEN. |
| FC-30 | QMX-F030 | todo | — | `qa/tests/epic_17` seed reaches slippage-model boundary | OR-11; stochastic draw remains UNPROVEN-by-design. |
| FC-31 | QMX-F039 | todo | — | Skylos dead-code ratchet | Delete only six corroborated symbols. |
| FC-32 | QMX-F040, QMX-F041, QMX-F042, QMX-F043 | todo | — | four qmf-core mutation pins + mutmut confirmation | OR-03 typed exhaustion refusal and boundary fix. |
| FC-33 | QMX-F036, QMX-F018, QMX-F100 | todo | — | CI/factory gate assertion + Story 1.7/1.8 scanner fixtures | OR-10c: only permitted `adws/` edit. |
| FC-34 | QMX-F038, QMX-F039 | todo | — | Skylos/Vulture/check CI and nightly mutmut configuration | OR-10a/b ratchets and permanent battery. |
| FC-35 | QMX-F037 | todo | — | lane-entry authority-path assertion | Toolchain quarantine applies; do not execute authority machinery. |

## Run notes

- Main checkout `C:\Users\Mubarak\Desktop\QMX` is untouched.
- Active worktree: `C:\Users\Mubarak\Desktop\QMX-worktrees\fix-round-1` on `fix/qa-round-1`.
- Repository BMad/Claude/factory skills and workflows are quarantined and must not be loaded or executed. The sole `adws/` allowance is the one-line FC-33 configuration edit specified by OR-10(c).
