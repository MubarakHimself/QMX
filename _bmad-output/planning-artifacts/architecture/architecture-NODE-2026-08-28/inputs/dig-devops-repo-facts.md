# DevOps ground truth of the repo as built — trading-node architecture sitting

Discovery dossier. Source of truth: the integration worktree at
`C:/Users/Mubarak/Desktop/QMX-worktrees/node-inventory`, detached at
`integration@ef9bb253fc87ec3a66d5c6a78f3cb95bb45c760c` (read-only). Every
citation below is `path:line`, repo-relative to that worktree root (which mirrors
integration@ef9bb25). Nothing was modified; no git write command was run.

Scope note on vocabulary: the corpus's own words "engine", "daemon", "kernel",
"plugins" are quoted only where a cited source uses them; they are not used in
this dossier's own prose.

---

## 0. One-paragraph bottom line

The repo as built is a **pure, deterministic, synchronous library workspace** with
**no runtime**, **no deployment substrate**, and **no observability implementation**.
CI is **Linux-only** (`ubuntu-latest`) yet the ratified tier-1 OS is **Windows**
(pyright pins `pythonPlatform = "Windows"`); Ubuntu is a *ratified-but-untested*
tier-1 target awaiting a remote. There is exactly **one console script in the whole
workspace** (`qmb`, a click CLI for backtests). The shipped libraries **ban**
`asyncio`/`threading`/`sched`/`multiprocessing`, and `qmf-data` **refuses by
contract** to own any "scheduler, daemon, process supervisor, or retry loop." No
Dockerfile, compose file, systemd unit, terraform, ansible, cloud-init, or
install.sh exists for the trading product. Secrets are handled as opaque
`SecretRef`s through a core `SecretStore` **Protocol port** whose only concrete
implementation is an in-memory reference store; the real `systemd-creds`-class
store is documented-but-unbuilt and explicitly deferred to *this* node/ops sitting.
Logging-vs-journals is separated **in the contract** (DEC-0112) but **no operator
log framework, metrics exporter, health endpoint, or clock-sync monitoring exists
in code** — all deferred to this sitting. The long-running Book/BMS + venue-session
runtime the node needs **does not exist yet**; the foundation was deliberately built
to hand that job to the node.

---

## 1. CI: OS matrix, runners, Python, gates, schedule

### 1.1 The two workflows (the only ones)

`.github/` contains exactly two workflows plus GitHub's own secret-scan config:
- `.github/workflows/skylos.yml`
- `.github/workflows/battery.yml`
- `.github/secret_scanning.yml`
No `dependabot`, no other CI. (`find .github -type f`.)

### 1.2 Exact CI OS matrix TODAY — Linux only

**Every CI job runs on `ubuntu-latest`.** There is NO `windows-latest` anywhere in
CI. The task's hypothesis "is tier-1 CI pinned to windows-latest only?" is **FALSE**.

- `.github/workflows/skylos.yml:36` — `skylos` job: `runs-on: ubuntu-latest`.
- `.github/workflows/battery.yml:35` — `check` job: `runs-on: ubuntu-latest`.
- `.github/workflows/battery.yml:57` — `vulture` job: `runs-on: ubuntu-latest`.
- `.github/workflows/battery.yml:85` — `mutation` job: `runs-on: ubuntu-latest`.

So **answer (b): yes, the entire CI runs on Linux; nothing in CI runs on Windows.**

### 1.3 The Windows/Linux tension baked into the type gate

Although CI is Linux, the **ratified tier-1 OS is Windows**, and the type-checker is
pinned to render the Windows platform view even on the Linux runner:
- `pyproject.toml:307-312` — `[tool.pyright] pythonPlatform = "Windows"`, with the
  comment: *"Pin the analysis platform to the ratified tier-1 OS (AR-04/AR-23:
  Windows). The orchestrator's process-watch seam uses the Windows process APIs
  (ctypes.WinDLL); pinning makes the battery CI job on a Linux runner render the same
  byte-identical verdict the tier-1 machine renders (AR-11), instead of failing on
  platform-conditional stdlib surface."*
- `pyproject.toml:331` — `pythonVersion = "3.14"`.

**Ubuntu is a second, ratified-but-untested tier-1 OS.** The release tier explicitly
defers the Ubuntu clean-install smoke until a remote exists:
- `pyproject.toml:503-506` — `[tool.poe.tasks.check-release]`: *"Tier 3 — ship. Tier 2
  today; the clean-install smoke on both tier-1 OSes is added once a remote exists
  (AR-23: Ubuntu tier-1 stays untested until then)."*

Node relevance: the node runs on a **Linux VPS**, i.e. on the tier-1 OS that is
ratified but currently unexercised in CI, while the strict type gate validates a
Windows view. This is a first-order gap for the node sitting.

### 1.4 Python versions

- Project target: **CPython 3.14**, pinned in `.python-version:1` (`3.14`) and in
  every member's `requires-python = ">=3.14,<3.15"` (e.g.
  `packages/qmf-core/pyproject.toml:6`, `qmb/pyproject.toml:5`, `qml/pyproject.toml:5`).
- `uv.lock:3` — `requires-python = "==3.14.*"`; `uv.lock:1-2` — `version = 1`,
  `revision = 3`.
- The SSSF factory-stamp floor stays `>=3.10` at the workspace root
  (`pyproject.toml:34`, `requires-python = ">=3.10"`) — deliberately, to keep ruff's
  inferred target at py310 for `adws/` (`pyproject.toml:29-33`). `[tool.mypy]
  python_version = "3.10"` (`pyproject.toml:228`) — mypy scopes to `adws` only.
