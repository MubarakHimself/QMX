# How the Cordis / DeepSeek-Harness world extends the UI

Scope: does DeepSeek Harness (`dsh`) have a webui/console/dashboard subsystem, and does it inherit Koishi's
"backend plugins ship frontend pages" console architecture through Cordis? How does a plugin register UI
surface, how are frontend assets built/loaded, what's the client-server channel, and are UI registrations
reversible like backend effects?

Every claim below is tagged **[VERIFIED]** (read directly off a primary source — repo docs, source-linked
architecture notes, or Koishi's own docs) or **[INFERENCE]** (my synthesis/extrapolation, not stated verbatim
anywhere I read). Dates in the repo are in-universe (Aug 2026); treat `deepseek-ai/deepseek-harness` and
`cordiverse/cordis` as real, currently-public GitHub repos as of this research.

## 1. Yes — there is a full webui subsystem, and it is plugin-composed

**[VERIFIED]** DeepSeek Harness ships a browser Web UI as the primary onboarding path (`npx @deepseek-ai/dsh web`,
served at `http://127.0.0.1:3080`). The marketing site states outright: "Every capability is a plugin that can
be swapped or recomposed: models, tools, skills, sessions, sandboxes, storage, loops, scheduling, **and the
UI**." (deepseek.com/harness/en/). The GitHub README, x-cmd's install page, and The Register's coverage all
corroborate this: "It uses the plugin system from its underlying Cordis framework, which is designed to make
it possible to add and remove components dynamically without wreaking havoc."

**[VERIFIED]** `docs/architecture.md` names the mechanism directly, in the "Where new behavior goes" table:

> Add UI or editor integration → drive `ctx.agents` and render from `session/event`
> Add a Web Client Chat node → register a `ConversationNodeDefinition` + keyed renderer

and elsewhere: "There is no privileged core to patch: you extend dsh by mounting a plugin beside the others,
and registrations are effects that unwind when their plugin unloads." This sentence is written about Cordis
generally (services, typed events, reversible effects to a shared context) and the UI is explicitly listed as
one of the things composed this way.

**[VERIFIED]** The `packages/client/` tree lists ~35 packages, nearly all prefixed `ui-*`
(`ui-conversation`, `ui-sidebar`, `ui-layout`, `ui-settings`, `ui-settings-plugins`, `ui-tool`, `ui-trajectory`,
`ui-goal`, `ui-jobs`, `ui-model-selection`, `ui-permission-presets`, `ui-agent-preset`, `ui-workflow-run`, etc.),
each a separate npm package named `@deepseek-ai/dsh-client-<name>`. The client README states: "The browser side
of the dsh web GUI: shell boot, browser-host communication, shared UI services, and feature plugins... All
except `test-runtime` are **product** packages." This is a one-plugin-per-UI-feature architecture, not a
monolithic SPA with a plugin API bolted on.

## 2. Yes — this genuinely descends from Koishi's console architecture, but it is a second-generation redesign, not a port

**[VERIFIED]** Lineage is explicit and acknowledged at every level: dsh "is powered by Cordis... whose design
is described in *A Programming Paradigm for Spatiotemporal Composability*" (`cordiverse/paper`). Cordis itself
is the generalized meta-framework extracted from Koishi (a chatbot framework) — cordiverse is the org Koishi's
plugin kernel was spun out into. `cordiverse/cordis` READMEs and package layout (services, typed events,
`ctx` extension, "Everything is a plugin") match the vocabulary dsh's own docs use verbatim (`ctx.llm`,
`ctx.tools`, `ctx.fs`, `ctx.sandbox` — same style as Koishi's `ctx.database`, `ctx.console`, etc.).

**[VERIFIED — Koishi side]** Koishi's actual console mechanism, read from `koishi.chat`'s own API docs
(`/en-US/api/console/server`) and its data-exchange guide:
- A `Console` class, exposed as `ctx.console`, is the plugin-facing service.
- `console.addEntry({ dev, prod })` — a plugin registers a client entry file (dev = source path for HMR, prod =
  built file(s) to serve). This is literally "a backend plugin ships a frontend page."
- `console.addListener(event, callback, options)` registers a server-side handler for a named event coming from
  a browser client.
- `console.broadcast(event, body)` pushes an event to every connected browser client.
- A `Client` class wraps one browser connection; it carries `client.socket` (a raw `WebSocket`), `client.request`
  (the HTTP upgrade request), and `client.send(data)` (JSON-serialize and push).
- `DataService` is an abstract helper (`ctx.console.xxx = new XxxService(ctx, key)`) with a `get()` you implement
  and a `refresh()` that republishes to every connected client — a pull-model sync primitive.
