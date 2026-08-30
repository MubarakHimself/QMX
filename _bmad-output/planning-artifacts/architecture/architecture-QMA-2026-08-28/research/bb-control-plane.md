# Reference Extract — bb (get-bb/bb): the control-plane / multi-surface reference

Scope: how one daemon serves many client surfaces over one versioned wire contract; thread/state model;
provider adapters; three-part plugins; UI contribution points; auth; attach/reattach. Filter = QMX Constitution
(single-operator, deterministic infra, daemon⊥UI, QMX owns its contracts). All facts primary-source, dated.

Sources (all checked 2026-08-28): repo README `https://github.com/get-bb/bb`;
`.../main/docs/system-overview.md`; `.../docs/repository-overview.md`; `.../docs/VISION.md`;
`.../docs/multiple-devices.md`; `.../docs/configuration.md`; `.../packages/bb-app/README.md`;
`.../packages/plugin-sdk/README.md`; `.../packages/plugin-sdk/src/backend-contract.ts`.

---

## Q1 — Target mental model
bb = "an agentic IDE that builds itself"; every surface (desktop app, web app, CLI `bb`, HTTP API) is a
**first-class, equal way to drive the same work** — "Work runs in threads you can follow live, steer at any
point, or hand off" (README, checked 2026-08-28). Central authority is a **Server** (SQLite = source of truth,
stateless itself); **Host daemons** on each execution machine actually run agents; **clients** are thin control
surfaces. Vision: "Users and agents are both first-class operators… The CLI should not be treated as a sidecar"
and "adapt to a user's infrastructure… not force them to fork bb" (VISION.md). This is exactly QMX decision #6
(daemon⊥UI) already realized as a shipping system.

## Q2 — Concrete runtime / API structures (real names)
Runtime pieces (system-overview.md, checked 2026-08-28):
- **Server** — central hub, all state in SQLite, exposes **HTTP API + WebSocket change notifications**, stateless
  (DB is truth), routes work to hosts over the active **daemon WebSocket**.
- **Host daemon** (`apps/host-daemon`) — one per enrolled machine; connects out to server, handles **host RPC**,
  provisions workspaces, runs **agent provider processes**, posts events back; also a **local HTTP API** for
  co-located app/CLI (open editor, pick folder, daemon status).
- **App** (`apps/app`, web UI) + **CLI** (`apps/cli`, `bb`) + **mobile** (`apps/mobile`) — all pure clients.

Data model (system-overview.md): **Project** → one+ **sources** (each local-path source bound to a specific
host) · **Thread** = unit of work (a conversation with a provider; lifecycle state; **append-only stream of
events** — messages, tool calls, file changes; `standard` vs `manager`; threads own child threads for
delegation) · **Environment** = workspace dir bound to a host (`unmanaged` | `managed`; GC'd when no unarchived
thread uses it; shareable) · **Host** = long-lived daemon identity.

Two contract packages are the ONLY cross-boundary imports (system-overview.md):
- **`@bb/server-contract`** — HTTP+WS between clients and server: route schemas, req/resp types, WS notification
  types.
- **`@bb/host-daemon-contract`** — server↔daemon: command types, event types, session lifecycle, the local API.
  "Implementation packages never import across these boundaries." Commands run async: server issues host RPC,
  **settles side effects when the daemon returns an RPC result**; daemons **separately post progress as event
  batches**. (Command≠event separation is explicit.)

SDK / wire surface (bb-app README): `import { BBSdk } from "bb-app"`; `bb.threads.spawn({projectId,
environment:{type:"host",workspace:{type:"personal"}}, prompt})`, `bb.threads.wait({threadId,status:"idle"})`,
`bb.threads.output({threadId})`. Env injected into launched scripts: `BB_SERVER_URL`, `BB_THREAD_ID`. Default
server `http://127.0.0.1:38886`; config `~/.bb/config.json` (`BB_APP_URL`,`BB_INFERENCE`…), secrets `~/.bb/env.json`.

Provider adapters (`packages/agent-runtime`, repo-overview): "runtime adapters and bridges for **Codex, Claude
Code, Pi, and ACP** agents"; a `PluginProviderDeclaration` carries `capabilities` (`fork: ProviderFork`,
`supportsManualCompaction`, `supportsThreadArchive/Rename`, `permissionModes`, `reasoningLevels`, `models[]`,
`composerActions[]`), plus `configure()`, `registerTool()`, `contributeInstructions()` (backend-contract.ts,
checked 2026-08-28).