- Skylos CI runner uses **Python 3.12** — *only* to run Skylos itself, not the target:
  `.github/workflows/skylos.yml:56` (`python-version: '3.12'`), with the comment at
  lines 52-55 explaining 3.12 is chosen because every Skylos tree-sitter dependency
  ships a wheel for it.
- The battery CI jobs use `python-version-file: .python-version` (i.e. 3.14):
  `.github/workflows/battery.yml:46, 67, 95`.

### 1.5 The Skylos gate (skylos.yml)

- Trigger: `on.push.branches: [integration]` + tags `factory-candidate/**`, and
  `pull_request.branches: [main]` (`.github/workflows/skylos.yml:20-26`).
- `permissions: contents: read` at workflow and job level (`:31-32`, `:41-42`).
  Timeout 20 min (`:40`).
- Pinned tool: `skylos==4.33.2` (`:60`). Runs the CLI directly, **not** the
  `duriantaco/skylos` composite action, to avoid the action's unconditional upload
  (`:16-19`).
- **Free tier only**, no cloud: `--no-upload` passed explicitly, no `id-token`
  permission, no `sync pull`/`defend`/`--verify` (`:10-14`).
- Scope: **scans the repo ROOT and subtracts by NAME** via `[tool.skylos] exclude` in
  pyproject; not an include-list, so a new top-level folder is in scope the moment it
  lands (`:3-8`, and `pyproject.toml:333-352`).
- Scan command: `python -m skylos.cli . -a --no-upload --json` (`:148`). `-a` = full
  local audit: dead code + security/dangerous-flow + secrets + quality + dependency
  CVEs + AI-defect checks (`:144-147`). Fail-closed: any exit code other than 0/1 is
  treated as a broken run, not clean (`:154-157`).
- Gate: `python -m skylos.cli cicd gate --input skylos-report.json --summary`
  (`:170`); thresholds come from `[tool.skylos.gate]` in pyproject; incomplete
  analysis exits 2 rather than passing (`:166-170`).
- A derived allow-list (`SKYLOS_PRIVATE_DEPS_ALLOW`) teaches the hallucinated-dep rule
  (SKY-D222) the workspace's own package names, computed from the layout
  (`:113-138`); floor `{qmf, qmb, qml}` at `:135`.
- Report uploaded as artifact `skylos-report`, 30-day retention (`:172-178`).

**Does Skylos scan IaC/Docker/systemd?** By design it auto-detects languages by file
extension in one pass and names no language (`:6-8`, `pyproject.toml:336-338`). There
is no Skylos config key that special-cases Docker/systemd/IaC; it would scan any such
files that landed at the root and were not excluded by name. **Today no IaC/Docker/
systemd files exist to scan** (see §4). There is **no standalone Skylos config file** —
all Skylos config lives in `[tool.skylos]` / `[tool.skylos.gate]` in root
`pyproject.toml` (`:333-450`); local state cache is gitignored at `.gitignore:47-49`
(`.skylos/`).

### 1.6 The QA Battery gate (battery.yml) — three jobs

Header (`.github/workflows/battery.yml:1-14`): permanent CI for the QA battery
(card FC-34; OR-10a/b, NFR-02 / AR-11). Runner setup mirrors workspace pins: CPython
3.14 from `.python-version` (AR-04) + pinned `uv==0.12.6`
(`:47-48, 68-69, 96-97`), then `uv sync` for default groups. Fail-closed throughout.

- **`check` job** (`:30-52`): `if: github.event_name != 'schedule'`. Runs
  `uv run poe check` in full (`:51-52`) — the four Tier-1 static scanners
  (money-path float, ambient-nondeterminism, mock-data, secret) plus
  fmt-check/lint/strict-types/tests+coverage/workspace-tool suite. Timeout 30 min.
- **`vulture` job** (`:54-78`): `if: github.event_name != 'schedule'`. Dead-code
  **ratchet**: fails only if the finding count rises above a committed baseline
  (ratchet DOWN, never up). Runs
  `uv run --no-project --with "vulture==2.14" python tools/vulture_gate.py --baseline
  qa/_trace/battery/vulture/gate-baseline-min80.txt --min-confidence 80 --
  packages extensions qml qmb tools` (`:75-78`). `tools/vulture_gate.py` enforces
  vulture's exit-code discipline (0/3 = ran; else broken scan → fail closed)
  (`:70-74`). Timeout 15 min.
- **`mutation` job** (`:80-153`): `if: github.event_name == 'schedule'` — **nightly
  only, Linux-only**. `mutmut==3.3.0` (`:108`) on `qmf-core` `exact.py` + `chrono.py`,
  kill-rate floor **68%** (OR-10b, from the 2c8d495 baseline 249 killed / 117 survived
  = 68.03%) (`:9, :80-83`). Kill-rate = killed / (killed + survived); parses the run
  log's final tally with a results-listing fallback, **fail-closed** if zero mutants
  classified (`:118-145`). Timeout 60 min. Uploads `mutmut-results` (`:146-153`).

### 1.7 Schedule / cron

Exactly one cron, in battery.yml only:
- `.github/workflows/battery.yml:20-23` — `schedule: - cron: "17 2 * * *"` (nightly
  02:17 UTC), which **drives the mutation job only** (`:9, :21-22, :84`). GitHub runs
  scheduled workflows on the default branch (`main`), *"which is exactly where the
  ratified exact.py / chrono.py live."* skylos.yml has **no** schedule.

