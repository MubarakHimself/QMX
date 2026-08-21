# Review — Currency / Reality lens

**Spine:** ARCHITECTURE-SPINE.md (QMB, draft 2026-08-20)
**Lens:** every committed technology and factual claim must be web-current, not asserted from training memory.
**Reviewer gate date of my checks:** 2026-08-20 (independent web verification, PyPI + GitHub).

## Verdict

The two Stack rows marked "pin verified at reviewer gate" both hold under independent web
verification, at the exact versions the spine already writes; the uv-distribution assumption in
B-13 is not just correct but unusually well-caveated; and the other factual claims under this lens
(JSONL append atomicity, TPE/optuna sampler suitability, JSON-Schema-class validation,
process-per-run cross-platform) are accurate. No stale or web-contradicted claim found. This is a
clean pass — the findings below are low-severity forward-looking notes, not defects.

## What I verified on the web (primary sources)

### click — Stack row says `8.4.2 (BSD-3; pure-Python, verified CPython 3.14-compatible)`

- **Latest stable = 8.4.2, released 2026-06-24.** Confirmed current as of 2026-08-20 (no 8.5/9.0
  exists yet). Source: PyPI JSON (`pypi.org/pypi/click/json`) and PyPI release history.
- **License = BSD-3-Clause.** Confirmed (matches the row).
- **requires-python = `>=3.10`.** Confirmed.
- **CPython 3.14 compatibility:** click is pure-Python with no compiled extension, so it runs on
  3.14 by construction. The spine's explanation is exactly right and worth keeping: click
  **publishes no per-version `Programming Language :: Python :: 3.x` classifiers at all** (I
  confirmed the metadata carries only the generic `Programming Language :: Python` and
  `Typing :: Typed`), so any pyreadiness/wheel-readiness "✗" is a metadata artifact, not an
  incompatibility signal.
- **Exact pin to write in:** `click==8.4.2` — no change needed; the row is correct.

### optuna — Stack row says `4.9.0 (MIT; 3.14 classifier present; 5.0.0rc1 is pre-release, not pinned)`

- **Latest stable = 4.9.0, released 2026-06-01.** Confirmed via GitHub releases and PyPI history.
  4.8.0 (2026-03-16) is the prior stable; **5.0.0rc1 (2026-08-03) is a labelled pre-release**, not
  a stable — so pinning 4.9.0 and not 5.0.0rc1 is the correct, current call. (One early
  general web-search result of mine mis-reported 4.8.0 as latest and 4.9.0 as a `.dev`; that was
  wrong — the authoritative PyPI/GitHub release lists both show 4.9.0 as a normal stable release.
  The spine's pin, not that search snippet, is right.)
- **License = MIT.** Confirmed on the 4.9.0 release metadata.
- **CPython 3.14 classifier = present on 4.9.0.** Confirmed directly on `optuna/4.9.0/json`: the
  classifier list runs 3.9 → 3.14, and requires-python is `>=3.9`.
- **Dependency-chain 3.14 reality (the part that actually gates install on CPython 3.14):** optuna
  4.9.0 core install_requires = alembic, colorlog, **numpy**, packaging, sqlalchemy, tqdm, PyYAML.
  The only binary-wheel dependency is numpy, and numpy ships cp314 wheels (numpy 2.5.x, 2026); scipy
  (1.18.0, 2026-06-19) also ships cp314 wheels for the optional integrations. So the whole chain is
  3.14-ready, not just optuna's own classifier — the compatibility claim is real, not asserted.
- **Exact pin to write in:** `optuna==4.9.0` — no change needed; the row is correct.

### B-13 — uv tool distribution of a mixed library+CLI package

- The spine's assumption is **correct and precisely stated**, which is the failure mode I was
  looking for and did not find. `uv tool install qmb` / `uvx qmb` installs into an isolated,
  ephemeral environment and exposes only the package's entry-point executables — it does **not**
  make the package importable into the user's own project environment. B-13 already says exactly
  this: the primary channel MUST be a normal pinned lockfile dependency (`uv add qmb`) "because the
  Python API door must be importable," and it explicitly demotes `uvx`/`uv tool install` to an
  optional CLI-only convenience that "does NOT provide the importable library and is never the
  sandbox provisioning channel." That is the correct mental model for uv tool distribution. No
  finding.

### Other factual claims under this lens

- **JSONL append atomicity (B-4):** "single-file append is not atomic on Windows and only
  PIPE_BUF-atomic on Linux" — accurate. The WriterId-scoped-fragment design (one file per writer,
  merge only on read) is the correct way around it. No finding.
- **Process-per-run on Windows 11 + Ubuntu with stdlib (B-5):** sound and cross-platform; separate
  OS processes with isolated output dirs sidesteps the fork-vs-spawn difference entirely. No
  finding.
- **TPE/optuna sampler suitability (B-8):** optuna's default sampler in the 4.x line is
  `TPESampler`, which is genuinely adaptive — the "TPE-class" description is accurate, and B-8
  correctly does not rely on the library default (it binds sampler identity + seed + generator
  provenance into every label). No finding. (See low note 1 on 5.0's default change.)
- **JSON-Schema-class validation / JSON config (Consistency Conventions):** standard, current, no
  currency concern.

## Findings (low, forward-looking — no critical/high)

1. **(low) optuna 5.0 is imminent and changes the default sampler + has breaking changes.**
   5.0.0rc1 landed 2026-08-03 ("massive default sampler algorithm enhancement," breaking changes).
   Pinning 4.9.0 now is correct. The reason this is only informational and not a defect: B-8 already
   requires the sampler identity to be pinned explicitly and stamped into every result label, so a
   future 4.9→5.0 bump cannot silently change search behaviour behind stored evidence. Note for
   whoever eventually bumps the pin: treat the optuna major bump as a metric/contract-versioning
   event (the default sampler algorithm changes), not a transparent dependency update.

2. **(low) Fix the pins to exact `==`, and keep them lockfile-tracked, not floating.** The Stack
   table states `8.4.2` and `4.9.0` as bare numbers. For a build-substrate whose whole premise is
   reproducible, fingerprinted runs (B-3/B-13), the written pins should be exact-equality
   (`click==8.4.2`, `optuna==4.9.0`) and carried in the uv lockfile, so an agent provisioning a
   sandbox six months from now does not silently pull optuna 5.x. This is consistent with what the
   spine already intends under AD-2/AD-5 lockstep and B-13's "pinned, lockfile-tracked" language —
   just make the Stack rows say `==`.

3. **(low, affirmation not defect) The spine's self-dated web-verification matches independent
   re-verification.** Both "pin verified at reviewer gate" annotations (dated 2026-08-20) reproduce
   exactly against PyPI/GitHub on the same date. The currency claims in this spine are grounded, not
   asserted from training memory — which is the specific thing this lens exists to catch, and it is
   clean.

## Review path

C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/reviews/review-currency.md
