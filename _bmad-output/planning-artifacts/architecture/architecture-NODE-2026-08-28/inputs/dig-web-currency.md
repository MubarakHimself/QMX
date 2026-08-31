# dig-web-currency — Web-Verification Seat (Node Spine)

Seat: web-verification. Date of run: 2026-08-28. All citations are PRIMARY-source
URLs (vendor docs, official repos, PyPI JSON metadata, official release pages)
unless the grade column says otherwise. Where a fact is load-bearing for the
node spine, the exact source wording is quoted. No credential was read, printed,
or copied during this run.

Evidence grades:
- **PRIMARY** — vendor/official documentation, official repo, PyPI JSON
  metadata, or official release/announcement page.
- **SECONDARY** — reputable third-party (mailing-list archive, distro tracker,
  official community forum answered by a vendor moderator, established review
  site) that is not the canonical vendor page.
- **UNVERIFIED** — could not confirm from a trustworthy source; absence of
  evidence.

---

## GRADED SUMMARY TABLE

| # | Fact the spine will pin | Value verified | Primary URL | Page/release date | Grade |
|---|---|---|---|---|---|
| 1a | Official Spotware Python SDK name | `ctrader-open-api` (a.k.a. OpenApiPy) | https://pypi.org/project/ctrader-open-api/ | 0.9.2 uploaded 2024-06-26 | PRIMARY |
| 1b | Current version on PyPI | **0.9.2** (0.9.3 was released 2024-08-06 then **yanked**, so 0.9.2 is the installable latest) | https://pypi.org/pypi/ctrader-open-api/json | 2024-06-26 | PRIMARY |
| 1c | Transport / async framework | **Twisted** (returns Twisted Deferreds; callback-based, NOT asyncio) | https://spotware.github.io/OpenApiPy/ | n/a (docs) | PRIMARY |
| 1d | Hard-pinned dependencies of 0.9.2 | `Twisted==24.3.0`, `pyOpenSSL==24.1.0`, **`protobuf==3.20.1`**, `requests==2.32.3`, `inputimeout==1.0.4` (all exact `==` pins) | https://pypi.org/pypi/ctrader-open-api/json | 2024-06-26 | PRIMARY |
| 1e | requires_python of 0.9.2 | `<4.0,>=3.8` | https://pypi.org/pypi/ctrader-open-api/json | 2024-06-26 | PRIMARY |
| 1f | Maintained asyncio-native community client | **None verified.** Official SDK is Twisted-only. `ctrader-sdk` (0.1.1, 2024-05-25, maintainer Nils Lopez) has 2 same-day releases and no updates since → not a maintained asyncio client. | https://pypi.org/project/ctrader-sdk/ | 2024-05-25 | UNVERIFIED (no maintained asyncio client found) |
| 1g | Rate limit — non-historical | **50 requests/sec per connection** | https://help.ctrader.com/open-api/ | n/a (docs) | PRIMARY |
| 1h | Rate limit — historical data | **5 requests/sec per connection** | https://help.ctrader.com/open-api/ | n/a (docs) | PRIMARY |
| 1i | Heartbeat requirement | Send a heartbeat **at least once every 10 seconds** or be disconnected | https://help.ctrader.com/open-api/faq/ | n/a (docs) | PRIMARY |
| 1j | Demo host / port | `demo.ctraderapi.com:5035` (Protobuf), `:5036` (JSON) | https://help.ctrader.com/open-api/proxies-endpoints/ | n/a (docs) | PRIMARY |
| 1k | Live host / port | `live.ctraderapi.com:5035` (Protobuf), `:5036` (JSON) | https://help.ctrader.com/open-api/proxies-endpoints/ | n/a (docs) | PRIMARY |
| 1l | TCP transport security | **TCP client connection must use SSL** | https://help.ctrader.com/open-api/connection/ | n/a (docs) | PRIMARY |
| 1m | Access-token lifetime | **2,628,000 seconds (~30 days)**; default `expiresIn` = `2628000` | https://help.ctrader.com/open-api/account-authentication/ | n/a (docs) | PRIMARY |
| 1n | Refresh-token lifetime | **No expiration**; valid until used to refresh, or until re-authorisation | https://help.ctrader.com/open-api/account-authentication/ | n/a (docs) | PRIMARY |
| 2 | Trendbar price basis (ProtoOATrendbar / ProtoOAGetTrendbarsReq) | **BID prices.** "It is not possible to get trendbars based on ask prices." No official *docs page* states the basis; confirmed by Spotware moderator on the official forum. | https://community.ctrader.com/forum/connect-api-support/41268/ | forum thread (Spotware moderator answer) | SECONDARY (vendor moderator, not a docs page) |
| 3a | Current Ubuntu LTS (Aug 2026) | **26.04 LTS "Resolute Raccoon", released 2026-04-23** — it IS out | https://documentation.ubuntu.com/release-notes/26.04/ | 2026-04-23 | PRIMARY |
| 3b | systemd in 26.04 | **259** | https://documentation.ubuntu.com/release-notes/26.04/ (version confirmed via LinuxConfig/Cherry Servers previews) | 2026-04-23 | PRIMARY (release) / SECONDARY (exact 259) |
| 3c | systemd in 24.04 LTS "Noble" | **255.4** (`255.4-1ubuntu8`) | https://launchpad.net/ubuntu/noble/amd64/systemd/255.4-1ubuntu8 | 24.04 archive | PRIMARY |
| 3d | systemd-creds / LoadCredentialEncrypted / TPM2 | Encrypted+authenticated credentials added in **systemd v250**; `LoadCredentialEncrypted=` + TPM2 sealing available. Both 24.04 (255) and 26.04 (259) are **≥ 254**, so fully available. | https://systemd.io/CREDENTIALS/ | n/a (docs) | PRIMARY |
| 3e | Python 3.14 via uv-managed python on Ubuntu | Available. `uv python install 3.14` pulls from python-build-standalone. Python 3.14.0 final released 2025-10-07. | https://docs.astral.sh/uv/concepts/python-versions/ ; https://www.python.org/downloads/release/python-3140/ | 3.14.0 = 2025-10-07 | PRIMARY |
| 4a | chrony current version | **4.7** released 2025-06-12; **4.8** stable, 4.9-pre1 in pre-release | https://www.mail-archive.com/chrony-users@chrony.tuxfamily.org/msg03819.html ; https://chrony-project.org/download.html | 4.7 = 2025-06-12 | PRIMARY (4.7 announce) / SECONDARY (4.8 latest) |
| 4b | Ubuntu default time-sync daemon | **chrony is default since Ubuntu 25.10** (so 26.04 ships chrony by default). 24.04 and earlier default to **systemd-timesyncd**. | https://ubuntu.com/server/docs/explanation/networking/about-time-synchronisation/ | n/a (docs) | PRIMARY |
| 5a | prometheus_client (a.k.a. prometheus-client) | **0.26.0**, released 2026-07-24; classifiers list Python 3.9–**3.14** | https://pypi.org/project/prometheus-client/ | 2026-07-24 | PRIMARY |
| 5b | opentelemetry-sdk | **1.44.0**, released 2026-07-16; supports Python 3.10–**3.14** | https://pypi.org/project/opentelemetry-sdk/ | 2026-07-16 | PRIMARY |
| 5c | opentelemetry exporter (otlp) | Versioned in lockstep with the SDK (1.44.0 line); Python 3.14 tracked upstream | https://pypi.org/project/opentelemetry-sdk/ ; https://github.com/open-telemetry/opentelemetry-python/issues/4789 | 2026-07-16 | PRIMARY (SDK) / SECONDARY (exporter-otlp exact) |
| 5d | structlog | **26.1.0**, released 2026-06-06; supports Python 3.10–3.15 (incl. **3.14**) | https://pypi.org/project/structlog/ | 2026-06-06 | PRIMARY |
| 6a | keyring current version | **25.7.0**, released 2025-11-16 | https://pypi.org/project/keyring/ | 2025-11-16 | PRIMARY |
| 6b | keyring Windows backend | Class **`WinVaultKeyring`** (module `keyring.backends.Windows`), a.k.a. "Windows Credential Locker"; requires pywin32; uses `CRED_TYPE_GENERIC` | https://raw.githubusercontent.com/jaraco/keyring/main/keyring/backends/Windows.py | n/a (repo main) | PRIMARY |
| 6c | Read a UI-stored generic credential from Python? | **Yes, if target-name matches.** keyring stores under target = `service`; on username collision it moves the entry to compound `{username}@{service}`. Reads via `win32cred.CredRead(Type=CRED_TYPE_GENERIC, TargetName=target)`, which returns any matching generic credential regardless of how it was created. | https://raw.githubusercontent.com/jaraco/keyring/main/keyring/backends/Windows.py | n/a (repo main) | PRIMARY |
| 7 | Skylos scans IaC? | **Yes (partial).** Skylos scans Dockerfile, docker-compose, **systemd `*.service` units**, Kubernetes YAML bundles, GitHub Actions, GitLab CI — but **NOT Terraform** (not in its file list). Skylos is a dead-code + secrets + security + IaC-misconfig PR scanner, not a pure "security scanner." | https://github.com/duriantaco/skylos/blob/main/README.md ; https://github.com/duriantaco/skylos | n/a (repo main) | PRIMARY |
| 8a | IC Markets swap-free admin/holding fee | Flat-rate holding fee on positions held overnight; **grace period up to five grace days** (triple-swap night = 3 grace days); some instruments (XNGUSD/XTIUSD/XBRUSD) charge from Day 1, USDJPY/GBPJPY from Day 3. Available on MT4/MT5/**cTrader**. Schedule is per-instrument. | https://ic.com/en/trading-accounts/islamic-account (301 from icmarkets.com) | n/a (broker page) | PRIMARY (grade only; exact schedule to operator separately) |
| 8b | Open API on demo AND live for IC Markets | **Yes.** Spotware Open API is broker-wide: "by default, it is supported by all trading accounts of any cTrader-affiliated brokers." IC Markets is cTrader-affiliated. Demo and live both usable (separate connections). | https://help.ctrader.com/open-api/ | n/a (docs) | PRIMARY |
| 9a | uv current version | **0.12.1**, released 2026-08-25 | https://github.com/astral-sh/uv/releases | 2026-08-25 | PRIMARY (release) / SECONDARY (exact 0.12.1) |
| 9b | uv recommended deployment pattern | For a service in a Docker/production image, docs recommend **`uv sync --locked`** (asserts lockfile is current); `--frozen` used only for the dependency-only layer before the full project is copied. `uv tool install` is for CLI tools, not a long-running service. | https://docs.astral.sh/uv/guides/integration/docker/ | n/a (docs) | PRIMARY |
| 9c | uv console_scripts / single-app dist | Docs show running an app entry point via `CMD ["uv", "run", "my_app"]`; no dedicated single-file-distribution feature. Entry points come from the project's `[project.scripts]`. | https://docs.astral.sh/uv/guides/integration/docker/ | n/a (docs) | PRIMARY |
| 10 | Demo-vs-live separation requires two connections | **Yes, explicit.** "Demo and live environments are fully separated… you would need to establish and maintain two separate connections." "At most, you should create two connections: one for demo accounts and one for live accounts." | https://help.ctrader.com/open-api/proxies-endpoints/ ; https://help.ctrader.com/open-api/connection/ | n/a (docs) | PRIMARY |

---

## ITEM-BY-ITEM DETAIL WITH LOAD-BEARING QUOTES

### 1. Spotware cTrader Open API — Python SDK, transport, limits, hosts, tokens

**SDK identity & version.** The official Spotware Python package is published on
PyPI as `ctrader-open-api` (import name `ctrader_open_api`; project name
"OpenApiPy"). PyPI JSON metadata gives `info.version = 0.9.2`, uploaded
2024-06-26. A 0.9.3 was uploaded 2024-08-06 but **yanked**, so pip resolves
0.9.2 as the installable latest.
- https://pypi.org/pypi/ctrader-open-api/json
- https://pypi.org/project/ctrader-open-api/
- https://github.com/spotware/OpenApiPy

**Transport = Twisted (NOT asyncio).** The SDK docs state it "works
asynchronously by using Twisted" and "methods return Twisted deferreds."
Message serialization is Protocol Buffers.
- https://spotware.github.io/OpenApiPy/

**Hard dependency pins (SPINE-CRITICAL).** From PyPI JSON `requires_dist` of
0.9.2, every dependency is an exact `==` pin:
- `Twisted==24.3.0`
- `pyOpenSSL==24.1.0`
- **`protobuf==3.20.1`**
- `requests==2.32.3`
- `inputimeout==1.0.4`
`requires_python = <4.0,>=3.8`.
- https://pypi.org/pypi/ctrader-open-api/json
- (Same pins confirmed in the repo source: https://raw.githubusercontent.com/spotware/OpenApiPy/main/pyproject.toml — note the repo `pyproject.toml` carries a placeholder `version = "0.0.0"`, but the dependency pins match the published wheel.)

> **RED FLAG for the spine:** `protobuf==3.20.1` (released April 2022) is an
> exact pin. The current protobuf is **7.36.0** (requires Python ≥3.10, ships
> cp314 wheels). protobuf 3.20.1 predates Python 3.14 and has **no cp314
> wheels** — it will not install/run cleanly on Python 3.14. A node targeting
> Python 3.14 cannot honor the SDK's `protobuf==3.20.1` pin without either (a)
> isolating the cTrader order-path process in its own venv on an older Python,
> (b) relaxing/repackaging the pin (SDK ships pre-compiled `_pb2` modules
> generated against 3.20.1 — regenerating against modern protobuf is possible
> but is product work, out of scope here), or (c) vendoring. This is the single
> largest currency-conflict the node spine must resolve.
> - protobuf latest: https://pypi.org/pypi/protobuf/json (7.36.0, requires_python ≥3.10, lists 3.14 classifier)

**Rate limits (PRIMARY, Getting Started page).**
> "You can perform a maximum of 50 requests per second per connection for any
> non-historical data requests." / "…a maximum of 5 requests per second per
> connection for any historical data requests."
- https://help.ctrader.com/open-api/

**Heartbeat (PRIMARY, FAQ).**
> "make sure that you send a heartbeat to the server at least once every 10
> seconds."
- https://help.ctrader.com/open-api/faq/

**Hosts / ports (PRIMARY, Proxies and endpoints).**
- Live: `live.ctraderapi.com:5035` (Protobuf), `:5036` (JSON)
- Demo: `demo.ctraderapi.com:5035` (Protobuf), `:5036` (JSON)
- The SDK constants are `EndPoints.PROTOBUF_DEMO_HOST` / `EndPoints.PROTOBUF_LIVE_HOST` / `EndPoints.PROTOBUF_PORT`.
- https://help.ctrader.com/open-api/proxies-endpoints/

**TCP requires SSL (PRIMARY, Establish a connection).**
> "The TCP client connection must use SSL, otherwise you will not be able to
> connect or interact with the API."
- https://help.ctrader.com/open-api/connection/

**Token lifetimes (PRIMARY, Account authentication).**
> "The expiration period of an access token is 2,628,000 seconds (approximately
> 30 days)." (default `expiresIn` = `2628000`)
> "The refresh token does not have an expiration period." (FAQ adds: "valid
> forever until you use it to refresh an access token or if you re-authorise
> your cTrader ID.")
- https://help.ctrader.com/open-api/account-authentication/
- https://help.ctrader.com/open-api/faq/

**Asyncio-native community client — not verified.** The official SDK is Twisted.
No actively-maintained asyncio-native Python client for cTrader Open API was
found. `ctrader-sdk` (0.1.1, 2024-05-25, maintainer Nils Lopez) has only two
same-day releases and no subsequent activity — cannot be recommended as a
maintained asyncio path. Graded **UNVERIFIED** (i.e., could not confirm a
maintained asyncio client exists).
- https://pypi.org/project/ctrader-sdk/

### 2. TRENDBARS — bid, ask, or mid?

No official Open API *documentation page* (Getting Started, symbol-data,
model-messages, ProtoOAGetTrendbarsReq reference) states the price basis of
`ProtoOATrendbar` bars. The definitive statement is a Spotware **moderator**
answer on the official community forum: trendbars are built from **bid** prices,
and it is **not possible** to obtain ask-based trendbars.
> Spotware moderator (PanagiotisChar): "It is not possible to get trendbars
> based on ask prices. If you need to backtest, you should base your backtesting
> on tick data instead." (thread confirms the OP's observation that "the prices
> are based on the bid prices")
- https://community.ctrader.com/forum/connect-api-support/41268/

This is consistent with cTrader charts being **bid-based by default**. Graded
**SECONDARY** honestly: the source is a vendor moderator on the official forum,
not a canonical docs page. The spine should record the basis as **BID** with the
caveat that Spotware has not documented it on a docs page, and that spread/ask
reconstruction for backtests requires tick data (`ProtoOASubscribeSpotsReq` for
live bid/ask; `ProtoOAGetTickDataReq` for historical ticks).

### 3. Ubuntu LTS, systemd, systemd-creds, Python 3.14

- **26.04 LTS "Resolute Raccoon" is released** — 2026-04-23 (official release
  notes). It ships **systemd 259** (release-notes overview + LinuxConfig/Cherry
  Servers previews for the exact number; 259 removes cgroup v1 support).
  - https://documentation.ubuntu.com/release-notes/26.04/
- **24.04 LTS "Noble"** ships **systemd 255.4** (`255.4-1ubuntu8`, Launchpad).
  - https://launchpad.net/ubuntu/noble/amd64/systemd/255.4-1ubuntu8
- **systemd-creds / encrypted credentials.** Encrypted+authenticated service
  credentials were introduced in **systemd v250**; `LoadCredentialEncrypted=` /
  `SetCredentialEncrypted=` decrypt at service start; the key can be sealed to
  `/var` (host key), the **TPM2** chip, or both (AES256-GCM). Because both 24.04
  (255) and 26.04 (259) are well above v250/v254, the full feature — including
  TPM2 binding — is available on the node's target OS.
  > "SetCredentialEncrypted= is safe to use even for sensitive information
  > because … the ciphertext … cannot be decoded unless access to
  > TPM2/encryption key is available."
  - https://systemd.io/CREDENTIALS/
  - https://manpages.ubuntu.com/manpages/noble/man1/systemd-creds.1.html
- **Python 3.14 via uv.** `uv python install 3.14` installs a
  python-build-standalone build (incl. a free-threaded variant). Python 3.14.0
  final released **2025-10-07**, so this is a stable target as of Aug 2026.
  - https://docs.astral.sh/uv/concepts/python-versions/
  - https://www.python.org/downloads/release/python-3140/

### 4. NTP — chrony version & Ubuntu default

- **chrony 4.7** released **2025-06-12** (chrony-users announcement). The
  project download page lists **4.8** as current stable with **4.9-pre1** in
  pre-release.
  - https://www.mail-archive.com/chrony-users@chrony.tuxfamily.org/msg03819.html
  - https://chrony-project.org/download.html
- **Ubuntu default time-sync daemon:** PRIMARY (Ubuntu Server docs):
  > "Since Ubuntu 25.10 `chrony` is used to synchronize time by default."
  > "On upgraded systems (from Ubuntu 25.04 or below) `systemd-timesyncd` might
  > still be the active time-daemon…"
  So **26.04 ships chrony by default**; 24.04 defaults to systemd-timesyncd. A
  node on 26.04 gets chrony out of the box; on 24.04 the operator must install
  chrony (recommended for a trading node needing tight, resilient sync).
  - https://ubuntu.com/server/docs/explanation/networking/about-time-synchronisation/

### 5. Observability libraries with cp314 support

- **prometheus-client 0.26.0** (2026-07-24) — classifiers list Python 3.9–3.14.
  https://pypi.org/project/prometheus-client/
- **opentelemetry-sdk 1.44.0** (2026-07-16) — Python 3.10–3.14.
  https://pypi.org/project/opentelemetry-sdk/
  (exporter-otlp is released in lockstep with the SDK version line; upstream
  tracks 3.14 in open-telemetry/opentelemetry-python#4789.)
- **structlog 26.1.0** (2026-06-06) — Python 3.10–3.15 (incl. 3.14).
  https://pypi.org/project/structlog/
All three are pure-Python or ship cp314 wheels and are safe on Python 3.14. (The
protobuf conflict in Item 1 is the only observability-adjacent risk, via
opentelemetry-exporter-otlp's own protobuf dependency — but modern
opentelemetry-proto uses protobuf ≥5, which is compatible with 3.14 and
**incompatible** with the cTrader SDK's `protobuf==3.20.1`. This reinforces the
Item-1 process-isolation recommendation.)

### 6. Windows Credential Manager access from Python (keyring)

- **keyring 25.7.0** (2025-11-16). https://pypi.org/project/keyring/
- **Windows backend:** class **`WinVaultKeyring`** in
  `keyring.backends.Windows` ("Windows Credential Locker"); uses pywin32's
  `win32cred`, credential type `CRED_TYPE_GENERIC`.
- **UI-stored credential read semantics:** keyring stores a password under
  TargetName = the `service` string; on a username collision it moves the entry
  to a **compound** TargetName `{username}@{service}`. Reads call
  `win32cred.CredRead(Type=CRED_TYPE_GENERIC, TargetName=target)`, which returns
  **any** matching generic credential regardless of how it was created. So
  **Python can read a generic credential created via the Credential Manager
  UI**, provided the UI credential's "Internet or network address" (TargetName)
  equals the `service` string keyring queries, and (for a specific-username
  lookup) the UI credential's UserName matches. Store the UI credential's target
  name = the exact service string the node uses.
  - https://raw.githubusercontent.com/jaraco/keyring/main/keyring/backends/Windows.py

> Note for the spine: Windows Credential Manager is the **operator's workstation
> control-door** path (CLI/API run from Windows), not the VPS secret store. On
> the Linux VPS the secret store is systemd-creds / `LoadCredentialEncrypted=`
> (Item 3d). keyring on Windows and systemd-creds on Linux are two different
> doors; don't conflate them.

### 7. Skylos — does it scan IaC?

Skylos (github.com/duriantaco/skylos) is **not a pure security scanner** — it
self-describes as a "local-first PR scanner that finds dead code, security bugs,
secrets, quality regressions, and AI-code mistakes." It **does** scan
Infrastructure-as-Code / deployment config, but a specific subset:
- **Docker:** `Dockerfile`, `Dockerfile.*`, `*.dockerfile` — flags dangerous
  `RUN`, remote `ADD` without checksum, literal build `ARG`/`ENV` secrets.
- **Docker Compose:** `compose*.y[a]ml`, `docker-compose*.y[a]ml` — privileged
  containers, broad host device/control mounts, host networking.
- **Systemd:** `*.service` — root edge services, mutable `ExecStart` paths,
  missing sandboxing, broad capabilities, broad device access.
- **Kubernetes:** rendered multi-doc `*.y[a]ml` bundles — unguarded HTTP routes
  to sensitive endpoints.
- **GitHub Actions** (`.github/workflows/*`, `action.y[a]ml`) and **GitLab CI**
  (`.gitlab-ci.yml`).
- **NOT Terraform** — Terraform/`.tf` is **not** in Skylos's supported file list.
- https://github.com/duriantaco/skylos/blob/main/README.md
- https://github.com/duriantaco/skylos

> Spine implication: the node's **systemd unit files and Dockerfile will be
> scanned** by the existing Skylos CI gate (root services, missing sandboxing,
> ExecStart hygiene, ENV secrets) — this is a real, useful gate for the node's
> deployment artifacts. But **Terraform is out of Skylos's scope**; if the node
> introduces Terraform, a separate IaC scanner (Checkov/Terrascan/tfsec) would
> be needed. Note also the QMX memory/CLAUDE refers to Skylos as "the security
> scanner"; more precisely it is a dead-code + secrets + IaC-misconfig PR
> scanner (its stablemate Vulture is the pure dead-code tool).

### 8. IC Markets cTrader — swap-free fees & Open API availability

- **Swap-free (Islamic) admin/holding fee — grade only.** The IC Markets Islamic
  account applies a flat-rate holding fee on positions held overnight, with a
  **grace period of up to five grace days** before fees begin (standard rollover
  = 1 grace day; triple-swap night = 3 grace days), and per-instrument
  exceptions (XNGUSD/XTIUSD/XBRUSD from Day 1; USDJPY/GBPJPY from Day 3). It is
  available on MT4, MT5, and **cTrader** (Raw Spread and Standard). The exact
  per-instrument schedule must be obtained by the operator in writing — do not
  hard-code the figures on this page into the spine.
  > "New positions may benefit from a grace period of up to five grace days,
  > during which no holding fees will be incurred."
  > "The swap free option is available on both our Raw Spread and Standard
  > account types on the MetaTrader4, MetaTrader 5 and cTrader platforms."
  - https://ic.com/en/trading-accounts/islamic-account (301 redirect from https://www.icmarkets.com/en/trading-accounts/islamic-account)
  - Grade **PRIMARY** for the source/policy existence; the figures themselves are
    operator-verified-separately per task instruction.
  - Caveat: IC Markets operates multiple regulated entities (e.g. .com global,
    .com.au) whose fee schedules can differ; confirm the entity the node trades
    under.
- **Open API on demo AND live.** Spotware Open API is broker-wide by default:
  > "the API can be accessed by anyone with a cTID, and, by default, it is
  > supported by all trading accounts of any cTrader-affiliated brokers."
  IC Markets is a cTrader-affiliated broker, so both its **demo and live**
  cTrader accounts are reachable via Open API (with the demo/live two-connection
  separation of Item 10).
  - https://help.ctrader.com/open-api/

### 9. uv — version & deployment pattern

- **uv 0.12.1**, released **2026-08-25** (GitHub releases).
  https://github.com/astral-sh/uv/releases
- **Recommended deployment pattern (PRIMARY, uv Docker guide):** For a
  production image, sync with **`uv sync --locked`** (asserts the lockfile is up
  to date). `uv sync --frozen` is used only for the intermediate,
  dependency-only layer before the full project is copied (multi-stage build).
  Run the service via its entry point: `CMD ["uv", "run", "my_app"]`, where
  `my_app` is a `[project.scripts]` console script.
  - `uv tool install` is for installing standalone **CLI tools**, not the right
    tool for a long-running service — use `uv sync --locked` + `uv run` (or a
    baked venv) for the node service.
  - There is no dedicated single-file "application distribution" feature in uv;
    packaging is via standard console_scripts / the project's own entry points.
  - https://docs.astral.sh/uv/guides/integration/docker/

### 10. Demo-vs-live host separation → two connections

PRIMARY and explicit in two places:
> "Demo and live environments are fully separated. If you connect to a live
> endpoint, you cannot use demo accounts in your application, and vice versa. …
> you would need to establish and maintain two separate connections."
> — https://help.ctrader.com/open-api/proxies-endpoints/
> "At most, you should create two connections: one for demo accounts and one for
> live accounts. Each connection can support an unlimited number of accounts of
> a certain type."
> — https://help.ctrader.com/open-api/connection/

Spine implication: the node's ONE product with two modes (paper/live) maps
cleanly onto cTrader's model — paper mode = a demo-endpoint connection, live mode
= a live-endpoint connection. If the node ever needs both simultaneously
(e.g. a live seat plus a demo/shadow seat), that is **two** long-lived TLS
connections, each with its own heartbeat and its own 50/5 rps budget.

---

## CROSS-CUTTING FLAGS FOR THE SPINE

1. **protobuf pin vs Python 3.14 (highest priority).** `ctrader-open-api==0.9.2`
   hard-pins `protobuf==3.20.1`, which has no cp314 wheels and predates 3.14.
   Modern protobuf is 7.36.0. The order-path process cannot share a protobuf
   with a 3.14 / modern-observability process. Resolution options: isolate the
   cTrader order-path in its own environment (older Python or a repackaged SDK),
   or regenerate the SDK's `_pb2` modules against modern protobuf (product work).
   The opentelemetry-exporter-otlp protobuf dependency makes co-location in one
   venv untenable.
2. **Twisted vs asyncio.** The only maintained SDK is Twisted-based; there is no
   verified maintained asyncio-native client. A Twisted reactor must coexist
   with (or be bridged to) whatever concurrency model the node runtime uses.
3. **Trendbar basis is BID, but undocumented on a docs page** — record with the
   moderator-forum caveat; ask/spread needs tick data.
4. **systemd-creds is the VPS secret door; keyring/Windows Credential Manager is
   the operator-workstation door** — keep them distinct in the spine.
5. **Skylos covers Dockerfile + systemd units + compose + k8s + CI, but not
   Terraform** — the node's deployment artifacts are gated; a Terraform choice
   would need a separate scanner.
6. **Two cTrader connections max** (demo + live) — paper/live modes map onto
   demo/live endpoints; each carries its own heartbeat and rate budget.