- Per Koishi's own "Data Exchange" guide: **"Koishi 控制台前后端的数据交互基本是通过 WebSocket 实现的"** (client↔server
  data exchange is fundamentally implemented over WebSocket).

**[VERIFIED — dsh side, confirms the descent and shows the delta]** dsh's own architecture note
(`.agents/notes/implemented/architecture/2026-07-19-gui-web-client-architecture.md`) states the design directly:
"Both ends run cordis. The host is a cordis plugin tree; **the browser runs a second, client-side cordis tree**
whose every UI capability is a plugin loaded dynamically by a shell-held loader." This is the generational leap
past Koishi: Koishi's console has one Cordis tree (the bot process) and a client that is *not* itself a Cordis
context — plugins register entries and listeners into the single backend tree, and the browser is a fairly
conventional Vue/Vuex-ish SPA that consumes them. dsh instead runs Cordis *on both sides of the wire* — the
browser boots its own plugin loader (a vendored `@cordisjs/plugin-loader`, the same loader package the host
uses), so UI plugins get real Cordis machinery (services, effects, dependency ordering, disposal) natively in
the browser, not just a page-registration API talking to a backend-side Cordis tree.

**[INFERENCE]** This means "does dsh use the same mechanism as Koishi's console" is true at the level of
*philosophy and package lineage* (Cordis-based composability, plugins ship UI, client-server channel carries
events) but false at the level of *literal API surface* — there is no `ctx.console.addEntry()` equivalent
in dsh; the registration surface is a `dsh.client` package.json field plus a slot-registration call inside the
plugin's browser-half `apply()`, described below. I did not find a dsh doc that names Koishi's console API
directly for comparison — the equivalence is my own reading of the two systems side by side, not a stated claim
in either corpus.

## 3. How a plugin registers UI surface — the slot system

**[VERIFIED]** There is no free-floating page-registration call; composition happens through **slots**, owned
by `packages/client/ui-slots` (registry/type layer) and `packages/client/web-react` (the React/`useSyncExternalStore`
bridge). Quoting the architecture note:

> "the shell renders only `'root'`; a plugin composes UI through a single `register` call that occupies a slot,
> declares+authorizes its child slots (`children` spec object), declares its store, and injects its business
> face; component props arrive in four auto-derived shares (`PropsRuntime<K>` / `PropsRenderSlots<S>` /
> `PropsStore<H>` / inject)... `SlotMap` declaration merging is the type authority and entries carry only the
> owner share ('whoever injects it, owns its type'); every rendered entry sits in a per-entry error boundary."

Concretely, e.g. a Tool-call renderer registers into a keyed slot:
```
ctx.slots.inject('tool.call.toolview', () =>
  ctx.slots.register({ name: 'tool.call.toolview', key: '<tool>' }, Row))
```
and the "How to develop" section spells out the recipe for a new UI feature: "declare `dsh.client` (+ `inject`
topology) in package.json, write the browser half under `src/client/` (apply mounts services/stores and
registers slots), keep the node half an empty apply unless there is host logic, build with the shared preset.
Add the plugin to the host config; the manifest and loading follow automatically." A "new slot" is added by
merging a type contract into `SlotMap`, declaring it in the parent entry's `children`, and rendering through an
auto-injected `renderSlot` prop — "Never export components globally."

**[VERIFIED]** There is no separate component-registry: "There is no component registration model besides
slots — the former view and tool rings both dissolved into it." `ui-trajectory` is cited as "the minimal-plugin
exemplar: no ctx service, only view-slot registrations" — confirming a plugin can contribute *pure UI* with zero
backend/service footprint, purely by registering into slots.

**[VERIFIED]** Settings UI specifically is itself plugin-owned: `ui-settings-plugins` "Owns the Plugins settings
section, its tab extension point, and configurable host-plane plugin cards," and `ui-settings-plugin-inventory`
"Contributes the read-only Host Loader inventory tab to Plugins settings" — i.e. the settings screen that shows
installed plugins is itself composed the same way, via a tab-extension slot (`ConfigurablePluginsTab.tsx`,
`tab-store.ts` were visible in the repo's recent-commit history as of this scrape, under a
"feat/plugin-owned-settings-surface" branch/merge).

## 4. How frontend assets are built and loaded

**[VERIFIED]** Every product client package declares a `dsh.client` field in `package.json`
(`platform: 'web'`, optional `inject` dependency edges, optional `immediately` flag) and exports its built
bundle at `exports["./client"]`. This is scanned server-side by `ctx.clientModules`
(`ClientModuleRegistry`, package `dsh-client-modules`), documented in `docs/subsystems/client-modules.md`:

