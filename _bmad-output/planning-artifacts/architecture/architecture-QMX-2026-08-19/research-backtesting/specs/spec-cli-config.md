# Spec: The CLI Itself + Config Model (the Wind-Tunnel)

**Feature area:** QMX command-line entrypoint and configuration layering — creating a
Book/BMS materializes a read-only CONFIG the CLI resolves and consumes; "test = can a
bot fit the Book"; CLI updatable like npm.

**Sources read (read-only):**
- Lean CLI (Python orchestrator): `scratchpad/lean-cli/lean/...`
- Lean engine (C#): `scratchpad/lean-engine/Launcher/config.json`
- Jesse v3.0.6 (Python): `workroom/reference/repos/jesse/jesse/...`

**Method:** mechanism understanding only. No third-party code is reused. QMF law is the
binding contract everywhere below.

---

## 1) Feature claim (verbatim, with URL)

**Lean CLI** — https://www.lean.io/docs/v2/lean-cli/initialization/configuration
- "The Lean configuration contains settings for locally running the LEAN engine. This
  configuration is created in the `lean.json` file when you run `lean init` in an empty
  directory."
- "The configuration is stored as JSON, with support for both single-line and multiline
  comments."
- "The CLI stores its persistent configuration in various places depending on the context
  of the configuration." Three tiers: Global config = "CLI defaults and API credentials";
  Lean config = "settings for locally running the LEAN engine"; Project configuration
  (separate).
- "The CLI commands can update most of the values of the `lean.json` file" (some settings
  are manual).
- Marketing header: "Harness the power of LEAN locally or in the cloud."

**Lean CLI install/update** — https://www.lean.io/docs/v2/lean-cli/installation/installing-pip
- Installed and upgraded via `pip install lean` / `pip install --upgrade lean` (the CLI's
  own outdated-warning message, verified in code, tells the user this exact command).

**Jesse** — https://docs.jesse.trade/docs/getting-started/
- "We understand the importance of getting started quickly and easily. So we've taken care
  of all the hard work for you."
- `jesse run` "starts the application" (prints `Uvicorn running on http://0.0.0.0:9000`).
- ".env file by copying it from the template" — users edit `.env` for DB credentials and
  dashboard password; "APP_PORT value in your project's `.env` file" changes the port.
- Project template ships a `strategies` directory and a `storage` directory ("logs, chart
  images, etc").
- Install/upgrade: `pip install jesse` / `pip install -U jesse`.

---

## 2) Mechanism — how the code actually does it

### 2A) Lean — the config is the product; the CLI is a config compiler

Lean's CLI is fundamentally **a config-synthesis + Docker-launch orchestrator**. The C#
engine only ever reads one thing: a fully-resolved `config.json` mounted into the
container. The CLI's whole job is to *produce* that file from layered sources. This is
exactly the operator's wind-tunnel: the tunnel (engine) never changes; the CLI assembles
the variables into one artifact the tunnel consumes.

**The layers (precedence, lowest → highest):**

1. **Synthesized engine defaults** — the `lean.json` starts life as a *cleaned copy* of the
   engine's own `Launcher/config.json`. `lean init` downloads the Lean repo, reads
   `Launcher/config.json`, and runs `clean_lean_config()` to strip every key the CLI will
   set automatically per-run, then saves the remainder as `lean.json`
   (`commands/init.py:177-185`). `clean_lean_config()` removes `environment`,
   `algorithm-type-name/-language/-location`, `parameters`, credentials, debugging keys,
   etc. via **string manipulation, not JSON parsing, specifically to preserve comments**
   (`config/lean_config_manager.py:158-210`, keys list at :186-191).

2. **`lean.json`** (the persistent project-root config, JSON-with-comments). Located by
   **recursing upward from cwd** until a `lean.json` is found — this is what makes any
   subdirectory "inside the workspace" (`lean_config_manager.py:53-84`; filename constant
   `DEFAULT_LEAN_CONFIG_FILE_NAME = "lean.json"`, `constants.py:57`). Parsed by a custom
   comment-stripping parser with a `json5` fallback (`lean_config_manager.py:323-354`).

3. **Per-project `config.json`** (one per project dir; `PROJECT_CONFIG_FILE_NAME =
   "config.json"`, `constants.py:63`). Holds `algorithm-language`, `parameters`,
   `local-id` (a random 9-digit id minted on first use, `project_config_manager.py:52-69`),
   `cloud-id`, `libraries`. Managed as a `Storage` JSON file
   (`project_config_manager.py:44-50`).

4. **Global config / credentials** — two `Storage` files: general options and credentials,
   fronted by `CLIConfigManager` (`config/cli_config_manager.py:23-75`). Typed options:
   `user-id`, `api-token` (credentials store), `default-language`, `engine-image`,
   `research-image`, `database-update-frequency`. `lean config set/get/list/unset` operate
   here.

5. **CLI flags for the specific run** (highest) — e.g. `--parameter k v`, `--image`,
   `--data-provider-historical`, `--backtest-name`, `--extra-config k v`.

**The synthesis function — `get_complete_lean_config(environment, algorithm_file,
debugging_method)`** (`lean_config_manager.py:212-294`) is the heart. It:
- loads `lean.json`, sets `environment`, `close-automatically`, `composer-dll-directory`,
  debugging keys;
- fills a `config_defaults` block (`job-user-id`, `api-access-token`, org id, project id,
  IB/IQFeed hosts) **only for keys the user hasn't already set** (the `if config.get(key,
  "") == "":` guard at :257-259 — the precedence rule in code);
- introspects the algorithm file to set `algorithm-type-name/-language/-location` (Python:
  filename-derived; C#: regex `class ... : QCAlgorithm` at :271);
- pulls `parameters` and library paths from the **project** `config.json` (:275-286);
- defaults object-store limits (:289-292).

**The resolved-run artifact (the inspectable fingerprint source).** Two things happen at
run time in `backtest.py`:
- an **output directory** is created at `PROJECT/backtests/<TIMESTAMP>`
  (`commands/backtest.py:325-326`);
- the fully-resolved config dict is serialized to a real file and **bind-mounted read-only**
  into the engine container at `.../config.json`
  (`docker/lean_runner.py:304-324`: `dumps(lean_config, indent=4)` → temp `config.json` →
  `Mount(..., read_only=True)`).
- a sidecar `config` Storage file in the output dir records the run's identity: an
  `id` (prefix-tagged: `1`=backtest, `2`=optimization, `3`=live, minted as
  `int(prefix + randint(1e8,1e9))`, `output_config_manager.py:151-165`), `container` name,
  `backtest-name`, and resolved environment. This is how a completed run is later found
  **by id** (`get_backtest_by_id`, :74-81) — an immutable per-run ledger key.

So Lean already has: a compiled read-only config per run + a stable run id + a saved
resolved artifact. That triple is the fingerprint substrate.

**Atomic, comment-preserving writes.** `set_properties()` rewrites `lean.json` preserving
comments (:140-156); all `Storage` writes go through `safe_save()` — lock-file + temp-file +
atomic `move` (`config/storage.py:18-49`). No torn configs under 12-14 concurrent runs.

**CLI framework.** Click group `lean` with an `AliasedCommandGroup`
(`commands/lean.py:23`), commands registered flat in `commands/__init__.py:38-59`
(`config`, `cloud`, `data`, `library`, `live`, `login/logout/whoami`, `init`,
`create-project`, `delete-project`, `backtest`, `optimize`, `research`, `report`, `build`,
`logs`, `object-store`, `private-cloud`). Every heavy command subclasses `LeanCommand`
(`click.py:178-284`) which declaratively declares `requires_lean_config` /
`requires_docker`; on invoke it locates/prompts for the config, auto-injects a
`--lean-config` override option (`get_params`, :286-296), auto-elevates for Docker on Linux,
and runs the update check. **Autocomplete** is stock Click shell completion (Click
generates bash/zsh/fish completion; the CLI adds nothing custom — the docs page
"Setting up local autocomplete" points at Click's mechanism).

**Self-update (the npm-update analog).** Two independent clocks in `UpdateManager`
(`util/update_manager.py`):
- **CLI package:** on *every* command, after the body runs, `warn_if_cli_outdated()` queries
  `https://pypi.org/pypi/lean/json`, compares `packaging.version.Version`, and if newer
  prints "Run `pip install --upgrade lean`" (:43-75). Throttled to once / **24h**
  (`UPDATE_CHECK_INTERVAL_CLI = 24`, `constants.py:88`). Dev versions never warn (:54).
- **Engine image:** `pull_docker_image_if_necessary()` compares local vs remote Docker
  **digest** and pulls when they differ; throttled per-image to **once / 7 days**
  (`UPDATE_CHECK_INTERVAL_DOCKER_IMAGE = 24*7`, :91). `--update` forces a pull, `--no-update`
  suppresses it. So the *engine* auto-updates on a weekly cadence while the *CLI package* is
  a user-run pip upgrade. The throttle state lives in a cache `Storage` keyed
  `last-update-check-<key>` with UTC timestamps (:174-203).

`create-project` scaffolds a project dir + starter algorithm + a fresh project `config.json`
(random `local-id`) + a research notebook (`commands/create_project.py:403+`).

### 2B) Jesse — config as a mutated global dict + `.env`, CLI reduced to a server launcher

Jesse v3.x has **inverted** its model: the CLI is now essentially one command. `jesse run`
(`cli.py:43-167`) validates cwd, runs DB migrations, starts an LSP + an **MCP server**, and
launches a **FastAPI/uvicorn dashboard** on a port. There is no `jesse backtest` on the
command line anymore — configuration and runs are driven through the dashboard, the research
API, or MCP tool calls. `cli.py` also exposes `install-live`. (`--version` via
`click.version_option`, `cli.py:17`.)

**Config model:**
- A single module-global `config` **dict** with two halves: `env` (user-tunable: caching,
  logging toggles, per-exchange fee/type/leverage/balance, optimization trials, warmup
  candles) and `app` (runtime placeholders: symbols, timeframes, trading_mode, debug)
  (`config.py:8-103`). Exchange defaults are auto-populated from `info.py`
  (`config.py:106-113`).
- **`set_config(conf)`** mutates that global at run start, branching on mode
  (`is_optimizing/backtesting/live`) and copying only the mode-relevant keys
  (`config.py:116-171`). `reset_config()` restores a `backup_config.copy()` snapshot
  (:173-178) — important because the global is process-wide and reused across runs.
- **`.env`** supplies infra + secrets: Postgres, Redis, `APP_PORT/APP_HOST`, dashboard
  password, license. Loaded via `python-dotenv` into `ENV_VALUES`
  (`services/env.py:1-19`). `cli.py:114-123` reads `APP_PORT/APP_HOST` from it.
- **`get_config('a.b.c', default)`** is dotted-path lookup with an **env-var override**:
  `A_B_C` in `os.environ` wins over the dict (`helpers.py:343-366`). Results cached in
  `CACHED_CONFIG`.
- **Per-run config for programmatic use** — `research.backtest()` takes a *researcher-
  friendly* flat dict (`starting_balance`, `fee`, `type`, `exchange`, `futures_leverage`,
  `warm_up_candles`) and `_format_config()` reshapes it into Jesse's internal nested form
  before `set_config()` (`research/backtest.py:218-254`, called at :107). **Routes**
  (symbol/timeframe/strategy tuples) are passed *alongside* config, not inside it
  (`research/backtest.py:64-114`).
- Project layout is convention: cwd must contain `strategies/` and `storage/`
  (`helpers.py:1021`, `validate_cwd` :1273+). Each strategy is a Python class folder.

**Self-update:** none in-process. Purely `pip install -U jesse`; the live plugin is a
separate `install-live` step.

---

## 3) Jesse vs Lean — which fits QMX

| Dimension | Lean | Jesse | QMX fit |
|---|---|---|---|
| CLI shape | rich command tree, config-compiler per run | one `run` server; dashboard/MCP drive it | **Lean.** QMX is config-driven CLI; agents invoke commands. |
| Config source of truth | layered files → one **resolved artifact per run** | mutated process-global + `.env` | **Lean.** The resolved-artifact-per-run *is* the wind-tunnel run config + fingerprint substrate. |
| Precedence | explicit, code-enforced (flag > project > root > synth) | env-var > dict; ad-hoc per-mode | **Lean.** QMX needs deterministic, inspectable layering for Book+BMS. |
| Comment/format | JSON5-ish, comment-preserving edits | plain dict | Neutral; QMX will use a typed format, not hand-edited JSON5. |
| Run identity | prefix-tagged random id + saved config + output dir | none (dashboard tracks) | **Lean.** Maps to QMX LEDGER keys. |
| Concurrency safety | `safe_save` lock+atomic-move | global dict + `reset_config` (process-scoped, race-prone across threads) | **Lean.** Jesse's global-dict model is unsafe for 12-14 concurrent tasks in one process; QMX must isolate run config per task. |
| Self-update | pip warn (24h) + engine-image digest pull (7d) | pip only | **Lean's split**, but the operator wants `uv tool` + versioned package (see §4F). |
| Engine coupling | config mounted read-only into container | config injected into same process | **Lean's read-only mount** is the QMF-clean pattern: config is data the engine cannot mutate. |

**Verdict:** QMX takes **Lean's architecture wholesale in spirit** — CLI as config
compiler, deterministic layering, one resolved read-only artifact per run, stable run id —
and rejects Jesse's process-global mutable config (unsafe under concurrency, no per-run
artifact). QMX keeps one Jesse idea: the **researcher-friendly flat input** that a
formatter expands into the strict internal shape (agents author simple; the CLI compiles
to strict). And QMX keeps Jesse's clean split of **secrets/infra into `.env`-like layer**
separate from run semantics.

