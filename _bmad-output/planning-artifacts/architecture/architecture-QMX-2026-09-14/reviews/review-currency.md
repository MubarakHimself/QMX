# Review — Currency / Reality lens

**Spine:** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md` (draft 2026-09-14)
**Companions read:** sitting `.memlog.md`; `docs/architecture/stack.md` (ratified, verified 2026-09-11)
**Lens:** every committed technology and factual claim must be web-current or brownfield-checked, not asserted from training memory.
**Reviewer gate date of my checks:** 2026-09-14 (independent web verification: python.org, PEP 790, PyPI JSON, GitHub releases; brownfield: `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`).

## Verdict

**CONDITIONAL PASS — one Stack-row correction before this sitting is a clean currency record.**

The sitting *did* web-research the two versions it restamps (CPython 3.14.7, Optuna 5.0.0) and *did* reality-check brownfield on `integration@1b451a8`. Named donor products still exist and still fit the refuse/borrow split. No training-data invention of a library, a version, or a vanished vendor.

The leak is the Stack table itself. It reports Optuna 5.0.0 as current upstream and then hides the load-bearing facts: the lockfile pin is still `optuna==4.9.0`, and v5 is the first default-sampler change since Optuna 1.5 — exactly the contract-versioning event DEC-0168 already named. The table currently justifies non-adoption with “floats never enter identity,” which is the wrong law. Fix the row; do not bump the pin.

---

## What I verified on the web (primary sources)

### CPython — Stack row says `3.14 (3.14.7 current stable 2026-08-05; 3.15 not adopted)`

- **Latest stable = 3.14.7, released 2026-08-05.** Confirmed: python.org downloads (“Latest: Python 3.14.7”), python.org/downloads/latest, Python Insider 2026-08-05, PEP 745 (3.14.7 actual; 3.14.8 expected 2026-10-06). Docs “What’s New” last-updated 2026-09-13 still lists 3.14.7 as the 3.14 tip. No 3.14.8 exists today.
- **3.15 is not stable.** PEP 790: 3.15.0rc2 actual 2026-09-01; 3.15.0 final expected 2026-10-01. python.org news 2026-09-01: “Python 3.15.0 candidate 2 is here!” CPython GitHub latest tag `v3.15.0rc2`.
- **Fit:** inherited AD-1 / DEC-0099 pin of the 3.14 line still holds. Brownfield: `integration` members declare `requires-python = ">=3.14,<3.15"`; workspace `.python-version` is `3.14`; `uv.lock` is `requires-python = "==3.14.*"`.
- **Reality check, this machine:** `python --version` → **3.14.6** (not 3.14.7). Same 3.14 line; sqlite3 reports **3.50.4**, matching the QMA 2026-08-28 currency finding. This sitting does not re-pin SQLite.
- **Memlog is more precise than the spine.** Memlog: “3.15.0rc2 exists, not adopted.” Spine Stack row drops the rc2 / 2026-10-01 dating. See L-1.

### Optuna — Stack says `current upstream 5.0.0 as of 2026-09-07; the qmb lockfile owns the pin`

- **Latest stable = 5.0.0, released 2026-09-07.** Confirmed independently today via PyPI JSON (`pypi.org/pypi/optuna/json`): `info.version = 5.0.0`, `release_url = …/optuna/5.0.0/`, classifiers include `Programming Language :: Python :: 3.14`, `requires_python = ">=3.9"`, MIT. GitHub `optuna/optuna` latest release **v5.0.0**. Release history: 5.0.0 (2026-09-07) → 5.0.0rc1 (2026-08-03) → 4.9.0 (2026-06-01). No 5.0.1.
- **3.14 fit:** 5.0.0 is a pure-Python wheel (`py3-none-any`) with an explicit 3.14 classifier. It still fits as a TPE-class sampler *library*. It does **not** fit as a silent drop-in for QMB’s `TPESampler(seed=…)` call.
- **v5 default-sampler change (the load-bearing currency fact):** GitHub v5.0.0 notes — first major default-sampler update since v1.5. Single-objective `TPESampler` now enables **multivariate TPE** and **constant liar** by default; multi-objective default becomes `TPESampler` (replaces NSGA-II). Listed under Breaking Changes (`#6746`, `#6738`, `#6766`).
- **Brownfield pin is 4.9.0, not 5.0.0.** On `integration@1b451a8`:
  - `qmb/pyproject.toml`: `optuna==4.9.0`
  - `uv.lock`: package `optuna` sdist/wheel **4.9.0** (upload-time 2026-06-01), specifier `==4.9.0`
  - `DEPENDENCIES.md` and `docs/registry/variables.yaml` `qmb_sampler_pin`: `optuna==4.9.0`
  - `qmb/src/qmb/optimize/sampler.py`: `TPESampler(seed=gen_seed)` — library defaults, `n_jobs` not used; `SAMPLER_CONSULTS_OPTUNA_STORE = False`
