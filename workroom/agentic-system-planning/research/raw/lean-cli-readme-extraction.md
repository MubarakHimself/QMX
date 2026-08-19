# RAW: Lean CLI README extraction (unreviewed straggler output)

Provenance: produced by a straggler child of a stopped research agent, completed 2026-08-18 after a pause order. Archived verbatim so the work isn't lost. Unreviewed raw input for the future Lean CLI borrowings step (parked — see map.md).

Source: QuantConnect/lean-cli README (master, ~Aug 2026, v1.0.228). Full docs live at lean.io; the README only contains the `--help` text of all commands.

## 1. Complete command list

**Auth / identity**
- `lean login` — log in with a QuantConnect account (`-u, --user-id`, `-t, --api-token`, `--show-secrets`); interactive prompt if not provided.
- `lean logout` — log out and remove stored credentials.
- `lean whoami` — display who is logged in.

**Init / scaffolding**
- `lean init` — scaffold a Lean configuration file and data directory (`--organization`, `-l, --language [python|csharp]`).

**Project management**
- `lean project-create` — create a new project containing starter code (`-l, --language [python|csharp]`).
- `lean create-project` — alias for `project-create`.
- `lean project-delete` — delete a project locally and in the cloud if it exists (by name or cloud id).
- `lean delete-project` — alias for `project-delete`.
- `lean library add` — add a custom library (NuGet / PyPI / Lean CLI library path) to a project (`--version`, `--no-local`).
- `lean library remove` — remove a custom library from a project (`--no-local`).
- `lean encrypt` / `lean decrypt` — encrypt/decrypt your local project using the specified key (`--key FILE`).

**Local backtest / research / optimize / report / logs**
- `lean backtest` — backtest a project locally using Docker.
- `lean optimize` — optimize a project's parameters locally using Docker (`--strategy [Grid Search|Euler Search]`, `--target`, `--target-direction [min|max]`, `--parameter <name min max step>`, `--constraint`, `--optimizer-config FILE`, `--estimate`, `--max-concurrent-backtests`).
- `lean research` — run a Jupyter Lab environment locally using Docker (`--port` default 8888, `--no-open`, `-d, --detach`).
- `lean report` — generate a report of a backtest (LEAN Report Creator in Docker; `--backtest-results`, `--live-results`, `--report-destination`, `--css`, `--html`, `--pdf`, `--overwrite`).
- `lean logs` — display the most recent backtest/live/optimization logs (`--backtest` default, `--live`, `--optimization`, `--project`).

**Local live trading (`lean live`)**
- `lean live deploy` — start live trading a project locally using Docker (interactive wizard unless `--environment`, `--brokerage`, or `--data-provider-live` given).
- `lean live stop` — stop an already running local live trading project.
- `lean live liquidate` — liquidate the given symbol from the latest deployment of the given project.
- `lean live command` — send a command (`--data` dict-string) to a local running live trading project.
- `lean live add-security` — add a security to the algorithm (`--ticker`, `--market`, `--security-type` required).
- `lean live submit-order` / `update-order` / `cancel-order` — manage orders on the running algorithm (`--order-id`, `--quantity`, `--limit-price`, `--stop-price`, `--tag`).

**Cloud (`lean cloud`)**
- `lean cloud backtest` — backtest a project in the cloud (`--name`, `--push`, `--open`, `--parameter`).
- `lean cloud optimize` — optimize in the cloud (`--target`, `--target-direction`, `--parameter`, `--constraint`, `--node [O2-8|O4-12|O8-16]`, `--parallel-nodes`, `--push`).
- `lean cloud pull` — pull projects from QuantConnect to local drive (`--project`, `--pull-bootcamp`, `--encrypt`, `--decrypt`, `--key`).
- `lean cloud push` — push local projects to QuantConnect (`--project`, `--encrypt`, `--decrypt`, `--key`, `--force`).
- `lean cloud status` — show the live trading status of a project in the cloud.
- `lean cloud live` — subcommands: `deploy` (wizard unless `--brokerage` given, then `--node`, `--auto-restart`, `--notify-order-events`, `--notify-insights` required), `stop`, `liquidate`, `command` (`--data`), `broadcast` (send command to all live projects in an organization; `--data` required, `--organization`, `--exclude-project`; newest addition in v1.0.228).

**Object store**
- Cloud: `lean cloud object-store get|set|list|ls|properties|delete` — organization cloud object store (`get` takes multiple keys + `--destination-folder`; `set KEY PATH`).
- Local: `lean object-store get|set|list|ls|properties|delete` — "Opens the local storage directory in the file explorer."

**Data**
- `lean data download` — purchase/download data from QuantConnect Datasets or supported providers (interactive wizard, or non-interactive with `--dataset`; `--data-type [Trade|Quote|Bulk|Universe|OpenInterest]`, `--resolution [Tick|Second|Minute|Hour|Daily]`, `--security-type`, `--market`, `--ticker`, `--start`/`--end` yyyyMMdd, `--overwrite`, `-y, --yes`, `--data-purchase-limit` in QCC).
- `lean data generate` — generate random market data (Brownian motion model; `--start` required, `--symbol-count`, `--tickers`, `--security-type`, `--resolution`, `--data-density [Dense|Sparse|VerySparse]`, `--random-seed`, splits/dividends/IPO percentages, option-chain options).

