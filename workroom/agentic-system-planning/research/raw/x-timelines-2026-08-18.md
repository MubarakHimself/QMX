# RAW: X timeline captures — @Teknium1 & @imbabybrooklyn (2026-08-18)

Provenance: straggler children of a stopped research agent, completed 2026-08-18 after a pause order. First timeline page only (~1 day Teknium, ~5 days Brooklyn), via TwStalker mirror. Archived so the work isn't lost. X research is PARKED — later down the road per Mubarak.

## Teknium (@Teknium1) — Cofounder & Lead Engineer, Hermes Agent @NousResearch

**Bot Mode announcement (status 2089430781668303090, ~2026-08-17):**
> Reintroducing Bot Mode for Hermes Agent. Bot Mode is an alternative to sessions, where you have one chat with each agent profile, or "bot". These bots can be given jobs, descriptions, profile pics, and communicate with your other bots — They maintain their own memory, skills, tools, and external connections as well!

Quoted @NousResearch (2089429432612147572): "Your agent profiles become a series of named Bots. Each Bot has its own role, model, memory, skills and profile picture; Bots can use any model and even communicate with each other. Build a specialist Bot once to use it forever."

**Hermes Agent positioning (2089657576300376099):** "100% free, open source, MIT licensed agent harness… complete optionality and capabilities… 2,500+ contributors… plugins, skins, skills, and projects powered by hermes." Older launch post: "a very good blend between coding agents like Claude Code and generalist agents like Clawdbot… started as a way for us to have agentic primitives for datagen and RL."

**Architecture facts (2089653342297538767 — Teknium pasting his own Hermes' support answer):**
- `api_server` = OpenAI-compatible platform surface, port **8642**, authed by `API_SERVER_KEY`.
- `hermes serve` = dashboard backend, default port **9119**; desktop app connects here via session token, OAuth, or SSH-adopted token.
- Settings → Gateways supports SSH connections (app opens tunnel + handles auth itself).
- `hermes peer add` = cross-machine bot messaging.
- Docs: hermes-agent.nousresearch.com/docs/user-guide…

**Gateways/GUI control (2089651977919881609):** "a linux machine with a GUI, a mac mini, a windows PC — they can all run a gateway you can hook into your hermes desktop and can control those GUI Machines."

**Other:** Kanban plugin (settings → plugins → kanban); mobile app on roadmap, no date.

**Negative finding:** no HUD / browser-use / computer-use / CUA content in this capture window.

## Brooklyn (@imbabybrooklyn) — Hermes UI dev ("just a doll using a lot of tokens", brooklyn.sh, GitHub OutThisLife)

**In-app browser (2089669386718085430, highest engagement):** "Okey you have full control of the in-app browser now. Hermes does too." Shortcuts: ⌘⇧L, and ⌘K → "Open browser" (command palette exists).

**Inline generative UI (2089453432918753626):** "You can make your own inline, native widgets in Hermes Agent. For example, create a skill like `/get-price btc` and render a live chart right inside your chat." → skills are slash-command-invocable and can render native widgets.

**Sessions model (2089397281627721894):** sidebar customizable; group by project; project view lists all related **sessions & worktrees**. Skill example `/list-open-work`: "list my open MRs/PRs in the current repo/worktree" → Hermes has current-repo/worktree awareness.

**Shipping cadence:** user requested settings search → shipped in ~2 hours.

**Negative finding:** zero posts in window on HUD, Bot Mode, voice, Electron/IPC/gateway internals, computer use. Older posts need pagination.

**Ecosystem bios spotted:** @iamlukethedev "Building Hermes Agora — The 3D Command Center for Hermes Agents"; @phragg "ui eng @nousresearch"; @steeldotdev "Humans use Chrome, Agents use Steel" (third-party agent-browser product).