---

## 4) QMX spec draft (requirements — WHAT, not code design)

### 4A) The wind-tunnel invariant
- **R-CLI-1.** The engine (tunnel) MUST consume exactly one fully-resolved, immutable run
  config per task. The engine MUST NOT read layered sources or mutate config. Config is
  data handed in read-only. (Mirrors Lean's read-only mount; satisfies QMF "no third-party
  engine code" and separation of concerns.)
- **R-CLI-2.** Creating a **Book** or a **BMS** MUST *materialize* a config fragment. A Book
  version compiles to a **read-only config fragment**; likewise a BMS version. These
  fragments are the persistent, versioned tunnel definition. Editing a Book = producing a
  new versioned fragment, never mutating an existing one.

### 4B) Config layering for Book/BMS-as-config
- **R-CLI-3.** The **resolved run config** MUST be composed, in defined precedence, from:
  `Book fragment` ⊕ `BMS fragment` ⊕ `bot spec` ⊕ `data window` ⊕ `run variables (flags)`,
  over synthesized QMX defaults. Precedence (highest wins): run flags/variables > bot >
  BMS fragment > Book fragment > QMX defaults. (Mirrors Lean `config_defaults` guard
  `lean_config_manager.py:257-259` and flag-over-file ordering.)
- **R-CLI-4.** Layering MUST be deterministic and pure: same inputs → byte-identical
  resolved config. Every layer's contribution MUST be attributable (which layer set which
  key) for auditability.