**Config**
- `lean config get|set|unset|list` — get / set / unset / list configurable CLI options.

**Custom images / private cloud / misc**
- `lean build` — build Docker images of your own version of LEAN from a local Lean repo checkout (`--tag`, defaults to latest).
- `lean private-cloud start` — start a new private cloud (`--master`/`--slave`, `--token`, `--master-domain, --master-ip`, `--master-port`, `--slave-domain, --slave-ip`, `--compute`, `--update`/`--no-update`, `--stop`).
- `lean private-cloud add-compute` — add private cloud compute (same connection flags).
- `lean private-cloud stop` — stops a running private cloud.

Common flags across commands: `--verbose`, `--help`, `--lean-config FILE`, `--image`, `--update`/`--no-update`, `-d, --detach`, `--extra-docker-config` (JSON passed to docker-py), `--release` (C# release build), `--python-venv`.

Prefix shortcuts: any unambiguous prefix runs the command (`lean clo back` → `lean cloud backtest`); ambiguous prefixes list options; README warns to use full names in scripts.

## 2. Configuration

- **CLI root directory**: `lean init` in an empty directory downloads "the latest configuration file and sample data" from QuantConnect/Lean; recommended to run all commands in that directory.
- **lean.json discovery**: commands take `--lean-config FILE` — "defaults to the nearest lean.json". Brokerage/provider flags update or fall back to the Lean config; for `lean live deploy`, if a required option is not given and cannot be found in the Lean config, the command aborts.
- **Global CLI options** (via `lean config set/get/unset/list`): `user-id`, `api-token`, `default-language`, `engine-image` (default `quantconnect/lean:latest`), `research-image` (default `quantconnect/research:latest`), `database-update-frequency` (DD.HH:MM:SS, default 1 day).
- **Credentials**: stored in `~/.lean/credentials`, removed on `lean logout`; `lean config get` refuses to print sensitive options.
- **Precedence**: command-line flag > nearest lean.json / stored config; per-command `--image` overrides configured images. No environment variables are mentioned in the README.

## 3. Local/cloud parity

- Two documented workflows: **cloud-focused** (`lean cloud pull` → edit → `lean cloud backtest "Project Name" --open --push` → `lean cloud push`) and **locally-focused** (`lean create-project` → `lean research` → `lean backtest`). "You're free to mix local and cloud features in any way you'd like."
- Local runs use Docker: `lean backtest` runs in a container "containing the same packages as the ones used on QuantConnect.com, but with your own data."
- Sync semantics: `cloud pull` overrides local file content but "will not delete local files"; `cloud push` overrides cloud files and "will delete cloud files which don't have a local counterpart" (`--force` for lock conflicts). `--push` on cloud backtest/optimize/live-deploy pushes local changes first.
- Images: defaults `quantconnect/lean:latest` / `quantconnect/research:latest`; override per-run with `--image` or globally via config. `--update` pulls latest before running; `--no-update` uses local.
- Custom LEAN: `lean build` compiles your own Lean repo into `lean-cli/foundation:latest`, `lean-cli/engine:latest`, `lean-cli/research:latest` and sets them as defaults; reuses `quantconnect/lean:foundation` when the foundation Dockerfile matches the official one.

## 4. Project scaffolding

- `lean init`: scaffolds config + sample data pulled from the QuantConnect/Lean repo.
- `lean project-create`: starter code (`main.py` / `Main.cs`); path segments auto-create subdirectories. Per-project `config.json` (e.g. `lean report` reads its description). Results land in `PROJECT/backtests/TIMESTAMP`, `PROJECT/live/TIMESTAMP`, `PROJECT/optimizations/TIMESTAMP`. Libraries: C# via `.csproj` (restored if `dotnet` on PATH), Python via `requirements.txt` installed locally for autocomplete (pins to latest compatible with Python 3.8, matching the Docker images). Local autocomplete is a listed highlight.

## 5. Architecture, development, distribution

- **Language/structure**: 100% Python. Commands live in `lean/commands/` mirroring the CLI tree (e.g. `lean/commands/cloud/live/broadcast.py`); each README section links "See code". Repo top level: `lean/`, `scripts/`, `tests/`, `setup.py`, `requirements.txt`, `pytest.ini`, `static_analysis.py`, `announcements.json`. Help format is Click-style.
- **Dev setup**: Python 3.7+, `pip install -r requirements.txt` (editable mode). Production deps in `setup.py`, dev deps in `requirements.txt`. Tests: `pytest` with filesystem and HTTP mocked. Build: `python setup.py sdist bdist_wheel`. README command reference is generated by `python scripts/readme.py`. CI runs mypy/flake8 (`static_analysis.py`); PyInstaller spec in `scripts/`.
- **Release/distribution**: `pip install --upgrade lean` (PyPI). Maintainers release by pushing a git tag → GitHub Actions publishes to PyPI. Docker required for many commands. License Apache-2.0; 154 releases, latest 1.0.228.