---

## 2. Toolchain, tasks, and the tier-1 scanners

### 2.1 uv workspace

- `pyproject.toml:85-92` — `[tool.uv.workspace] members = ["packages/*",
  "extensions/*", "qml", "qmb"]`.
- `uv.lock:6-18` — locked members: qmb, qmf-calendar-forex, qmf-core, qmf-data,
  qmf-indicators, qmf-registry, qmf-risk, qmf-structure, qmf-venue, qml, sssf-project.
- `pyproject.toml:83` — `default-groups = ["dev", "store-engines", "calendar-tzdata",
  "venue-proto", "indicators-talib", "qml-lib", "qmb-lib", "qa-suites"]`.
- Dependency groups (`pyproject.toml:119-200`): `dev` (the SSSF gate contract + QMF
  toolchain), `store-engines`=[qmf-data], `qa-suites`=[hypothesis>=6,<7],
  `calendar-tzdata`=[qmf-calendar-forex], `venue-proto`=[qmf-venue],
  `indicators-talib`=[qmf-indicators], `qml-lib`=[qml], `qmb-lib`=[qmb], and
  **`scan`=[skylos]** — deliberately separate from `dev` because skylos's
  tree-sitter-dart-orchard dep is sdist-only and needs MSVC on Windows; a shared group
  would take the whole toolchain down on `uv sync` (`:194-200`).

### 2.2 Pinned toolchain (dev group, DEPENDENCIES.md §Toolchain)

`ruff==0.16.3`, `pyright==1.1.411`, `pytest>=9,<10`, `pytest-cov>=7,<8`,
`poethepoet==0.48.0` (`pyproject.toml:137-141`; `DEPENDENCIES.md:73-77`). Build
backend `uv_build>=0.12,<0.13` (`DEPENDENCIES.md:98`).

### 2.3 Ruff / pyright config

- Ruff: `line-length = 100` (`pyproject.toml:243`);
  `extend-exclude = ["adws/adw_data", "recorder", "tools/tests/fixtures"]`
  (`:242`); real select set `["E","W","F","I","UP","B","S","C4","SIM","RUF","PL"]`
  (`:253`), with reasoned `ignore` list (`:254-273`) and per-file carve-outs
  (`:275-301`). Note the two S404-subprocess carve-outs for the qmb host runner and
  orchestrator (`:297-301`), documenting stdlib process-per-run (B-5).
- Pyright: **strict, workspace-wide** over `["packages","extensions","qml","qmb",
  "tools"]` (`:306`), `typeCheckingMode = "strict"` (`:330`),
  `pythonPlatform = "Windows"` (`:312`), `pythonVersion = "3.14"` (`:331`); adws is
  mypy's job (`:304-305`).

### 2.4 poe tasks (the task surface)

`[tool.poe.tasks]` (`pyproject.toml:452-507`):
- `fmt` / `fmt-check` / `lint` = ruff over `packages extensions qml qmb tools`
  (`:456-458`).
- `types` = `pyright` (`:459`).
- `test` = `pytest packages extensions qml qmb --cov=qmf --cov=qml --cov=qmb
  --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  --cov-fail-under=80` (`:460`).
- `cov-report` = `python tools/coverage_report.py` — per-package + contract-module
  floors: 80% per package, 100% branch on exact.py/chrono.py (`:462-465`).
- `test-tools` = `pytest tools/tests` with its own 80% floor over the scanner modules
  (`:466-469`).
- **The four Tier-1 static scanners** (the ones the task asked to be named):
  - `secret-scan` = `python tools/secret_scan.py` (`:470`; AR-24).
  - `money-path-scan` = `python tools/money_path_scan.py` — fails closed on any
    binary float on the money path (`:471-473`; NFR-02 enforcing FR-001; CT-01,
    DEC-0105).
  - `ambient-scan` = `python tools/ambient_scan.py` — fails closed on any read of the
    system clock or other ambient nondeterminism below the composition root
    (`:474-476`; NFR-02 enforcing FR-002; CT-02, AR-16).
  - `mock-data-scan` = `python tools/mock_data_scan.py` — fails closed on mock/
    placeholder/fabricated data in shipped source (`:477-479`).
- `build-all` = `uv build --all-packages` (`:480`).
- `isolated-build` = `python tools/isolated_build_check.py` — Tier-2 isolated-install
  smoke (`:481-484`; AR-06/AR-18; M9).
- `qa-verify` = `python qa/run_qa_verify.py` (`:461`).

Task sequences:
- `check` (Tier 1): `["fmt-check","lint","types","test","cov-report","test-tools",
  "money-path-scan","ambient-scan","mock-data-scan","secret-scan"]` — fail-closed
  (`:486-494`).
- `check-integration` (Tier 2): `["check","build-all","isolated-build"]` (`:496-501`).
- `check-release` (Tier 3): `["check-integration"]` today; the both-OS clean-install
  smoke is added once a remote exists (`:503-507`).

The `tools/` directory (all files): `ambient_scan.py`, `coverage_report.py`,
`isolated_build_check.py`, `mock_data_scan.py`, `money_path_scan.py`,
`secret_scan.py`, `vulture_gate.py`, `workspace_meta.py`, plus `tools/tests/`.
These import as top-level modules via the pytest/pyright pythonpath
(`pyproject.toml:220-223, 327-328`).

### 2.5 The Skylos gate thresholds (fail-closed + ratchet)