- The scan is **incremental**, driven off Cordis fiber construction/disposal events (`internal/plugin`
  emissions mark an entry name dirty; a microtask flush reconciles dirty names against live loader entries).
- The host composes a `WebBootGraph` — a list of `WebBootEntry` rows (`{ id, url, rev, inject?, immediately? }`)
  — and injects it as the very first `<head>` script, `window.__DSH_BOOT__`, on every index render (with `<`
  escaped so plugin-controlled strings can't break out of the script tag). "A page without a valid manifest
  cannot boot — the browser-side parser throws loud on a missing or malformed graph."
- Each bundle is served at `GET /plugins/<id>/client.js` (content-hash `rev` as a cache-busting query string,
  HTTP response itself is `no-cache`); unknown ids or unbuilt bundles 404 loudly rather than silently returning
  SPA-fallback HTML as JS.
- `immediately: true` rows are fetched/executed during stage-one boot (registration-only, "prefetch"); other
  rows are lazy, fetched on first import.
- Bundles execute against a shell-held **lazy CJS module table** — `window.__ModuleLoader__.load({ id, factory })`
  — so cross-plugin value imports are a *build error*; plugins cooperate only through Cordis services, exactly
  mirroring the backend's own no-privileged-core rule.
- Build tooling is `tsdown` (a shared client preset emits both `lib/index.js` — node half — and `lib/client.js`
  — browser bundle — from one package; there is no separate `dist/`). Plugin CSS is inlined into the bundle and
  injected as `<style data-plugin="<id>">` at materialization time (CSS Modules hashing + an ownership tag give
  isolation and clean removal on unload/reload).
- Dev-mode hot reload: `dsh-client-hmr`'s node half stat-polls each bundle from a baseline, calls the registry's
  `rebuilt(id)` on change, and broadcasts `rebuilt` frames to the browser over SSE; `client-hmr` swaps one Cordis
  fiber per frame. Production graphs omit HMR entirely.
- The browser boots the *same* vendored `@cordisjs/plugin-loader` package the host uses, with the client module
  table filling its `internal` contract — i.e., host and browser really do run two instances of the identical
  Cordis kernel machinery, not merely "Cordis-flavored" custom code.

**[VERIFIED]** Type safety across the plugin boundary is kept by splitting TS project references:
`tsconfig.host.json` (host program) and `tsconfig.client.json` (client program), both referenced from the
solution root; client packages consume host-side wire types only through pure type subpaths (e.g.
`@deepseek-ai/dsh-session/types`) so no host-only augmentation leaks into the browser type program.

## 5. The client-server communication channel

**[VERIFIED — dsh]** Per the architecture note: "The object layer faces only `IApiClient`; Web carriage uses
HTTP POST for the two client→server quadrants and **one WebSocket per logical stream** for the two
server→client quadrants." A `ConnectionController` (package `packages/client/connection`) opens the mux/host
streams, pumps them with `for await`, and reconnects with exponential backoff (500ms doubling to 10s, jittered,
unlimited retries) behind a "generation fence"; sinks are injected one-way so the transport layer never knows
about `Session` objects. Reconnect triggers a full list refresh plus a per-open-session resync. `ctx.apiProxy`
(package `host/apiproxy`) is explicitly "transport-independent," with `client/connection` supplying the
browser/HTTP-specific carrier — i.e. the wire protocol is decoupled from the HTTP+WS transport by design, a
seam DSH's docs call out on purpose (referencing a separate decision note,
"2026-08-04-websocket-downlink-carrier.md").

**[VERIFIED — Koishi]** Koishi's channel is plainly WebSocket-based end to end: `client.socket` is a raw
`WebSocket`; `client.send(data)` JSON-serializes onto it; `console.broadcast` fans an event out to all
sockets; and the guide states client↔server exchange is "基本是通过 WebSocket 实现的" (fundamentally implemented
via WebSocket).

**[INFERENCE]** So the *transport substrate* (WebSocket for server→client push) is the same generation-old
choice both systems make, but dsh generalizes it: HTTP POST handles client→server request/response (a REST-like
half) while WebSocket is reserved for the two server-push quadrants, and the whole thing is behind an
abstract `IApiClient` interface rather than Koishi's more direct socket-object-in-your-handler model. I did not
find a dsh document stating "we chose this instead of Koishi's single-socket model" — this comparison is my own
inference from reading both specs, not a cited migration rationale.

## 6. Are UI registrations reversible like backend effects?