- **Not bumping is the correct call** (DEC-0168: optuna major bump is a contract-versioning event). The Stack row currently gives the wrong reason. See M-1.

### Inherited pins this sitting restates but does not bump

| Pin | Spine posture | Web / brownfield 2026-09-14 |
| --- | --- | --- |
| uv workspace + lockfile | inherited (`stack.md`) | Current uv **0.12.13** (2026-09-10). Ratified stack still names 0.12.5 (QMF) / 0.12.7 (QMA). Same 0.12.x line; not a new pin. Informational only. |
| click (QMB CLI) | not restated | Brownfield `click==8.4.2`. **click 8.5.0** is current on PyPI (2026-08-26), a feature release that “may introduce potentially breaking changes.” Not adopted. See L-2. |
| DuckDB | inherited store | Brownfield `duckdb==1.5.5`. PyPI latest **stable still 1.5.5** (2026-07-22); 1.6.0 and 2.0.0 are `.dev` pre-releases. Inherited pin is still current. |
| Parquet / SQLite / JSONL | inherited store engines | Still exist; still fit behind QMF contracts. No new version claimed. |
| MCP door | “MCP later”; deferred after CLI v1 | MCP spec **2026-07-28 is still the latest** (modelcontextprotocol.io, “Version 2026-07-28 (latest)” as of 2026-09-13). Brownfield `MCP_SHIPPED = False`. Fits. |
| Jupyter | explicitly not pinned (AD-11) | Correct. No vendor pin to go stale. |

### Named donor technologies — still exist, still fit the refuse/borrow split

Fetched / confirmed 2026-09-14:

| Named in spine | Exists? | Fit of the sitting’s use |
| --- | --- | --- |
| StrategyQuant (RandomCondition templates, Custom Projects) | Yes — strategyquant.com docs (how-it-works, templates, Custom Projects). Donor file fetched this sitting. | Shapes only. Not an engine. Matches AD-4 / AD-9. |
| QuantAnalyzer What-if (hours/days/max-trades snippets) | Yes — strategyquant.com/quantanalyzer/what-if-scenarios/. Snippet-extensible trade-list filter. | Maps to **projection** (AD-5). Vendor still does not claim path-dependent Book replay. |
| QuantDataManager timezone clones that auto-update | Yes — strategyquant.com/quantdatamanager (“cloned data will be automatically updated when you update the source data”). Build 125, Dec 2025. | The refuse in AD-13 is still the live vendor behaviour. |
| QuantConnect paper-brokerage | Yes — live docs + LEAN `Brokerages/Paper/` (commit 2026-08-24). Paper = live-data fictional-capital simulation, not a research replay. | AD-7 refusal still accurate. LEAN itself is actively released (build 18086, 2026-09-12). |
| AlgoCloud / F17 | Yes — StrategyQuant-family cloud product for US stocks/ETFs; still a separate bill from SQX. | Deferred as lower-confidence donor; inspectability already QML+CT-33. Fits. |
| RoboQuant.dev RQ Engine | Yes — roboquant.dev/next: “Closed beta — Jul/Aug 2026”, waitlist, v2 rebuild. Distinct from Kotlin `neurallayer/roboquant` and PyPI `roboquant`. | Spine “Closed beta; shapes only; live-survive-tab-close is node territory” still holds. Sitting donor file is stronger than `inputs/orchestrator-verified.md` (which recorded a session-check-only homepage fetch). |
| TPE / Optuna sampler | Yes — still the default single-objective family. | QMB already wraps it. AD-4 correctly refuses selling TPE as *generation*. |

### Brownfield objects the spine names as connect-work

All present on `integration@1b451a8` (commit object exists; contained in `integration` / `origin/integration`):

- `qma.daemon.backtest.RecordingQmbDoorTransport` — default transport; records, does not spawn `qmb` (AD-8).
- `qmb.MCP_SHIPPED is False`.
- `qmb` CLI + Python API, TPE optimize, data commands, robustness library.
- Planning checkout SHA `430fb7d` exists (current HEAD of this worktree).

Class/test existence ≠ end-to-end proof — the spine already says this. Currency lens does not treat that as a defect.