`[tool.skylos.gate]` (`pyproject.toml:402-450`): all hard-zero buckets —
`max_critical=0`, `max_high=0`, `max_security=0`, `max_reliability=0`,
`max_secrets=0`, `max_dependency_vulnerabilities=0`, `max_ai_defects=0`
(`:409-415`); `strict=false` deliberately (`:416-420`). Two **ratchet** limits
(OR-10a/b, 2026-08-27): `max_quality=4084` (`:441`) and `max_dead_code=80`
(`:446`) — "never worse than today", ratchet down only. `SKY-D223` (undeclared
import) is the one rule switched off, because it cannot read PEP 735
`[dependency-groups]` or workspace-member manifests (`:383-400`); SKY-D222
(hallucinated dep) stays fully on.

---

## 3. justfile, .python-version, .vscode, .env.sample, conventions/, CLAUDE.md

### 3.1 justfile (`justfile`, 197 lines)

SSSF starter recipes, stamped by install.py. Key facts:
- `set dotenv-load` (`:8`) — `.env` reaches every ADW.
- `set windows-shell := ["cmd.exe", "/c"]` (`:13`) — Windows uses cmd.exe; *"just only
  applies windows-shell when actually running on Windows, so Linux/mac keep the
  default shell — the server is unaffected"* (`:9-12`).
- Recipes are all **factory** recipes: `doctor`, `demo`, `prompt`, `scout`, `plan`,
  `plan-build`, `sdlc`, `simple-sdlc`, `work`/`work-next` (dispatch), `engine`,
  `worktrees`/`worktrees-prune`, `ship-report`, `clean`, `sessions`/`phases`/`tail`/
  `procs` (sqlite reads), `obs` (bun/vite trace UI).
- **The engine recipe documents a systemd unit on the server** (factory precedent):
  `justfile:99-110` — *"The always-on worker that runs the Board by itself... On the
  server systemd runs this exact command as `sdl-engine.service`; this recipe is the
  same process in the foreground."* `engine:` = `uv run adws/engine.py` (`:109-110`).
- `obs` recipe has per-OS bodies (`[windows]`/`[unix]`, `:191-197`) and needs `bun` +
  `bunx vite`; the visualizer is a Node/TS app under `.claude/skills/sssf`
  (`:167-178`). Not part of the node product.

### 3.2 .python-version / uv.lock / .vscode / conventions

- `.python-version:1` = `3.14`.
- `.vscode/settings.json:1-8` — only `files.exclude` for `__pycache__`, `.agent`,
  `.agents`, `.claude`, `_bmad`. No launch/task/debug config, no remote-container
  config.
- `conventions/` has ONE file: `conventions/failure-register.md` — the **NFR-11
  failure-register convention**: every designed failure mode ships a
  `packages/<pkg>/FAILURES.md` (or `extensions/<pkg>/FAILURES.md`) entry with fields
  Failure class / Detection / Auto-recovery-retry / Visible degraded state /
  Notification tier / Product-user affordance (`conventions/failure-register.md:1-49`).
  A designed failure with no register entry is an incomplete story (`:11-13`). This is
  a **coding convention the node must follow** for every failure mode it introduces
  (connection loss, credential expiry, reconciliation drift, kill-switch, etc.).

### 3.3 .env.sample — VARIABLE NAMES ONLY (no values read)

`.env.sample` is the **SSSF factory** environment, not node runtime. All keys are
commented placeholders. Names present:
- `OPENROUTER_API_KEY` (`.env.sample:23`)
- `XAI_API_KEY` (`:24`)
- `ANTHROPIC_API_KEY` (`:25`)
- `PI_PATH` (`:28`)
- `PI_MODELS_PATH` (`:29`)
- `ENGINEER_NAME` (`:30`)

Explicitly: *"Set a key here only for a provider whose entry ... reads one from the
environment"* (`:15-17`). **There are NO trading-node / cTrader / IC-Markets / venue
credentials in `.env.sample`** — the node's runtime secrets have no sample and no
`.env` slot yet (consistent with the secret contract, which forbids secrets in `.env`
entirely; see §6). `.env` itself is gitignored (`.gitignore:45`).

### 3.4 CLAUDE.md on integration

`CLAUDE.md:1-38` on integration is an **older** copy than the working-tree project
CLAUDE.md: at `:35-38` it bans `bmad-sprint-planning`, `bmad-build`, **and every
`bmad-testarch-*` skill**. (The working-tree CLAUDE.md re-allows testarch per operator
ruling 2026-08-27.) Divergence noted; not DevOps-blocking, but the integration branch
predates the testarch re-allowance.

---

## 4. Deployment-artifact search — what exists, what does NOT

**Exhaustive search of the whole worktree found ZERO deployment artifacts for the
trading node.**

`find` for `Dockerfile*`, `docker-compose*`, `*.service`, `Procfile`, `*.tf`,
`*.tfvars`, `cloud-init*`, `install.sh`, `Makefile`, `*.nomad`, `Vagrantfile`
→ **no matches**. Directory search for `systemd`, `ansible`, `terraform`, `pulumi`,
`k8s`/`kubernetes`, `deploy*`, `infra*`, `helm` → only `docs/lenses/ops` (prose docs).

Keyword grep results (deployment/observability):
- **`systemd`**: hits are ONLY in factory machinery `adws/` (comments describing the
  `sdl-engine.service` unit) — e.g. `adws/engine.py:14`, `:212`, `:411`;
  `adws/adw_modules/git_helper.py:25,40,56,68`; `adws/adw_modules/utils.py:38,118-144`;
  `adws/adw_modules/quality.py:14`; `adws/dispatch.py:87,365`;
  `adws/adw_modules/agent_pi.py:79`. **No committed `.service` file exists** — the unit
  is referenced, never checked in.