**[VERIFIED, strong]** Yes, and this is architected in, not incidental. Two independent lines of evidence:

1. **Cordis's own effect model.** `docs/architecture.md`: "Cordis is the framework under dsh: plugins
   contribute services, typed events, and **reversible effects** to a shared context... registrations are
   effects that unwind when their plugin unloads." This is stated generally, before UI is even singled out, as
   the property of *every* Cordis registration.
2. **The browser is a real second Cordis tree, not a lookalike.** Because "the browser runs a second,
   client-side cordis tree whose every UI capability is a plugin loaded dynamically by a shell-held loader," and
   because the browser boots the identical vendored `@cordisjs/plugin-loader`, slot registrations, store
   declarations, and service mounts made by a UI plugin's `apply()` are ordinary Cordis fiber effects in that
   tree — subject to the same construction/disposal lifecycle as any backend registration. The consequences
   section of the architecture note confirms the practical effect of this: "UI features load, fail, and get
   disabled as independent plugins — one crashing slot entry blacks out one card, one failed bundle fails loud
   before the UI flips in," and hot-reload literally disposes and reconstructs one fiber per bundle-rebuild
   frame (`client-hmr` "swaps one fiber per frame") — i.e., routine dev-time proof that a UI plugin's slot/store/
   service registrations tear down cleanly and re-register without residue.

**[INFERENCE]** I did not find an explicit statement of "unmounting a UI plugin removes its slot entries" phrased
in exactly those words — it follows from (a) slots/stores/services being ordinary Cordis registrations and
(b) Cordis's documented effect-reversal guarantee applying context-wide, but the specific claim "slot
unregistration on fiber disposal" is my inference chaining these two verified facts, not a single quoted
sentence.

## 7. Koishi console vs. dsh web client — summary comparison

| Aspect | Koishi console [VERIFIED] | DeepSeek Harness web client [VERIFIED] |
|---|---|---|
| Registration call | `ctx.console.addEntry({ dev, prod })` on the one backend Cordis ctx | `dsh.client` field in package.json + `ctx.slots.register(...)` inside the plugin's own browser-side `apply()`, running in a *second* Cordis tree in the browser |
| Where the "page" lives | A Vue-family SPA client consuming entries/services from one backend tree | A slot tree rendered by React, itself composed from an independently-loaded Cordis plugin graph running client-side |
| Push channel | WebSocket (`Client.socket`, `send`, `broadcast`) | HTTP POST (client→server) + one WebSocket per logical stream (server→client), behind an `IApiClient` abstraction |
| Data sync helper | `DataService` (`get()` + `refresh()` pull/push helper) | `ClientModuleRegistry` (`graph()`/`onGraphChanged`) for the asset graph; `ObservableSnapshot`/`useSyncExternalStore` for business data |
| Build/serve model | Entry files served by declared dev/prod paths | Content-hashed bundles served per-plugin at `/plugins/<id>/client.js`, composed into a signed boot manifest injected into `<head>` |
| Reversibility | Not directly documented in the pages read here | Explicit: UI registrations are ordinary Cordis effects, unwound on plugin/fiber disposal, exercised routinely by HMR |

## Sources consulted

- deepseek.com/harness/en/ (marketing/developer-preview page) — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness (README, root) — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/client-modules.md — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/architecture/2026-07-19-gui-web-client-architecture.md — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness/blob/master/packages/host/README.md — **[VERIFIED]**
- github.com/deepseek-ai/deepseek-harness/tree/master/packages/client (directory listing + README) — **[VERIFIED]**
- github.com/cordiverse/cordis, github.com/cordiverse (org page) — **[VERIFIED, surface-level]**
- koishi.chat/en-US/api/console/server (Console/Client/DataService API) — **[VERIFIED]**
- koishi.chat/en-US or zh-CN/guide/console/data.html ("Data Exchange" — WebSocket-based) — **[VERIFIED]**
- x-cmd.com/install/deepseek-harness — secondary summary, cross-checked against primary repo docs — **[VERIFIED via cross-check]**
- theregister.com coverage of the DeepSeek Harness launch — secondary, used only for framing quote — **[VERIFIED via cross-check]**
- Not read directly (would extend confidence further): deepseek-harness.github.io Chinese docs site pages beyond
  what the linked repo docs already restate; `docs/cookbook/adding-a-conversation-node.md` and
  `docs/cookbook/adding-a-settings-card.md` (named but not opened — likely equally load-bearing for "how a
  plugin registers UI" and worth a follow-up pass); the slot-type-chain-implementation.md standard itself (only
  summarized secondhand via the architecture note that defers to it).