Plugin system — a plugin is a **backend part + frontend part**, each an authored contract file:
- backend `server.ts`: `export default function plugin(bb: BbPluginApi)`; impl lives in
  `apps/server/src/services/plugins/plugin-api.ts`, imported **type-only** so contract can't drift
  (backend-contract.ts). Registration surface (real members, design §4.x):
  `bb.settings.define/get/onChange` · `bb.kv.get/set/delete/list`, `bb.database()`, `bb.migrate()` ·
  `bb.on(threadEvent,handler)` (thread lifecycle) · **`bb.http.route(method,path,handler)`** (Hono) ·
  **`bb.rpc.register(contract,handlers)`** (typed, zod/StandardSchema) · **`bb.realtime.publish(channel,payload)`** ·
  `bb.service(name,{start(signal)})` · `bb.schedule(name,cron,fn)` · `bb.cli.register({name,summary,run(argv,ctx)})`
  (agent-facing subcommands) · `registerTool(...)` + per-turn agent context (thread/project/environment/host/
  provider capabilities) · `bb.providers.register(decl)` · `bb.registerMentionProvider(...)` · `bb.requestInput(...)` ·
  `bb.ai.register(...)` · `bb.needsConfiguration(msg)` / `NeedsConfigurationError` matched **by name** (no runtime import).