- **`systemd-creds`**: hits are ONLY in **docs and planning artifacts**, never code:
  `docs/contracts/ct-21-venue-secret-session.yaml:28`, `docs/glossary.md:514`,
  `docs/lenses/ops/runbook.md:122`, `docs/lenses/security/security-model.md:61`,
  `archive/recovery/trading-node-delta/...`, `_bmad-output/.../ARCHITECTURE-SPINE.md:265`,
  `_bmad-output/.../mine-node.md:175,186`, `_docwork/ledger.yaml:1279`. All say the same
  thing: the `systemd-creds`-class store is the *deployment substrate* and its
  **mechanics/key-custody land at the node/ops sitting (DEC-0136)** — i.e. this sitting.
- **`keyring`**: **no hits** anywhere.
- **`prometheus`**: only a workroom research note
  (`workroom/research/08-mis-ml-regime-models.md:323`) — not code, not a decision.
- **`opentelemetry`**, **`structlog`**, **`loguru`**, **`logging.config`**,
  **`journald`**, **`APScheduler`**: **no hits** anywhere.
- **`healthcheck` / `/health`**: no product code. `/health` appears only as an EXAMPLE
  prompt string in factory templates (`adws/adw_data/prompt_engineering/*/user.md`) and
  in prose docs/planning. There is no HTTP health endpoint.

