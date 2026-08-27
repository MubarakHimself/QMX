# Epic 13 — QMB substrate — Verification RESULTS (audit tier T1)

Executed: `uv run --with hypothesis pytest qa/tests/epic_13 -q --tb=short` from the
worktree root `C:/Users/Mubarak/Desktop/QMX-worktrees/qa-audit`.

**Outcome: 43 tests / 43 PASSED / 0 FAILED / 0 ERRORED.** (The 41 planned §4 checks;
T13-401 is implemented as three pytest functions — `401`, `401b`, `401c` — over the
same R-004 identity law.) **Zero findings** — the QMB Epic-13 substrate satisfies
every requirement-derived assertion. `findings.csv` therefore carries only its header.

Two test-code defects surfaced on the first run and were corrected without weakening
any assertion (permitted: fixtures/test-logic only, never source, never assertions):
`test_t13_007` initially flagged the conventional `__all__` export manifest as
"module-global mutable state" (over-broad AST scan → excluded dunder manifests); and
`test_t13_105` asserted `dict` where the compiler correctly freezes a nested namespace
to `MappingProxyType` (→ asserted `Mapping`). Both real assertions stand and pass.

Test artifacts:
- Fixtures: `qa/tests/epic_13/_fixtures.py` (registry/as-of/fragment universe, built
  through the same public construction API the shipped usage examples use).
- L0 `qa/tests/epic_13/test_l0_static_build.py` · L1 `test_l1_unit.py` ·
  L2 `test_l2_integration.py` · L3 `test_l3_contract.py` · L4 `test_l4_property.py`.

Independence: §4 of the PLAN was authored with zero `qmb/` source read; source was
opened only afterwards, to bind fixtures to the real construction API and confirm the
public seams the assertions call. Every assertion states what the REQUIREMENT demands.

---

## Per-test results