---

## Findings

### M-1 — Optuna Stack row hides the lockfile pin and cites the wrong law *(medium; fix before ratification)*

**Where:** Stack intro sentence and table row “Optuna (QMB sampler adapter only) | lockfile-owned; floats never enter identity”. Memlog version entry is better than the spine.

**What is wrong.**

1. The sitting verified that **5.0.0 is current stable** and correctly **did not re-pin**. That discipline is good.
2. The table never writes the brownfield pin **`optuna==4.9.0`**. “Lockfile-owned” is a pointer, not a version. CONNECT’s protobuf row named both `==7.36.0` and the newer `7.36.1` not adopted. This row should do the same.
3. “Floats never enter identity” is AD-7 / AD-22 / B-8 money-path law. It is **not** why the sampler stays on 4.9.0. The governing rule is **DEC-0168**: an Optuna **major** bump is a contract-versioning event because sampler identity is stamped into every trial label.
4. That rule is no longer hypothetical. v5.0.0 (2026-09-07) changes `TPESampler` defaults (multivariate + constant liar). QMB constructs `TPESampler(seed=gen_seed)` and therefore **inherits library defaults**. A silent 4.9 → 5.0 lockfile bump would change search behaviour behind stored evidence. Staying on 4.9.0 is the correct non-adoption *because of that*, not because floats are banned.

**Fix (editor):** replace the Stack sentence/row with the two facts and the governing invariant, e.g.

> Optuna remains an internal QMB sampler adapter. Current upstream **5.0.0** (PyPI 2026-09-07; 3.14 classifier; MIT). Brownfield pin stays **`optuna==4.9.0`** (`qmb/pyproject.toml`, `uv.lock`, `registry:qmb_sampler_pin`). This sitting does not bump: v5 is a default-sampler change (multivariate TPE + constant liar) and is a DEC-0168 contract-versioning event. Float conversion remains the named AD-7/AD-22 boundary and is a separate law.

Also add `docs/architecture/stack.md` + `variables.yaml` `qmb_sampler_pin` notes (“5.0.0rc1 is a pre-release”) to the existing documentation-factory reconcile deferred row. Those notes are now false.

### L-1 — CPython Stack row dropped the memlog’s 3.15 dating *(low)*

Memlog: “3.14.7 2026-08-05; 3.15.0rc2 exists, not adopted.” Spine: “3.15 not adopted.” Independent check: 3.15.0rc2 is real (2026-09-01); final expected 2026-10-01 (~16 days). “Not adopted” is correct; undated, a later reader may think 3.15 does not exist. Restore the memlog clause.

### L-2 — Inherited `click==8.4.2`; 8.5.0 exists and is not adopted *(low / CONNECT-style note)*

PyPI current click is **8.5.0** (2026-08-26), a feature release. Brownfield remains `click==8.4.2` (DEC-0168 `qmb_cli_pin`). This sitting adds no CLI framework and should not bump. Mirror the protobuf posture: record 8.5.0 exists, not adopted, revisit at a qmb CLI sitting — not this one.

### L-3 — Ratified `stack.md` Optuna note is stale relative to this sitting *(low, docs debt)*

`docs/architecture/stack.md` (verified 2026-09-11) and `qmb_sampler_pin` notes still say “5.0.0rc1 is a pre-release, not pinned.” As of 2026-09-07 that sentence is false. The spine’s “Inherited pins stand” is the right *pin* posture; it is the wrong *prose* posture for a note that names a pre-release which has since graduated. Fold into documentation-factory reconcile (already deferred for `defined-unwired` stamps).

---

## What is clean (no finding)

- CPython 3.14.7 as current stable: independently reproduced today; 3.15 not adopted is the right call.
- Optuna 5.0.0 as current upstream, dated 2026-09-07: independently reproduced via PyPI JSON, not asserted.
- No new framework minted. Parquet / DuckDB 1.5.5 / SQLite / JSONL still exist; DuckDB 1.5.5 is still the latest stable.
- MCP still exists; latest spec is still 2026-07-28; `MCP_SHIPPED=False` matches code.
- Jupyter left unpinned (AD-11): correct currency posture.
- Donor names are live products; the refuse/borrow split matches current vendor docs (QA What-if = trade-list filter; QC paper = live brokerage simulation; QDM clones auto-update; RoboQuant.dev v2 still closed-beta / waitlist).
- `integration@1b451a8` and `RecordingQmbDoorTransport` are real.

---

## Review path

C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/reviews/review-currency.md