`.github/secret_scanning.yml:1-12` — GitHub-native secret scanning, `paths-ignore`
scoped to `tools/tests/fixtures/secret/**` and `tools/tests/test_secret_scan.py` (the
scanner's own corpus). Not a deployment artifact.

`.gitignore` (`.gitignore:1-49`) ignores `.venv/`, build artifacts, `/data/`,
`*.bi5`, `recorder/data/`, `.env`, `adws/adw_data/sessions/` + `sssf.db*`, `.skylos/`,
agent tooling installs. Nothing deployment-related.

---

## 5. Packages, versions, dependencies, entry points

### 5.1 Console scripts — exactly ONE in the whole workspace

`qmb/pyproject.toml:20-21` — `[project.scripts] qmb = "qmb.doors.cli:main"`. This is
the **only** `[project.scripts]` / console-script across every pyproject in the repo
(confirmed by grep). qml is explicitly **never a CLI** (`qml/pyproject.toml:4`). The
trading node therefore has **no existing daemon/service entry point** — it must be
built.

### 5.2 Roster packages (all `0.1.0`, requires-python `>=3.14,<3.15`)

| Package | Version | Third-party runtime deps | Roster edges / note |
|---|---|---|---|
| `qmf-core` | 0.1.0 | **none** (stdlib only) | `packages/qmf-core/pyproject.toml:2-7`. Exact money/time primitives, typed refusals, single fp1 serializer, protocol seams. |
| `qmf-registry` | 0.1.0 | none | deps `qmf-core`, `qmf-data` (`packages/qmf-registry/pyproject.toml:7-9`). The sole inter-library edge `qmf-registry → qmf-data`. |
| `qmf-data` | 0.1.0 | `pyarrow==25.0.1`, `duckdb==1.5.5` | `packages/qmf-data/pyproject.toml:7-13`. Journals, source adapters, backup primitives. |
| `qmf-indicators` | 0.1.0 | `ta-lib==0.7.1`, `numpy==2.5.2` | `packages/qmf-indicators/pyproject.toml:16-26`. numpy now a DIRECT dep (QMX-F033), no longer "permitted-but-not-added". |
| `qmf-structure` | 0.1.0 | none | dep `qmf-core` (`packages/qmf-structure/pyproject.toml:7-8`). Causal chart objects (CT-17). |
| `qmf-venue` | 0.1.0 | `protobuf==7.36.0` | `packages/qmf-venue/pyproject.toml:7-17`. **Edge module: "nothing imports it"** (`:4`). cTrader translation; compiles Spotware proto in-house. |
| `qmf-risk` | 0.1.0 | none | dep `qmf-core` (`packages/qmf-risk/pyproject.toml:7-8`). **"The ratified Book, BMS, exit, paper-mode, control, and risk-arithmetic boundary (AD-29..41). An edge module: nothing imports it"** (`:4`). This is the node's runtime boundary. |

Off-roster / app-layer:
- `qmf-calendar-forex` 0.1.0 — deps `qmf-core`, `tzdata==2025.2`
  (`extensions/qmf-calendar-forex/pyproject.toml:2-11`).
- `qml` 0.1.0 — deps `qmf-core`, `qmf-registry`, `qmf-risk`; never a CLI
  (`qml/pyproject.toml:4, 8-12`).
- `qmb` 0.1.0 — deps `qmf-core`, `qmf-registry`, `qmf-data`, `qmf-indicators`,
  `qmf-structure`, `qmf-risk`, `qml`, `click==8.4.2`, `optuna==4.9.0`
  (`qmb/pyproject.toml:8-18`). Console script `qmb` (`:20-21`).

All build with `uv_build` and PEP 420 namespace (`module-name` set for qmb/qml which
are top-level imports, not `qmf.*`): `qmb/pyproject.toml:23-29`, `qml/pyproject.toml:14-20`.

### 5.3 Dependency POLICY (DEPENDENCIES.md) — a hard node constraint

`DEPENDENCIES.md:9-18`:
- Allowed: MIT, BSD, Apache-2.0, PSF.
- **Rejected: GPL/AGPL; any strategy-family dep; and any *platform-imposing*
  dependency — "one that dictates an event loop, reactor, daemon, or runtime the
  platform must adopt — e.g. Twisted"** (`:11-13`).
- `qmf-core` takes zero outside dependencies (`:16`).
- Spotware's OpenApiPy SDK is **reference-only, rejected as a runtime dep** precisely
  because "its pinned Twisted reactor is platform-imposing" (`:47`). qmf-venue compiles
  the Spotware proto in-house via `google.protobuf`; **zero Spotware code runs** (`:47`).

Node relevance: whatever long-running process the node adopts must be built on the
**stdlib** (asyncio is stdlib and permitted; a framework that imposes its own
reactor/daemon is not). alembic/sqlalchemy/mako appear in `uv.lock` (e.g.
`uv.lock:20-31`) only as **transitive deps of optuna**, not direct — no direct DB/ORM
dependency is declared.

---

## 6. Answers to the six pointed questions

### (a) Exact CI OS matrix today
**100% `ubuntu-latest`** across all four jobs (skylos + battery check/vulture/mutation):
`.github/workflows/skylos.yml:36`, `.github/workflows/battery.yml:35,57,85`. No
Windows, no macOS, no matrix strategy. Ratified tier-1 OS is nonetheless **Windows**
(pyright `pythonPlatform="Windows"`, `pyproject.toml:307-312`); **Ubuntu is a ratified
tier-1 target left untested until a remote exists** (AR-23, `pyproject.toml:503-506`).

### (b) Does anything run on Linux in CI at all?
**Yes — everything.** All CI is Linux (`ubuntu-latest`). The nightly mutmut job is
described as "Linux-only" (`.github/workflows/battery.yml:80-83`). The irony for the
node: the code targets Windows as tier-1 primary, but is only ever *exercised* on Linux
in CI.

### (c) Any long-running process / daemon / scheduler code anywhere?
**No persistent daemon/scheduler exists in the shipped product libraries — and it is
refused by design.**
- The libraries **ban** `asyncio`/`threading`/`sched`/`multiprocessing`/`concurrent`/
  `crontab` via conformance tests: `packages/qmf-data/tests/test_cycle.py:225`;
  `qml/src/qml/conformance/scan.py:72-73`; qml/qmb ban-tests
  (`qml/tests/test_prediction.py:425`, etc.).
- `qmf-data` **refuses by contract to own scheduling/daemons**:
  `packages/qmf-data/src/qmf/data/cycle.py:6` ("owns **no** threads, cron, daemon, or
  scheduler"), `:96`, and `own_schedule()`/`start_daemon()` **always return typed
  refusals** (`cycle.py:307-315`). `packages/qmf-data/src/qmf/data/ingest.py:30,98,112`
  — "owning a scheduler, daemon, process supervisor, or retry loop is a policy
  rejection (AC6/FM-5)."
- The only `while True` in product code is qmb's **run-scoped, bounded** backtest
  orchestrator watch loop (`qmb/src/qmb/orchestrator/spawn.py:508`, polling child
  `.poll()` with `wait(timeout=WATCH_POLL_S=0.05)`; `qmb/src/qmb/orchestrator/watch.py:56`)
  and a deterministic RNG loop (`qmb/src/qmb/data/rng.py:109,125`). Neither is a
  persistent service.
- No `signal.signal`, no `APScheduler`, no `threading.Timer` in product code
  (`threading.Thread` appears only in a qmf-data concurrency TEST,
  `packages/qmf-data/tests/test_jsonl_engine.py:186`).
- The **only** always-on process in the whole repo is the **factory** worker
  `adws/engine.py` (~60s cycle, systemd `sdl-engine.service`) — excluded machinery
  (`[tool.skylos] exclude` includes `adws`, `pyproject.toml:365`), NOT the trading
  product.
- The standalone `recorder/` calendar tool runs on a **Windows Scheduled Task**
  (`QMX-Calendar-Recorder`, daily 06:00 + repeat 12h) — `recorder/README.md`; stdlib
  only, gitignored data, not the node.

**Conclusion: the node's long-running Book/BMS runtime + venue-session loop + nightly
data cycle scheduling DOES NOT EXIST and was deliberately reserved for the node/ops
sitting.**

### (d) Any HTTP / API server code?
**No.** `fastapi`, `starlette`, `uvicorn`, `aiohttp`, `flask`, `httpx`, `requests`,
`django`, `http`, `socket`, `urllib`, `grpc` appear ONLY inside qmb **ban-tests** that
assert none of them are imported: `qmb/tests/test_api_door.py:22-49`,
`qmb/tests/test_mcp_door.py:36-...`. Findings on the actual doors:
- qmb **API door** = a *thin in-process re-export* (Story 16.3; B-1, B-13, AR-58) — NOT
  a network server; HTTP modules are forbidden (`qmb/tests/test_api_door.py:1`,
  `:22-49`). Source at `qmb/src/qmb/doors/api/`.
- qmb **MCP door** = "an **unshipped** localhost sibling (SC-08, B-1, AR-58)" — it has
  `BIND_HOST`/`LOCALHOST_BOUND`/`STACKED_OVER_HTTP` constants but is not shipped
  (`qmb/tests/test_mcp_door.py:1,11-28`). Source `qmb/src/qmb/doors/mcp/`.
- The shipped door is the **CLI** (`qmb/src/qmb/doors/cli/`), `POST_CLI_V1`.
No `http.server`, `asyncio.start_server`, `.listen(`, `.bind(`, `run_forever`, or
`mainloop` anywhere in product code.

### (e) What logging is used; are logs vs journals separated in code?
- **No logging framework or logger configuration exists in product code.** `import
  logging` appears only in a qmf-core TEST that verifies a `SecretValue` does NOT leak
  through a logger (`packages/qmf-core/tests/test_secret.py:12,147-150`). No
  `structlog`, `loguru`, `journald`, `logging.config`, or `getLogger` in shipped
  source (the one `optuna.logging.set_verbosity` at `qmb/src/qmb/optimize/sampler.py:76`
  just quiets optuna).
- **Logs vs journals are separated in the CONTRACT, not yet in operator-log code.**
  `docs/lenses/observability/logging-spec.md:16` (DEC-0112): *"Logs are not journals ...
  Operator and diagnostic log text renders timestamps as UTC ISO-8601 with an explicit
  `Z`; journals and every evidence stream store int64 UTC nanoseconds plus writer and
  sequence per the exact-time contract."* CT-13 is the ratified journal boundary
  (N append streams, one per producing component); *"The operator log-level taxonomy,
  logger names, file paths, and query system belong to the full monitoring design at
  the node/ops sitting; this lens carries the binding convention only."*
  `logging-spec.md:25` — operator-log storage = "Node/ops monitoring stack
  (unratified)".
- **Journals DO exist in code** (the evidence side): `qmf-data` `journal.py`
  implements CT-13 journals with fp1 identity and `correlation_id`/`display_time`
  **excluded from identity** (`packages/qmf-data/src/qmf/data/journal.py:27,31,92-95,296`).
  `correlation_id` is a linking annotation that propagates but never changes identity
  (DEC-0112).
- So: the **evidence journal** half is built; the **operator/diagnostic log** half
  (framework, level enum, logger names, file paths, query) is entirely a node/ops
  obligation with only the UTC-ISO-8601-`Z` convention binding now.

### (f) How are secrets read today?
- **Through a core `SecretStore` Protocol port — never from the environment.** Defined
  in `packages/qmf-core/src/qmf/core/secret.py`: `SecretRef` (opaque minted id),
  `SecretValue` (never renders its secret; `repr`/`str`/serialization/logging all yield
  the reference id; only `.reveal()` returns material), and `SecretStore`
  (`typing.Protocol` exposing only **read** + **atomic_replace**) —
  `secret.py:1,9,22,188`. The only concrete implementation is an **in-memory reference
  store for examples/tests** (`InMemorySecretStore`,
  `packages/qmf-core/examples/secret_usage.py:50-51`). **No production store exists.**
- **`keyring`: not used anywhere.** No `os.getenv`/`getenv` for secrets.
- `os.environ` reads in product code are NOT secret reads: subprocess env-passing in
  the qmb orchestrator/host (`qmb/src/qmb/host/runner.py:582`,
  `qmb/src/qmb/orchestrator/spawn.py:1278`), a factory-sandbox marker
  (`qmb/src/qmb/orchestrator/ledger.py:64`, `os.environ.get(FACTORY_SANDBOX_ENV,"")`),
  a benchmark PYTHONPATH set (`packages/qmf-core/src/qmf/core/_bench.py:142-144`), and
  the tzdata TZPATH set (`extensions/qmf-calendar-forex/src/qmf/calendar_forex/_tzdb.py:46`).
- **The contract (DEC-0136 / AD-26 / CT-21) binds the node here:** values are injected
  at the **composition root** from the deployment environment's protected store
  (`systemd-creds`-class on the VPS); only the adapter's **connection manager** holds
  `SecretValue`s in memory; secrets never appear in repos/config/docs/chat/`.env`/CLI/
  journals/evidence/fingerprints/logs; a missing/expired credential is an
  unavailable-dependency typed refusal carrying the reference id, never the value.
  Store mechanics + key custody are explicitly deferred to **this node/ops sitting**:
  `docs/lenses/security/security-model.md:61`, `docs/lenses/ops/runbook.md:122`,
  `docs/contracts/ct-21-venue-secret-session.yaml:28`, `docs/glossary.md:514`,
  `_bmad-output/.../ARCHITECTURE-SPINE.md:265`.

---

## 7. Observability & ops docs — promised vs implemented

`docs/lenses/observability/` = two prose specs; `docs/lenses/ops/` = two runbooks.
Nothing under either is executable.

| Promised (docs) | Implemented in code? | Citation |
|---|---|---|
| Operator/diagnostic logs (UTC ISO-8601 `Z`), log-level taxonomy, logger names, file paths, query system | **No** — "unratified", node/ops sitting owns it; only the `Z` convention binds | `docs/lenses/observability/logging-spec.md:16,25,66,74` |
| CT-13 evidence journals (int64 UTC ns + writer + sequence) | **Yes** — qmf-data `journal.py` | `packages/qmf-data/src/qmf/data/journal.py:27,296` |
| Metrics schema / dashboard / alert thresholds / severity / paging | **No** — "QMF V1 has no ratified metrics schema, aggregation window, dashboard, alert threshold, severity tier, notification destination, paging route, or automatic remediation" | `docs/lenses/observability/metrics-and-alerts.md:16,46,48` |
| Signals **exportable to Prometheus-class stacks with push alerting** (obligation binds now; stack choice = node/ops) | **Not implemented** — obligation only; no exporter, no `prometheus_client` | `docs/lenses/observability/metrics-and-alerts.md:16,20` |
| Named node signals: chrony offset/stratum/sync-age, per-venue clock skew, clock-step counter, over a push-alert path with no on-call rotation | **No** — no `chrony`/`ntp`/`stratum`/`sync-age` in code anywhere; companion planning doc `time-audit-devops.md` | `docs/lenses/observability/metrics-and-alerts.md:20`; companion `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md` |
| `health()` per component + `correlation_id` propagation (observability convention; a component with no working `health()` is a defect) | **Partly** — typed in-process `health()` methods exist (NOT an HTTP endpoint): qmf-venue connection `HealthReport`/`health()`, qmf-indicators streaming `health()`, qmb orchestrator log `health()` | `docs/lenses/bugs/triage.md:25`; `packages/qmf-venue/src/qmf/venue/connection.py:338,694`; `packages/qmf-indicators/src/qmf/indicators/streaming.py:918`; `qmb/src/qmb/orchestrator/log.py:451` |
| Benchmark harness per component (measure-then-budget, AD-13; peak memory + speed) | **Yes (harness present)** — e.g. `qmf-core` `_bench.py` | `packages/qmf-core/src/qmf/core/_bench.py`; `docs/lenses/observability/metrics-and-alerts.md:16` |
| Node-service secrets via `systemd-creds`; `Restart=on-failure`, start-limit counters; crash-loop thresholds K/T open | **No** — docs/planning only | `docs/lenses/ops/runbook.md:122`; `archive/recovery/trading-node-delta/work/wiki-inventory.md:78` |

Runbook posture is explicit that it grants no authorization: *"This runbook grants no
credential-bearing operation; implementation authorization arrives only through the
factory pipeline"* (`docs/lenses/ops/runbook.md:122`).

---

## 8. Platform-portability surface (node runs on Linux VPS)

- The ONLY `sys.platform` branching in all product code is
  `qmb/src/qmb/orchestrator/watch.py`: `if sys.platform == "win32"` (`:111`),
  `sys.platform == "darwin"` (`:366`), and a POSIX default. It reads child-process peak
  memory via `resource.getrusage` on POSIX (`try: import resource` with a Windows
  `ImportError` fallback, `:18-21`) and via `ctypes.WinDLL("kernel32"/"psapi")` +
  `GetProcessMemoryInfo` on Windows (`:274-309`). So the process seam **does have a
  Linux path** — but the strict type gate validates the **Windows** view of it
  (pyright `pythonPlatform="Windows"`, §1.3). This is the concrete "byte-identical
  Windows verdict on a Linux runner" seam and the one place the node's Linux target and
  the ratified Windows tier-1 collide.
- Process management everywhere is `stdlib.subprocess` (B-5): `PROCESS_MANAGEMENT =
  "stdlib.subprocess"` (`qmb/src/qmb/orchestrator/spawn.py:106`,
  `qmb/src/qmb/host/runner.py:99`); `subprocess.Popen`/`subprocess.run` with
  `TimeoutExpired` handling. No `psutil`, no Job Objects, no `os.kill`/`taskkill`.
- Everything else in the workspace is platform-agnostic pure Python.

---

## 9. What the node sitting must supply (gaps, all deferred by the corpus, not oversights)

1. **A long-running runtime** hosting Book/BMS (from edge module `qmf-risk`, AD-29..41)
   + QML bot seats + the venue session loop over `qmf-venue` — none exists; the
   libraries refuse to own it (§6c). Must be stdlib-based (no platform-imposing dep;
   `DEPENDENCIES.md:11-13`).
2. **A scheduler / process supervisor** for the nightly data cycle and session duties
   (heartbeat/refresh/reconnect/monitors run on "the app's scheduler",
   `tracker/trading-node-notes.md:47`) — refused by `qmf-data`
   (`packages/qmf-data/src/qmf/data/cycle.py:307-315`, `ingest.py:30`).
3. **A deployment substrate on Linux VPS**: service unit (the factory precedent is
   `sdl-engine.service` with `Restart=always`), no committed unit file yet.
4. **The `systemd-creds`-class SecretStore** concrete implementation injected at the
   composition root (only the in-memory reference store exists today) — DEC-0136,
   `packages/qmf-core/src/qmf/core/secret.py`.
5. **Operator logging + metrics export + alerting** (Prometheus-class exportability is
   an obligation that binds now; nothing implemented) — `metrics-and-alerts.md:16,20`.
6. **Control doors**: CLI/API now, UI later. The precedent is qmb's thin **click** CLI
   door (`qmb/src/qmb/doors/cli:main`); the API door pattern is in-process, the MCP
   door is localhost-bound but unshipped. No network control surface exists yet.
7. **Node numeric constants under do-not-default** (retry/pool/health, submission
   deadline that triggers UNKNOWN, crash-loop K/T) — corpus values are RECONFIRM-grade
   only (`docs/lenses/bugs/triage.md:54`;
   `_bmad-output/.../trading-node-order-path-study.md:138,170`).
8. **A `FAILURES.md` per package** for every designed node failure mode (NFR-11
   convention, `conventions/failure-register.md`).
9. **A Linux CI lane** if the node is to be exercised on its actual target OS (today
   CI is Linux but the type gate is pinned to Windows; the Ubuntu clean-install smoke
   is deferred until a remote exists, `pyproject.toml:503-506`).

---

## 10. Credential-material note

No credential or token was opened, printed, or copied. `.env.sample` contains only
commented placeholder KEY NAMES (§3.3); `.env` is gitignored and absent from the
worktree. No secret material was encountered.