| Test id | Level | Requirement ids | Status | Assertion (one line) |
|---|---|---|---|---|
| T13-001 | L0 | 13.1 AC1 / B-13, DEC-0167/0168 | PASS | ONE wheel, `module-name qmb`, single `qmb` console script, `import qmb` works. |
| T13-002 | L0 | 13.1 AC1 / DEC-0168 | PASS | `click==8.4.2` and `optuna==4.9.0` pinned at exact versions. |
| T13-003 | L0 | 13.1 AC1b / AR-06, B-13 | PASS | qmf deps == the six backends; no `qmf-venue`; `BACKEND_PACKAGES` agrees. |
| T13-004 | L0 | 13.1 AC2 / B-1 | PASS | Full structural-seed module tree present; `doors/mcp` scaffolded in the seed. |
| T13-005 | L0 | 13.1 AC3 / B-15 | PASS | No qmb module/symbol name uses engine/kernel/exam/plugin; no "snapshot" for state. |
| T13-006 | L0 | 13.1 AC5 / AR-11 | PASS | Tier-1 static gate green over qmb: `ruff` clean AND `pyright` (strict) clean. |
| T13-007 | L0 | 13.1 AC5 / AR-11, AR-04, NFR-02 | PASS | No module-global mutable state (dunder manifests excluded); no compiled extension. |
| T13-101 | L1 | 13.1 AC2 / SC-08 | PASS | MCP door not shipped in V1: `serve()`/`main()` refuse `unsupported capability`. |
| T13-102 | L1 | 13.2 AC2 / B-13, B-15 | PASS | Human alias resolves by `fp1`; the handle cites the fingerprint, never `name@version`. |
| T13-103 | L1 | 13.2 AC3 / FM-7 | PASS | Superseded ref → AD-11 `stale evidence` RETURNED, carrying `qmb_stale_evidence_severity`. |
| T13-104 | L1 | 13.3 AC5 / B-3 | PASS | `stress-spread` preset materializes as an ordinary derived, lineaged config fragment. |
| T13-105 | L1 | 13.4 AC1 / B-3 | PASS | Precedence pinned flags > run spec > BMS > Book > defaults; higher layer overrides lower. |
| T13-106 | L1 | 13.4 AC1 / AR-52 | PASS | Exactly ONE resolved config; frozen artifact + read-only keys; re-reads its schema. |
| T13-107 | L1 | 13.4 AC2 / FM-1 [R-004] | PASS | Unsanctioned Book/BMS collision → CT-04 `invalid input`; value never silently overwritten. |
| T13-108 | L1 | 13.4 AC2 / DEC-0143 | PASS | Sanctioned overlap resolves BMS-over-Book; V1 sanctioned set is empty. |
| T13-109 | L1 | 13.4 AC3 / B-3, B-13 | PASS | Artifact cites Book/BMS/bot by `fp1` even from an alias; no `@` leaks; `name@version` refused. |
| T13-110 | L1 | 13.4 AC5 / FM-3, SC-06 | PASS | Replay clock + synthetic-tainted → `invalid input`; a caller may not declare `world`. |
| T13-111 | L1 | 13.5 AC1 / B-3 | PASS | `starting_capital` mandatory (absent → refusal); run-spec/Book-fragment default honored. |
| T13-112 | L1 | 13.5 AC2 / FM-12 | PASS | Seed-override flag stamps `seed_overridden` and forces fold `unrated`; distinct binding id. |
| T13-201 | L2 | 13.2 AC1 / AR-55, B-15 | PASS | ONE library port is the sole path; autocomplete resolves through it; doors hold no cache. |
| T13-202 | L2 | 13.2 AC5 / B-15 | PASS | Immutable as-of set from passive storage (`passive-storage`); absent set → `unavailable`, no live fetch. |
| T13-203 | L2 | 13.2 AC4 / SC-11 | PASS | `admit_batch` freezes one as-of; then `fp1` resolves, alias & `name@latest` refused. |
| T13-204 | L2 | 13.4 AC4 / DEC-0160 | PASS | fp1 == run-id root == ledger key; artifact under run-id-named dir; API door computes the SAME fp1. |
| T13-205 | L2 | 13.5 AC3 / FR-036 | PASS | Exactly ONE CT-28 `world=replay` binding; same inputs → the same single binding id. |
| T13-206 | L2 | 13.5 AC1 / B-3 | PASS | `starting_capital` seeds the binding virtual ledger (seed == equity == capital). |
| T13-207 | L2 | 13.5 AC4 / B-6, AR-56 | **PASS (PARTIAL)** | Seam only: CT-23/CT-29 bound from resolved config (not ambient); seams refuse without the run's replay binding. Runtime open/exit = Epic 14 (PLAN §7.2). |
| T13-301 | L3 | 13.3 AC1 / AR-52, B-3 | PASS | Book fragment: derived, fingerprinted, CT-07 `occurrence-of` lineage to CT-22; not a kind; not free-hand. |
| T13-302 | L3 | 13.3 AC2 / AR-52, B-3 | PASS | BMS fragment: derived, fingerprinted, CT-07 lineage to CT-27; BMS materializer won't read a Book record. |
| T13-303 | L3 | 13.3 AC4 / CT-05 | PASS | AD-5 int format version; format-1 readable under a newer reader; unknown/newer version → `unsupported`. |
| T13-304 | L3 | 13.4 AC4 / AR-52 | PASS | Resolved config stamps AD-5 + declares AD-10 identity/display (disjoint); re-reads; newer format refused. |
| T13-305 | L3 | 13.5 AC3 / CT-28 | PASS | Minted binding is CT-28 `world=replay`, distinct identity from a live binding, incomparable (`policy rejection`). |
| T13-306 | L3 | 13.5 AC3 / CT-28 [R-004] | PASS | Replay binding fingerprints apart from live (world in identity); incomparability check never silently accepts. |
| T13-307 | L3 | 13.1 AC4 / CT-05 | PASS | QMB SemVer display-only: absent from every identity payload and from the config's canonical bytes. |
| T13-308 | L3 | cross-cutting / CT-04 | PASS | 8 Epic-13 refusals: category ∈ the seven, context present & non-null, retryability present — all RETURNED. |
| T13-309 | L3 | 13.5 AC4 / AR-56 | **PASS (PARTIAL)** | Seam only: AD-40 `require_full_loss_before_open(None)` RETURNS a refusal. Runtime open = Epic 14 (PLAN §7.2). |
| T13-401 | L4 | 13.4 AC4 [R-004] | PASS | Property: distinct horizon (identity field) ⇒ distinct config `fp1` (hypothesis, derandomized). |
| T13-401b | L4 | 13.4 AC4 [R-004] | PASS | Property: distinct starting_capital seed ⇒ distinct `fp1`. |
| T13-401c | L4 | 13.4 AC4 [R-004] | PASS | Provenance-derived world change and cited-bot change each move the run identity. |
| T13-402 | L4 | 13.4 AC1 [R-004 conv / NFR-03] | PASS | Property: identical inputs ⇒ byte-identical artifact / equal `fp1`, incl. across a fresh universe. |
| T13-403 | L4 | 13.4 AC1/AC3 [R-008] | PASS | Alias-vs-`fp1`, key ordering, CT-01 canonical rational forms ⇒ ONE `fp1` and one accept verdict. |
| T13-404 | L4 | 13.4 AC4 [AD-10] | PASS | Display-only change (bot alias) moves no `fp1`; an identity-field change (horizon) does. |
| T13-405 | L4 | 13.3 AC3 / DEC-0143 | PASS | Book ∩ BMS namespaces = ∅ over the full surface; each key one owner; a mixed-namespace fragment refused. |
| T13-406 | L4 | NFR-03 / DEC-0163 [P0-13 config-side] | PASS | Stored resolved config re-derives the SAME run-id root; a tampered/inconsistent identity differs or refuses. |