- frontend `app.ts` (`@get-bb/plugin-sdk/app`, replaced by BB's impl at `bb plugin build`; plugin-sdk README):
  named **UI contribution points** — `app.composer.customize({actions, banners, ComposerPlusMenuItem rows,
  ComposerRichTextSpec})`; **thread-panel actions** (`useBbNavigate().openThreadPanel`), `messageAction`,
  `experimental_newThreadPanelAction`; **homepage sections**; **nav panels + `fixedTabs`**
  (`experimental_useAppPanel().openFixedTab`); **content scripts** (`app.contentScripts.register({id,mount})`,
  trusted same-origin, generation+signal, exact-once reverse-order disposal); manifest **`bb.themes`** palettes;
  navigation (`useBbNavigate().openUrl`, `UrlLink`, `experimental_FileLink`). Every panel-open returns `boolean`
  (declined ≠ thrown). Reload is **generation-keyed**: `reload(factory)` preserves settings/KV/DB and invalidates
  the old API only after the replacement succeeds.

Auth / multi-device (multiple-devices.md, checked 2026-08-28): local default binds **loopback** and the API is
**unauthenticated** (permits command exec + file reads) — remote access goes via **bb connect** (account-gated
tunnel, server owns tunnel + reconnect) or **Tailscale Serve**; `--server-bind-host 0.0.0.0` is a flagged footgun.
Devices enroll as **machines** with a per-device `machineCredential`/`connectMachineId` (OS-keychain), listed &
revocable in the getbb.app dashboard; each machine takes an account slot.

## Q3 — Failure modes bb solved
1. **Client death must not kill work** → execution lives on host daemons, not clients; server stateless over DB;
   "browser device… does not execute" (multiple-devices.md). Closing/loss of a client leaves work running.
2. **Multi-surface consistency** (desktop/web/CLI/API all steer the same thread) → one `server-contract`, all
   surfaces are clients of it.
3. **Reconnect / roaming / restart** → stateless server over SQLite + WS reconnect; daemon **protocol-version
   negotiation at session open**: "If session open reports a newer server protocol, the daemon downloads… updates…
   then exits so the service manager restarts it… A daemon never downgrades itself to an older server protocol"
   (multiple-devices.md).
4. **Contract/impl drift** → contract packages imported type-only by both server impl and plugins.
5. **Hot reload without state loss** → generation-keyed `reload(factory)` preserving settings/KV/DB, exact-once
   disposal (plugin-sdk README).
6. **Async lifecycle vs sync callers** → command side-effects settle on RPC return; progress arrives as event batches.
Not fully solved (open issues, checked 2026-08-28): blocking on `AskUserQuestion` **409-rejects** inbound messages
(#1650); **long threads get slow** — keystroke cost scales with mounted timeline size (#1304, #1777). ⇒ QMX warning:
an append-only event stream needs UI-side windowing/compaction and a non-blocking interaction channel.

## Q4 — What QMX should reuse (conceptually)
- **Two-package contract law** as the daemon⊥UI boundary: a `server-contract` (client↔daemon) and a
  `host-daemon-contract` (daemon↔execution host), **the only things imported across the boundary** — the exact
  shape of Constitution §3/§4 and decision #6.
- **DB = source of truth; server/daemon stateless over it; per-unit append-only replayable event stream; WS push
  of change notifications.** Directly gives Constitution §6 and register #39 (session replay = architectural
  capability, not a chat feature).
- **Command≠event≠query separation** with async settlement (command acked, side effects settle later, progress as
  event batches).
- **Attach = pure subscription; execution identity independent of attachment** (register #7); a "control surface"
  device model.
- **Protocol-version reported/negotiated at session open** — the seed of QMX's forward-compat hook.
- **Plugin = logical bundle whose backend and frontend halves talk only over the daemon contract** (RPC/realtime),
  never shared memory (register #67); **host shell owns layout, plugins contribute only into named extension
  points** (register #68); generation-keyed reload preserving state (matches Cordis reversible-effects borrow).
- **Typed RPC contracts w/ schema validation + strict JSON** (Constitution §2 determinism); **name-tagged errors**
  (`NeedsConfigurationError`) so the UI needs no daemon runtime types.

## Q5 — What QMX should reject
- **The provider-adapter / agent-runtime bridge zoo** (Codex/Claude/Pi/ACP/Cursor/opencode/grok/hermes). It exists
  because bb serves the public who bring their own agent. QMX owns its runtime bottom-up (Constitution §3, decision
  #2); register overcooked-#1 already flags "QMX Agent Protocol + provider adapters" as dead weight. Keep only the
  model-proxy idea (that's OpenCodex's job, not bb's).
- **bb connect / getbb.app account gate, machine credentials + slots + revocation dashboard, mobile client,
  telemetry-to-vendor, `bb-community` marketplace + install counts.** All multi-tenant/public. QMX is single-operator.
- **Full-trust same-origin plugin model** — register reject (L886); a Rust UI host needs a real isolation story
  (open Q on Rust extension tech), not "content scripts are trusted page code."
- **Thin `thread(standard|manager)` as the ontology** — QMX has Desk/Role/Bot/Agent/Subagent + Mission/Task-Graph.
- **Unauthenticated loopback API + `0.0.0.0` bind + editor helper** — a footgun bb itself warns about.
- **Forced lockstep upgrade** (daemon auto-updates or refuses) — too rigid when a *separate team* ships the UI;
  QMX needs negotiated capability compatibility, not "download and restart or die."

## Q6 — INHERITED FASHION (exists for multi-user / marketplace, QMX drops)
bb connect + getbb.app auth/dashboard; machine credential + account slots + remote revocation; mobile app;
anonymous usage telemetry; `bb-community` plugin marketplace, public-plugin naming, install-count ranking; the
multi-provider adapter bridge (public agents); trust-level framing of plugins. QMX has one operator, one (or few)
enrolled hosts, and first-party plugins — none of this is load-bearing.

---

## Proposed QMX daemon↔UI wire contract SHAPE (QMX-owned)
Mirror bb's two-package law but QMX-shaped and **language-neutral** (Rust UI, TS/Python daemon undecided — define
contract first, per register open-Q #1). Contract package = single source of schemas → generated Rust + TS/Python
types; no impl imported across the seam.
- `qmx-daemon-contract` — UI/CLI/SDK ↔ Daemon (HTTP/RPC + query + durable WS event stream).
- `qmx-host-contract` — Daemon ↔ execution host / Docker / the one Windows VPS (internal, bb's host-daemon-contract role).

**Envelope (every message):** `{ v, type, id, scope, seq?, payload }`. `scope` = `agent|subagent|mission|task|desk`.

**Command family** (mutations; acked; side effects settle async): `bot.create-from-role`, `mission.compile`
(Goal→Mission), `mission.start`, `task.claim/complete`, `taskgraph.mutate`, `agent.spawn{mode:dialogue|rlm}`,
`agent.send` (steer/prompt), `agent.stop`, `subagent.spawn`, `interaction.answer`, `permission.grant/deny`,
`skill|loop|graph.register`, `router.config`, `mcp.configure` (per-desk/role).

**Query family** (reads of durable state): `taskgraph.get`, `mission.get`, `bot.list`, `agent.status`,
`ledger.query{desk}`, `knowledge.query`, `experiment.get`, `trace.get`, `replay.get{trajectory}`.

**Event family** (durable, append-only, per-scope, monotonic `seq`): `agent.turn.started|tool.call|tool.result|
output|progress|error|idle|completed` (bb's thread-event model); `mission.*` / `task.*` state transitions;
`ledger.entry` (agent-authored — a **separate stream** from telemetry, Constitution §12); `interaction.requested`
(non-blocking — do NOT 409 the mailbox, cf. bb #1650); `bus.message` (mailbox delivery).

**Attach / reattach:** `attach(scope, sinceSeq?)` → daemon replays events from `sinceSeq` out of the durable log
(DB=truth), then live-tails over WS; returns a snapshot cursor. Attachment changes **no** execution identity;
`detach` drops the subscription, agent keeps running on host (register #7, Constitution §4). **UI down for days →**
reconnect with the last persisted `seq`, nothing lost. **Session replay** = the same `attach(sinceSeq:0)` on a
finished trajectory, read-only (register #39). Interaction requests queue durably so a detached run isn't wedged.

**Versioning (a separately-teamed UI stays compatible):** semver `protocolVersion` + a **capability descriptor
negotiated at session open** (bb reports a protocol; QMX *negotiates* instead of force-upgrading). **Additive-only
within a major** — new event types, new optional fields, new commands never break an older UI; unknown types/fields
are **ignored** by older clients (forward-compat hook, PRD). UI declares the max major it speaks; daemon degrades
gracefully within a major and refuses only on major mismatch. Deprecations stay live for N minors with warnings,
then drop (bb's `customAcpAgents` "read, warn, stop at 0.41" pattern). Contract package is the compat authority.
