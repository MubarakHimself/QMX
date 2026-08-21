# QuantConnect Lean CLI — Deep Study (backtesting research dossier)

Prepared for the QMX architecture sitting, 2026-08-19. Read-only study of an external reference tool. QMX is **build-our-own / no third-party engine** (memlog line 8); Lean is studied here as a **reference architecture** for the composition-via-config engine skeleton and the Docker-mount reproducibility model, not as an adoption candidate. Lean is Apache-2.0 (permissive), so its ideas are freely borrowable.

Two artifacts studied:
- **lean-cli** (the Python CLI/orchestrator) — shallow-cloned locally to scratchpad `.../scratchpad/lean-cli`. Cites below are `lean/...` paths in that clone.
- **QuantConnect/Lean** (the C# engine, huge — NOT cloned) — studied via web (github.com/QuantConnect/Lean and its `Launcher/config.json`).

---

## 0. Provenance, versions, license, runtime

- **lean-cli latest version: `1.0.228`, uploaded 2026-08-12T21:06:07** (PyPI `pypi.org/pypi/lean/json`, fetched via curl 2026-08-20). The cloned working tree self-reports `__version__ = "0.0.0-dev"` (`lean/__init__.py`) — that is the dev placeholder, not the release.
- **License: Apache-2.0 for BOTH repos.** lean-cli `LICENSE` = "Apache License Version 2.0"; every source file header repeats it (e.g. `lean/constants.py:4`). `setup.py` classifier `"License :: OSI Approved :: Apache Software License"`. Note: PyPI `info.license` field is `null`, but the classifier + LICENSE file are authoritative → Apache-2.0. Lean engine repo confirmed Apache-2.0 (github.com/QuantConnect/Lean, README + repo footer).
- **Runtime: `python_requires >= 3.9`** (`setup.py`); classifiers list 3.9–3.14. Distributed on PyPI as `lean`, console entry point `lean=lean.main:main` (`setup.py` `entry_points`).
- **Production dependencies** (`setup.py install_requires`): `click>=8.0.4`, `requests>=2.27.1`, `json5>=0.9.8`, `docker>=6.0.0`, `rich>=9.10.0`, `pydantic>=2.0.0`, `python-dateutil>=2.8.2`, `lxml>=4.9.0`, `joblib>=1.1.0`, `packaging`, `quantconnect-stubs`, `cryptography>=41.0.4`. So: Click for the command tree, the `docker` SDK to drive the engine container, Pydantic v2 for models, Rich for output, joblib for parallel local optimization.
- **The CLI is a thin orchestrator.** It contains NO backtesting/trading logic. Every compute command marshals a `lean.json`, mounts host directories into a Docker container running the C# LEAN engine image, and streams logs back. All financial computation lives in the container.

---

## 1. Full command surface

Command tree lives under `lean/commands/` (one file/subpackage per command). Registered in `lean/commands/__init__.py`; root group `lean/commands/lean.py`. README §"Commands" (lines ~89–147) is the canonical list. Groups and commands:

**Project lifecycle**
- `lean init` — scaffold a `lean.json` config file + `data/` directory for an organization; `-l/--language python|csharp` default language (`lean/commands/init.py`; README:1201).
- `lean create-project` (alias `project-create`) — new project from template (`create_project.py`).
- `lean delete-project` (alias `project-delete`).

**Local compute (all `requires_docker=True`)**
- `lean backtest PROJECT` — run one backtest locally in Docker (`backtest.py`). Key options: `--output` (defaults `PROJECT/backtests/TIMESTAMP`), `-d/--detach`, `--debug [pycharm|ptvsd|debugpy|vsdbg|rider|local-platform]`, `--data-provider-historical <provider>`, `--download-data` (alias for `--data-provider-historical QuantConnect`), `--data-purchase-limit`, `--release`, `--image` (default `quantconnect/lean:latest`), `--python-venv`, `--update` (pull image first), `--backtest-name`, `--extra-docker-config` (raw JSON), `--no-update`.
- `lean optimize PROJECT` — local parameter optimization; spins many backtests (`optimize.py`). Options: `--optimizer-config`, `--strategy`, `--target`/`--target-direction`, `--parameter "name min max step"` (repeatable), `--constraint "stat op value"`, `--estimate` (dry-run runtime), `--max-concurrent-backtests`, plus the same data-provider/image/detach flags.
- `lean research PROJECT` — launch a Jupyter Lab environment in the `quantconnect/research:latest` image (`research.py`). Options: `--port` (8888), `--data-provider-historical`, `--download-data`, `--detach`, `--no-open`, `--image`, `--update`, `--extra-docker-config`.
- `lean report` — run the LEAN Report Creator in Docker to turn a backtest results JSON into a polished HTML (optionally PDF) report (`report.py`). See §4.
- `lean build [ROOT]` — build custom local Docker images from Lean Dockerfiles (`build.py`). See §7.

**Data**
- `lean data download` — buy/download market data from the QuantConnect Data Library into the local `data/` folder (`data/download.py`).
- `lean data generate` — **random/synthetic data generator** (`data/generate.py`). See §6.

**Cloud (QuantConnect SaaS)**
- `lean cloud push` / `lean cloud pull` — sync projects local↔cloud (`cloud/push.py`, `cloud/pull.py`).
- `lean cloud backtest` / `lean cloud optimize` — run on QC's cloud nodes (`cloud/backtest.py`, `cloud/optimize.py`).
- `lean cloud status` (`cloud/status.py`).
- `lean cloud live deploy|stop|liquidate|command|broadcast` (`cloud/live/*`).
- `lean cloud object-store get|set|list|ls|delete|properties` (`cloud/object_store/*`).

**Local live trading**
- `lean live deploy|stop|liquidate|command|add-security|submit-order|update-order|cancel-order` (`live/*`). Deploys the engine against a real brokerage module.

**Object store (local)**
- `lean object-store get|set|list|ls|delete|properties` (`object_store/*`).

**Libraries**
- `lean library add` / `lean library remove` — attach a shared library project (Python or C#/NuGet) to a project (`library/*`). See §9.

**Config & auth**
- `lean config get|set|list|unset` (`config/*`) — read/write the **global** CLI config (`~/.lean/config`). E.g. `lean config set engine-image <image>`.
- `lean login` / `lean logout` — store/remove QC API credentials in `~/.lean/credentials` (`login.py`, `logout.py`).
- `lean whoami` (`whoami.py`).

**Security of project files**
- `lean encrypt` / `lean decrypt` — encrypt project source at rest with a key (`encrypt.py`, `decrypt.py`), using the `cryptography` dep.

**Diagnostics / misc**
- `lean logs` — show logs of the last/ detached container (`logs.py`).
- `lean gui` (`gui/`), `lean private-cloud start|stop|add-compute` (`private_cloud/*` — multi-node local compute cluster).

**Autocomplete**: shipped via Click's native shell completion (README:16 links docs/v2/lean-cli/projects/autocomplete). Not a bespoke command — the user registers Click's completion script for bash/zsh/etc.

---

## 2. The `lean.json` config model + precedence

Three-layer configuration:

1. **Global CLI config** — `~/.lean/config` (`constants.py:39 GENERAL_CONFIG_PATH`) and credentials `~/.lean/credentials` (`constants.py:42`). Managed by `lean config set/get` and `CliConfigManager` (`components/config/cli_config_manager.py`) over a `Storage` abstraction (`storage.py`). Holds cross-project defaults: `engine-image`, `research-image`, `user-id`, `api-token`, default language, organization. `get_engine_image(override)` resolves precedence: explicit `--image` override → global config `engine-image` → `DEFAULT_ENGINE_IMAGE` (`cli_config_manager.py:93`).

2. **The Lean config `lean.json`** — the per-workspace engine config, default filename `lean.json` (`constants.py:57 DEFAULT_LEAN_CONFIG_FILE_NAME`), created by `lean init` alongside the `data/` folder (`constants.py:60`). Found by walking up from cwd (`lean_config_manager.py:53-84`, raises if none found → defines the "CLI root directory" `get_cli_root_directory()`). It is a JSON5 file (comments allowed) storing the engine's runtime knobs: `data-folder`, `environment`, all the pluggable-handler keys (§8), brokerage/data-provider settings, `job-user-id`/`api-access-token`, etc. `LeanConfigManager` (`components/config/lean_config_manager.py`) reads it, and `get_complete_lean_config(environment, algorithm_file, debugging_method)` (line 212) **synthesizes the final config actually handed to the engine**: it injects `data-folder=/Lean/Data`, `results-destination-folder=/Results`, `object-store-root=/Storage`, debugging flags, `algorithm-type-name`/`algorithm-language`/`algorithm-location`, `parameters` (from project config), `python-additional-paths` (library refs), and defaults for `job-organization-id`, `storage-limit-mb`, IB/IQFeed hosts — **only where the user has not already set them** (`config_defaults` loop, line 257: `if config.get(key,"")=="" `). `clean_lean_config()` (line 158) strips these back out when writing a human-facing file. Precedence rule: **user-set keys in `lean.json` always win; the CLI only fills gaps.**

3. **Per-project config `config.json`** — `constants.py:63 PROJECT_CONFIG_FILE_NAME="config.json"`, one per project directory, managed by `ProjectConfigManager` (`components/config/project_config_manager.py`). Holds `algorithm-language`, `parameters`, `libraries` (library references), `local-id`, `cloud-id` (cloud-id if pushed, else `-local-id`), `description`, and a `docker` sub-object for per-project Docker overrides (`lean_runner.py:203 docker_project_config = project_config.get("docker", {})`). This is how a single project overrides image/mounts for itself.

Net precedence for a run: **CLI flag (`--image`, `--data-provider-historical`, …) > project `config.json` docker/keys > `lean.json` explicit keys > CLI-synthesized defaults > hardcoded `constants.py` defaults.**

---

## 3. How a local backtest works (engine-in-container, mounts, reproducibility)

Mechanics in `lean/components/docker/lean_runner.py` + `docker_manager.py`:

- The CLI **never runs financial code in-process.** It builds a `run_options` dict and starts a container from the engine image (`quantconnect/lean:latest` by default, `constants.py:66`) on a dedicated docker network `lean_cli` (`constants.py:97`). The engine binary lives at `/Lean/Launcher/bin/Debug` in the image (`LEAN_ROOT_PATH`, `constants.py:36`).
- **Volume/bind mounts** (`lean_runner.py:376-431` `_mount_common_directories`, and `_mount_lean_config_and_finalize` :304):
  - Data folder → `/Lean/Data` (rw) — `volumes[data_dir] = {bind:/Lean/Data, mode:rw}` (:404).
  - Output dir → `/Results` (rw) (:408). Local object store → `/Storage` (rw) (:410).
  - The project source is mounted at `/LeanCLI` (compilation step keys off `if [ -d '/LeanCLI' ]`, :492); libraries mount alongside.
  - The **synthesized `lean.json` is written to a temp file and bind-mounted read-only** at `/Lean/Launcher/bin/Debug/config.json` (:316-324). This is the single source of truth handed to the engine each run.
  - Modules (brokerages/data providers) mount from `~/.lean/modules` → `/Modules` (ro) then copied to the launcher dir (:344-371).
  - Arbitrary extra files referenced in config mount under `/Files/<key>` (:414-431).
- **Reproducibility implication (relevant to QMX deterministic fingerprints, memlog:16):** the engine version is pinned by the **image tag**, not by the CLI. Default `:latest` floats; a container is only reproducible if you pin a digest/tag (`--image quantconnect/lean:<tag>` or `lean config set engine-image`). The CLI checks for image updates weekly (`UPDATE_CHECK_INTERVAL_DOCKER_IMAGE = 24*7`, `constants.py:91`) and can `--update`/`--no-update`. Data comes from the host `data/` folder mounted rw, so a run's inputs are whatever is on disk. **Determinism therefore rests on (a) pinned image digest, (b) frozen data folder, (c) the exact synthesized config JSON** — the CLI makes all three explicit and inspectable, which is the borrowable pattern.
- Python custom-dependency handling: user site-packages are cached in a docker volume (up to `SITE_PACKAGES_VOLUME_LIMIT=10`, `constants.py:75`) keyed to the requirements, so repeat backtests skip reinstall.

---

## 4. The `report` command (backtest JSON → HTML)

`lean/commands/report.py`. Input is a backtest **results JSON** (`--backtest-data-source-file` / `--live-data-source-file`); output an HTML file (`--report-destination`, default `./report.html`), optional `--pdf`, `--css`/`--html` overrides, `--strategy-name/-version/-description`, `--overwrite`.

Mechanics: it writes a small **report config** (`report_config`, :160-195) that itself is a full LEAN environment named `report` with its own handler set — `setup-handler=ConsoleSetupHandler`, `result-handler=BacktestingResultHandler`, `data-feed-handler=FileSystemDataFeed`, `real-time-handler=BacktestingRealTimeHandler`, `history-provider=SubscriptionDataReaderHistoryProvider`, `transaction-handler=BacktestingTransactionHandler` (:187-193). It bind-mounts this config + the backtest JSON into `/Lean/Report/bin/Debug/`, mounts `data/`→`/Lean/Data` and the destination dir→`/Output`, then runs `dotnet QuantConnect.Report.dll` in the container and `cp`s `/tmp/report.html` (or `.pdf`) to `/Output` (:208-254). So the report generator is **the same engine, a different environment + entry assembly** — the clearest illustration of the config-driven composition model (§8).

---

## 5. Data folder model (map files, market-hours db)

- The `data/` folder (default name `constants.py:60`) is the on-disk market-data root, scaffolded by `lean init`, mounted rw at `/Lean/Data`.
- **Map files / factor files**: symbol-remapping (ticker changes) and split/dividend factor files. The engine's default providers are `LocalDiskMapFileProvider` and `LocalDiskFactorFileProvider` (Lean `Launcher/config.json`; also hardcoded in the report config `report.py:177-178`). `lean_runner._handle_data_providers` forces LocalDisk map/factor providers when no recent zip is present and the API data provider isn't in use (`lean_runner.py:206-207` comment).
- **Market hours database**: `components/util/market_hours_database.py` — the CLI reads the market-hours DB (trading calendars/sessions per market+security type) from the data folder to validate/inform commands (e.g. live security addition, data generation markets).
- Data is organized by security-type / market / resolution / ticker as zip archives; `lean data download` populates it from the QC Data Library (metered by `--data-purchase-limit` in QCC when using the QC API data provider, `lean_config_manager.py:296`).

---

## 6. Random / synthetic data generator (`lean data generate`)

`lean/commands/data/generate.py` — runs LEAN's in-engine **RandomDataGenerator** in the engine image ("random data generator in LEAN to generate realistic market data using a Brownian motion model", :139). It writes generated zips into the local `data/` folder so subsequent backtests can consume them. Options: `--start`/`--end` (yyyyMMdd), `--symbol-count`, `--tickers`, `--security-type` (default Equity), `--resolution` (default Minute), `--data-density` (default Dense), `--include-coarse`, `--market`, `--quote-trade-ratio`, `--random-seed` (for reproducible synthetic sets), and equity corporate-action probabilities: `--ipo-percentage`, `--rename-percentage`, `--splits-percentage`, `--dividends-percentage`, `--dividend-every-quarter-percentage`; options chains: `--option-price-engine`, `--volatility-model-resolution`, `--chain-symbol-count`; plus `--image`/`--update`. Relevant to QMX: `--random-seed` is the reproducibility hook for synthetic test data — a pattern QMX would want for deterministic fixtures.

---

## 7. `lean build` — custom Docker images

`lean/commands/build.py`. Builds a local custom image stack from Lean's Dockerfiles (README:284-310):
1. `lean-cli/foundation:latest` from `Lean/DockerfileLeanFoundation(ARM)` — but if the foundation Dockerfile matches the official one, it reuses `quantconnect/lean:foundation` instead of rebuilding (:306).
2. `lean-cli/engine:latest` from `Lean/Dockerfile` on the foundation base.
3. `lean-cli/research:latest` from `Lean/DockerfileJupyter` on the engine base.
`--tag` sets the tag (default `latest`). Custom-image names are constants `CUSTOM_FOUNDATION/ENGINE/RESEARCH` (`constants.py:20-22`). This is how a user injects their own C# handlers/data providers into the engine and then points `--image` / `engine-image` at the custom build — the extension path.

**Modules/plugins**: brokerages, data providers, history providers, data-queue handlers, addon modules are "modules" (`constants.py:105-118`: types `brokerage`, `data-downloader`, `history-provider`, `data-queue-handler`, `addon-module`, `compute`; platforms `cli`/`cloud`). Stored in `~/.lean/modules` (`constants.py:48`), fetched via `ModuleManager` / `module_client`, mounted into the container and selected by config keys. This is the plugin marketplace layer on top of the config-driven handler selection.

---

## 8. The LEAN engine skeleton — composition-over-inheritance via config.json

This is the load-bearing architectural lesson (from Lean `Launcher/config.json` + report.py mirror). The engine is a fixed pipeline whose every stage is an **interface bound to a concrete class name in the config JSON**, resolved by reflection at startup. README (github.com/QuantConnect/Lean): *"LEAN is modular in design, with each component pluggable and customizable. It ships with models for all major plug-in points."*

Handler slots (assembly-qualified class names in config):

| Config key | Interface | Backtest default | Live default |
|---|---|---|---|
| `setup-handler` | ISetupHandler | `BacktestingSetupHandler` | `BrokerageSetupHandler` (report: `ConsoleSetupHandler`) |
| `data-feed-handler` | IDataFeed | `FileSystemDataFeed` | `LiveTradingDataFeed` |
| `real-time-handler` | IRealTimeHandler | `BacktestingRealTimeHandler` | `LiveTradingRealTimeHandler` |
| `transaction-handler` | ITransactionHandler | `BacktestingTransactionHandler` | `BrokerageTransactionHandler` |
| `result-handler` | IResultHandler | `BacktestingResultHandler` | `LiveTradingResultHandler` |
| `history-provider` | IHistoryProvider | `SubscriptionDataReaderHistoryProvider` | `BrokerageHistoryProvider`→`SubscriptionDataReader…` fallback |
| `data-provider` | IDataProvider | `DefaultDataProvider` | (module-specific) |
| `map-file-provider` | IMapFileProvider | `LocalDiskMapFileProvider` | same |
| `factor-file-provider` | IFactorFileProvider | `LocalDiskFactorFileProvider` | same |
| `object-store` | IObjectStore | `LocalObjectStore` | same |
| `data-channel-provider` | IDataChannelProvider | `DataChannelProvider` | same |
| `data-aggregator` | IDataAggregator | `AggregationManager` | same |
| `messaging-handler` | IMessagingHandler | `Messaging` | same |
| `job-queue-handler` | IJobQueueHandler | `JobQueue` | same |
| `api-handler` | IApi | `Api` | same |
| `log-handler` | ILogHandler | `CompositeLogHandler` | same |
| (brokerage) | IBrokerage | n/a | e.g. `InteractiveBrokersBrokerage`, `AlpacaBrokerage` |
| (algorithm) | IAlgorithm | user's `QCAlgorithm` subclass | same |

`environment` selects a named block under `environments`; each environment overrides the subset of handlers that differ (backtest vs live vs report). **Same engine binary, different behavior purely from config.** Backtest = FileSystemDataFeed + Backtesting{Setup,RealTime,Transaction,Result} handlers; live swaps in LiveTrading*/Brokerage* handlers + a real IBrokerage; report swaps in ConsoleSetupHandler and the Report assembly. This is the reference model for QMX's own "small core, wide seams" (memlog:14) — a contracts/seams layer where the runtime is assembled from interchangeable providers named in config, keeping the core definitions-only (DEC-0022).

---

## 9. Library projects + cloud↔local sync

- **Libraries**: `lean library add PROJECT LIBRARY` attaches a shared code library. Python libraries are referenced via `python-additional-paths` injected into the engine config (`lean_config_manager.py:281-286`) and also `pip install -e`'d into the local venv for autocomplete (README:1242, skippable with `--no-local`). C# libraries are NuGet or local project references (`get_csharp_libraries`, `project_config_manager.py:117`). Library refs are stored under `libraries` in the project `config.json`.
- **Cloud↔local sync**: `lean cloud push`/`pull` (managed by `PushManager`/`PullManager`, `CloudProjectManager` in `components/cloud/`) mirror projects between the local filesystem and the QC web IDE. Identity is the `cloud-id`/`local-id` pair in each project's `config.json` (`project_config_manager.py:80-93`: cloud-id if pushed, else negative local-id). `lean cloud backtest/optimize/live` then execute on QC's nodes via the REST API clients in `components/api/`. So the CLI is a full local mirror of the SaaS with a bidirectional file sync keyed on stable project ids.

---

## 10. Takeaways for QMX architecture

- **Config-driven composition is the whole engine.** Lean proves you can build a backtest/live/report system as one pipeline whose stages are interfaces named in a JSON config and resolved by reflection. QMX's "contracts/seams only in the framework, runtime in the node" (memlog:13-14) is the same idea; Lean is a concrete, battle-tested exemplar of the seam list (setup/datafeed/realtime/transaction/result/history/brokerage/dataprovider/objectstore).
- **Reproducibility = pin the image digest + freeze the data folder + capture the exact synthesized config.** Lean makes all three explicit; `:latest` defaults are the trap. For QMX deterministic fingerprints, the borrowable rule is: fingerprint must cover engine version, input dataset, and the fully-resolved config, not the human-facing sparse config.
- **Thin Python orchestrator over a container** cleanly separates the CLI (Click, Pydantic v2, docker SDK) from compute — a viable shape for a QMX runner without putting compute in the core.
- **`--random-seed` on synthetic data** is the pattern for deterministic test fixtures.
- **Licensing**: both repos Apache-2.0 — ideas and even code are borrowable under QMX's "LGPL/permissive deps ok" constraint (memlog:8), though QMX's build-our-own rule forbids adopting the engine wholesale.

### Not verified / gaps
- Exact `lean.json` full key schema not enumerated field-by-field here (studied via the manager's synthesis logic, not a published schema). ABSENT: an authoritative JSON-schema for `lean.json`.
- The C# interface definitions (`ISetupHandler` etc.) were confirmed by their config bindings and README, not by reading the engine source (repo not cloned — too large). Interface names are standard LEAN nomenclature; concrete class names are quoted verbatim from `Launcher/config.json` and `report.py`.