- **R-CLI-5.** Fragments MUST be typed and validated at compile time; an unfittable
  Book/BMS combination MUST produce a **typed refusal** (QMF), not a partial config.
  "Test = can a bot fit the Book" is evaluated here: fit failure is a typed refusal with the
  offending constraint.
- **R-CLI-6.** Secrets and infra (credentials, data source endpoints, concurrency limits)
  MUST live in a **separate global layer** distinct from run semantics, and MUST NOT enter
  the resolved run config's fingerprint region (see 4D). (Lean credentials Storage;
  Jesse `.env`.)

### 4C) CLI command tree (draft)
Config-driven, agent-invokable, deterministic. Proposed top-level:
- `qmx init` — scaffold a workspace: root config, data dir, ledger dir. (Lean `init`.)
- `qmx book create|show|list|version` — author/compile Book fragments.
- `qmx bms create|show|list|version` — author/compile BMS fragments.
- `qmx bot create|show|list` — bot specs (the candidate fitted to a Book).
- `qmx backtest <bot> --book <v> --bms <v> --from <utc-ns> --to <utc-ns> [--var k=v]...`
  — resolve config, run, log during, save to ledger. (Lean `backtest`.)
- `qmx optimize ...` — sweep run variables; each trial = its own resolved config + ledger
  entry. (Lean `optimize`.)