---

## Deferred / partial / out-of-Epic-13-reach (recorded, not counted pass or fail)

- **P0-13 CT-32 *result*-fingerprint reproduction — DEFERRED to Epic 14 (Story 14.7).**
  Only the config-side run-id-root reproduction is testable at Epic 13 (T13-406 PASS).
  The result-side needs the event-slice run loop + CT-32 artifact, absent until Epic 14.
- **Story 13.5 AC4 runtime — PARTIAL (T13-207, T13-309).** Sizing / R-freeze / exit
  execution and AD-40 full-loss-price-before-open fire inside the position-opening loop
  (Epic 14). Only the CT-23/CT-29 seam wiring and the config/binding-level precondition
  are testable now; both seams behave as required.
- **Full door parity (CLI/API/MCP) — Epic 16.** Epic 13 asserts single-source
  fingerprint agreement only (T13-204 API-vs-library). The MCP door is
  scaffolded-not-shipped (SC-08), so its parity is untestable in V1 (T13-101 asserts
  presence-without-shipment).
- **GAP-0048-gated content** (`world=simulated` unlock, fidelity taxonomy, forex
  calibration numbers) — only the refusal seam is testable now (T13-110).

## Observations (no requirement-level assertion fails; recorded for downstream attention)

- **Book-fragment `starting_capital` default is honored by the resolver but not
  populated by the materializer.** `resolve_starting_capital` reads
  `book_fragment.keys["sizing"]["starting_capital"]` (T13-111 confirms it honors such a
  default), yet the CT-22 section→namespace projection in `config/fragments.py`
  (`BOOK_SECTION_NAMESPACE`) never emits a flat `sizing.starting_capital` key from a real
  Book definition. Story 13.5 AC1 says the Book fragment *may* default it (permissive), so
  no assertion fails; but through the shipped materialization path a real Book cannot
  actually set that default. Flag for Epic-14 wiring / a Book-authoring seam. Severity: low.
- **Plan-integrity caveat (PLAN §7.6).** The two authorities the task named —
  `_bmad-output/test-artifacts/test-design-qa.md` and
  `_bmad-output/test-artifacts/test-design/QMX-handoff.md` — do **not** exist in this
  worktree (`_bmad-output/test-artifacts/` is absent entirely). The L0–L6 scheme,
  the 8-section template, and the risk gates R-004/R-008/P0-13 were reconstructed from the
  ratified quality tiers and the task brief. This is not a failing test (no test asserts
  those files), so it is recorded here rather than as a `findings.csv` row.

## Exit-criteria ledger (PLAN §8)

- Every §2 AC maps to ≥1 executed test with a recorded PASS. ✔
- L0 gate green (ruff + pyright-strict; manifest six-backends/no-venue; vocabulary;
  no module-global mutable state). ✔
- R-004 satisfied: T13-401/401b/401c, T13-402, T13-107, T13-306, T13-404 all PASS. ✔
- R-008 satisfied: T13-403 PASS (plus T13-204 single-source, T13-109 alias). ✔
- P0-13 config-side satisfied: T13-406 PASS. ✔
- Config-compiler hot-spot cleared: T13-105/107/108/405 + identity properties PASS. ✔
- Contract conformance T13-301..308 PASS. ✔
- Deferred items explicitly recorded, each with its owning epic. ✔