- `qmx research ...` — interactive/notebook run against a resolved config.
- `qmx report <run-id>` — render a saved ledger entry. (Lean `report`.)
- `qmx data download|generate|status` — data window provisioning. (Lean `data`.)
- `qmx config get|set|list|unset` — global/secret layer only. (Lean `config`.)
- `qmx ledger list|show <id>|find` — query the run ledger by id / fingerprint.
- `qmx self update|version` — see 4F.
- **R-CLI-7.** Every command that runs the tunnel MUST declare its config/resource
  requirements declaratively (Lean's `requires_lean_config`/`requires_docker` pattern) and
  MUST refuse (typed) if prerequisites are absent.
- **R-CLI-8.** Shell autocomplete MUST be provided via the CLI framework's native
  completion (as Lean relies on Click). No bespoke completion engine.

### 4D) The resolved-run-config artifact → fingerprints & ledger
- **R-CLI-9.** For every run, the CLI MUST write the **resolved run config** to a stable,
  human-inspectable artifact in the run's output directory before the engine starts
  (Lean `lean_runner.py:316-318`). The artifact is the canonical record of "what was run."
- **R-CLI-10.** The CLI MUST compute a **run fingerprint** = a hash over the
  *semantic* region of the resolved config (Book fragment, BMS fragment, bot, data window,
  run variables, engine version) **excluding** secrets/infra and non-semantic fields
  (timestamps, container names). Identical semantics → identical fingerprint (enables
  dedupe/cache and reproducibility claims).
- **R-CLI-11.** Each run MUST get an immutable **run id** and a sidecar identity record
  (id, fingerprint, result label, container/worker name, timestamps in **UTC-ns**), stored
  so a run is retrievable by id and by fingerprint (Lean's prefix-tagged id +
  `output_config_manager`). Money fields in results MUST be **exact integer money** (QMF).
- **R-CLI-12.** Results MUST be **logged during** the run and **saved at completion** into
  the **LEDGER** with an unbiased pass/fail end result and a **result label carrying the
  world** (`live` / `replay` / `simulated`) per QMF. The ledger entry references the
  resolved-config artifact and the fingerprint.
- **R-CLI-13.** All config/ledger writes MUST be crash-safe and concurrency-safe under the
  target load of **12-14 concurrent tasks** (atomic temp-file + rename, per-run isolation —
  Lean `safe_save`, `storage.py:18-49`). No shared mutable global config across tasks
  (explicitly reject Jesse's `config.py` global-dict + `reset_config` model).

### 4E) Book/BMS fragment format
- **R-CLI-14.** Fragments MUST be a typed, machine-authored format (not hand-edited
  JSON5). Agents author Books/BMSs via CLI commands; the CLI is the only writer. Fragments
  are versioned and content-addressable (a fragment version = its hash).
- **R-CLI-15.** A researcher-friendly *input* shape MAY be accepted and expanded by the CLI
  into the strict internal fragment (Jesse `_format_config` pattern,
  `research/backtest.py:218-254`) — simple to author, strict once compiled.

### 4F) Self-update (npm-analog) — `uv tool` + versioned package
- **R-CLI-16.** The QMX CLI MUST be distributable and self-updatable as a **versioned
  package via `uv tool`** (`uv tool install qmx`, `uv tool upgrade qmx`) — the operator's
  npm-update analog, replacing Lean's `pip install --upgrade`.
- **R-CLI-17.** On invocation the CLI MUST perform a **throttled** outdated-check against
  the package index and, when newer, print the exact `uv tool upgrade` command — never
  auto-upgrading itself. Throttle ~24h; dev/local builds never warn (Lean
  `warn_if_cli_outdated`, 24h interval, `update_manager.py:43-75`, `constants.py:88`).
- **R-CLI-18.** The **engine/runtime image** (if containerized) MAY auto-update on a
  separate, slower cadence via digest comparison, with `--update`/`--no-update` overrides
  (Lean's 7-day digest pull, `update_manager.py:77-114`). CLI-package cadence and
  engine cadence MUST be independent clocks.
- **R-CLI-19.** Update checks MUST fail open (offline → silent no-op) and MUST NOT block or
  alter a run (Lean catches `ConnectionError` and returns).

### 4G) QMF binding summary
- Exact integer money in all resolved-config monetary fields and ledger results.
- UTC-ns for all timestamps (data window bounds, run id record, ledger).
- Typed refusals for: missing prerequisites, unfittable Book/BMS, invalid fragment,
  layering conflicts.
- Result labels carry world (`live`/`replay`/`simulated`).
- No third-party engine code ever; the tunnel consumes QMX-authored config only.

---

## 5) Open questions

1. **Fingerprint boundary.** Exactly which resolved-config fields are "semantic" vs
   "excluded" from the fingerprint? Engine version is in; container name is out — but is the
   *data provider identity* (vs the data itself) semantic? Needs a canonical field
   classification before R-CLI-10 is buildable.
2. **Book/BMS fragment ↔ engine schema coupling.** Lean's `lean.json` is a cleaned copy of
   the engine's own config schema, so the two evolve together. QMX's fragments are
   independent typed objects — what is the contract/versioning story when the QMX engine
   adds/renames a config key? (Fragment migration policy.)
3. **Per-task isolation mechanism.** Lean isolates via one container + one mounted config
   per run. QMX targets 12-14 concurrent tasks — is isolation process-per-task,
   container-per-task, or in-process-with-immutable-config-object? R-CLI-13 forbids shared
   mutable config but doesn't pick the isolation primitive.
4. **"Fit" semantics.** "Test = can a bot fit the Book" — is fit a pre-run static check
   (constraints satisfiable) or does it require a trial run? Determines whether R-CLI-5
   refusal happens at compile time or after a probe run.
5. **`uv tool` vs container runtime.** If QMX ships both a `uv tool` CLI and a container
   engine image (R-CLI-16/18), how does a pure `uv tool` install (no Docker) run the tunnel?
   Is the engine a Python in-process module (Jesse-style) or always containerized
   (Lean-style)? This decides whether R-CLI-18 even applies.
6. **Ledger storage substrate.** Lean uses per-run directories + JSON sidecars. Does QMX's
   LEDGER want the same filesystem-per-run model, or a single append-only store queried by
   id/fingerprint? Affects R-CLI-11/12 durability and concurrent-write design.
