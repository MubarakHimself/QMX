# Reference Extract — Grok Bot (xAI) & Buzz (Block)

Scope: persistent-actor mental model, routines, async handoffs, daemon-level agent
messaging (mailbox + durable transport + wakeup). Operator did NOT agree to adopt
Buzz or Nostr (register §3.6, §5) — semantics only. Filter = QMX Constitution (single
operator, deterministic infra, daemon≠UI, ledger≠messages). All facts checked 2026-08-28.

Primary sources:
- Grok Bot: bots / skills-routines / chat-and-collaboration / computer-and-apps (docs.x.ai/grok-bot/*.md)
- Buzz: README + Architecture (github.com/block/buzz)
- Corroborating (3rd-party integration, tagged): Hermes-ecosystem env-vars & Veritas-Kanban BUZZ-INTEGRATION (NIPs, kinds, transport)

---

## Q1 — Target mental model

A **persistent, named actor is a first-class organizational object with its own identity,
memory, and addressable inbox — separate from any single running turn.** Grok calls it a
"durable AI teammate with a name, a job, its own conversation, and working context that
develops over time" (bots.md). Buzz makes it sharper and identity-first: "**Agents are
members, not bots. Add an agent to a channel the same way you add a person**" — every
participant (human, agent, workflow, git event) is a keypair, "scoped by identity, not by
permission flags — the same way you'd scope a teammate" (block/buzz README). This is
exactly the register's Bot(=durable identity) vs Agent(=running instance) split (§ontology
10–14): the actor persists; the reasoning run is disposable. Coordination is asynchronous
message-passing between long-lived addressable actors — the actor-model, at the daemon.

## Q2 — Concrete runtime/API structures

GROK BOT:
- **Bot** = name + title + description + avatar + enabled skills + routines + learned
  memory. Description holds *durable* rules ("Never send external messages without
  approval"); the conversation holds task instructions (bots.md). Account cap: 50 Bots+groups.
- **Rule for a new Bot** (bots.md, verbatim list): create one when work has a distinct
  **Goal/area of ownership · set of tools and sources · working style · approval boundary ·
  recurring schedule**. Otherwise reuse/duplicate. "Start with the smallest useful roster …
  add another Bot only when the work has a stable specialist role."
- **Routine** = "tells one Bot when to run a workflow — on a schedule or … after an event"
  (skills-routines.md). Owned by exactly one Bot. Fields confirmed at create: owning Bot,
  schedule+time zone, input source, expected result, approval boundary, no-data/stale-data
  policy. **Test run** = real side-effecting dry run. Caps: 50 routines/Bot, keeps 20 run
  records. **Event triggers** ("when #channel msg contains 'needs repro' …") warn against
  broad listeners. "Background routines can run while your laptop is closed."
- **Handoff/wakeup** (chat-and-collaboration.md, verbatim): "A Bot can send an
  **asynchronous message to another Bot. The receiving Bot wakes, handles the request, and
  can reply later.**" A direct human message "takes priority over background work and can
  redirect the current turn." Group chat (2–6 Bots) makes handoffs visible; `@Bot` routes,
  `@everyone` broadcasts. Handoff messages are text-only today.
- **Persistence/isolation** (computer-and-apps.md): Bot state (profile, memory, routines) is
  durable and survives app/laptop close ("Closing the Grok Bot app or your laptop does not
  stop cloud work"). BUT compute is a **single shared cloud computer per account** — shared
  cookies, files, `/workspace`, CLI creds; "Each Bot gets its own screen … The screens are
  separate work surfaces, **not separate security boundaries**." Durable snapshot + Update/
  Recover/Reset lifecycle.

BUZZ:
- **Identity**: every actor = a Nostr keypair (secp256k1 / Schnorr); own channel memberships;
  own audit trail. Stable pubkeys + room UUIDs are the routing+authorization identities;
  names/avatars are "presentation metadata only" (openclaw PR). Env: `BUZZ_PRIVATE_KEY`
  (nsec/hex, the only secret) [3rd-party Hermes docs].
- **Relay/mailbox**: `buzz-relay` (Rust/Axum) is the **single source of truth**. Every message,
  reaction, workflow step, review approval, git event = one signed event in one log. Backing:
  **Postgres** (events + full-text search), **Redis** (pub/sub, presence, typing), **S3/MinIO**
  (media/Blossom). **`buzz-audit` = hash-chain log.** Transport: WebSocket live delivery +
  REST fetch; inbound `auto` = WebSocket with **poll fallback** (default 4s) [3rd-party].
- **Membership** = the access boundary. A bridge "discovers every channel where the identity
  is a member and automatically subscribes"; channel membership, not a config list, gates
  reach [Hermes ACP doc, 3rd-party].
- **Delivery guarantees**: durable events persist in the Postgres log (replayable, searchable);
  **ephemeral observer frames (kind 24200) are NOT retained** by the relay — "Desktop must be
  online before the turn starts." So Buzz has two tiers: durable signed events vs ephemeral
  live frames.
- **NIPs/kinds** (primary README: NIP-01 events/filters, NIP-42 WS auth, NIP-98 HTTP auth;
  3rd-party Veritas pin adds NIP-11 metadata, NIP-29 relay groups/channels, NIP-09 delete,
  custom NIP-AO owner-attestation/observer, NIP-43 enforced membership; kinds: 9 message,
  40003 edit, 9005/5 delete, 24200 observer, 30617/1617 git). **Nostr is used for: portable
  keypair identity + Schnorr-signed events + a relay as the one durable audit log** — nothing
  more exotic ("Not blockchain").

## Q3 — Failure modes solved

1. **Context death** — durable actor identity + learned memory means a role survives without
   replaying every prior message (Bot "keeps a role over time"). Solves register's "important
   state must outlive any single model context" (Constitution §6).
2. **Role sprawl / over-staffing** — the 5-signal new-Bot rule + "smallest useful roster" is a
   discipline against exactly the specialist-roster overcooking the operator flagged (register
   §2 superseded, §8.9).
3. **Invisible coordination** — group chat + visible handoffs make who-owns-the-next-step
   auditable instead of implicit.
4. **Fire-and-forget async** — wake-on-message lets a sleeping actor receive work and reply
   later without a live session or the human orchestrating each step (the operator's stated
   "working without me" need).
5. **Identity-as-authority (Buzz)** — scoping by keypair, not permission flags, gives each
   actor its own audit trail and own reachable surface; a triaging agent can act "without the
   keys to the kingdom."
6. **One durable log (Buzz)** — message, patch, review, workflow, git in one signed,
   searchable, hash-chained event store: "ask the project a question and get an answer with
   receipts."

## Q4 — What QMX should REUSE (conceptually)

- **The 5-signal new-actor rule**, verbatim, as the QMX gate for spawning a new persistent
  Bot/Seat: distinct goal-or-ownership · tools/sources · working style · approval boundary ·
  schedule. Cheap, deterministic, and directly answers register open-Q "when is a new Bot
  warranted." Default to the smallest roster; prefer worker templates over standing staff.
- **Actor ≠ run** identity model: durable state (memory scope, ledger, missions, routines,
  preferences, relationships) binds to the Bot; the Agent is a disposable execution. (Register
  ontology 12–13 — this is convergent, not new.)
- **Description = durable rules, conversation = task** split → maps to QMX Role (declarative
  contract) vs Mission/Task (transient).
- **Wake-on-message semantics**: sleeping actor is woken by an inbound handoff, processes,
  replies later; live human message pre-empts background work.
- **Identity-first scoping (Buzz)**: each actor gets a stable `ActorId` (optionally a keypair)
  and its own reach/audit — QMX owns the keyspace; signing is optional and internal.
- **Two delivery tiers (Buzz)**: durable log events vs ephemeral live frames — QMX already
  wants durable task/ledger truth + ephemeral "watch the remote agent" streams (register §71).
- **Routine = one owner, schedule|event, with no-data/stale-data policy + test run** → QMX
  Scheduler/Cron primitive; the mandatory stale-data + approval fields are good hygiene.

## Q5 — What QMX should REJECT

- **Shared single account-level computer** (Grok) — operator demolished it: "no way in hell I
  want 40 research workers using one computer." Screens that are "not separate security
  boundaries" violate Constitution §10 and the Docker-per-worker ruling (register §62). INHERITED
  FASHION (Grok "designed for everyone").
- **Nostr / relay / signing as the transport** (Buzz) — operator: "I did not agree to use Buzz."
  secp256k1/Schnorr/npub/NIP-29/Blossom exist because Buzz is a **sovereign, multi-tenant,
  public, censorship-resistant** workspace for *strangers*. A single-operator daemon needs none
  of it. INHERITED FASHION (multi-tenant / public-web).
- **Chat/relay as source of truth** — Buzz makes the relay "the single source of truth"; QMX
  inverts this: ledger + task state are truth, messages are collaboration (register §33, §16).
  Do NOT let the bus become the record.
- **Marketplace surface** — Bot sharing via public link, third-party-bot terms, connector store,
  50-Bot cap: all multi-user/marketplace fashion. Irrelevant to one operator.
- **Persona-pack / ACP / buzz-cli external agent surface** — foreign-agent hosting QMX decided
  it does not need (register §8.1).
- **Group-chat-as-coordination** as the *primary* mechanism — visible handoffs are nice UX, but
  parallel workers must sync through the Task Graph, not chat (register §33: "must not
  synchronise through chat").

## Q6 — Contract QMX should OWN instead: the Agent Bus

A daemon-level, **non-authoritative** collaboration channel. Every durable actor (Bot/Seat)
has one durable **Mailbox**; the bus deploys deterministic delivery policy; state truth stays
in the Task Graph, Missions, and Desk Ledgers.

```
ActorId          = "seat:research/lead"  (stable) · { desk, role_ref, pubkey? (internal, optional) }
Mailbox          ops: send(Envelope) · poll(actor_id, cursor) → [Envelope] · subscribe(actor_id) (live) · ack(msg_id)
Envelope         { msg_id, from:ActorId, to:ActorId|GroupId, kind, mission_ref?, task_ref?,
                   correlation_id, reply_to?:msg_id, causation_id?, body, artifact_refs[],
                   priority, created_at, signature?, delivery_policy_ref }
MessageKind      handoff | reply | notify | review_request | status | question | approval_request
DeliveryState    DELIVERED (actor running/attached → live push)
                 QUEUED    (actor sleeping → durable store, picked up on next instantiation/poll)
                 WOKE      (WakePolicy matched → Scheduler instantiates an Agent for the Bot)
                 DEFERRED  (held for quiet-window / schedule)
                 DEAD_LETTER (expired / undeliverable → retention-bounded)
WakePolicy       { wake_on: priority>=N | kind∈{…} | from∈{…}, quiet_hours,
                   max_wakes_per_window, on_host_offline: queue|route_to_relay }  (deterministic; no LLM)
```

Semantics:
- **deliver-if-running / queue-if-sleeping / wake-if-policy** are decided by the deterministic
  Scheduler+WakePolicy, never by a model (Constitution §2).
- **Durability**: mailbox backed by a durable queue (append store); at-least-once + idempotent
  `msg_id` dedup; per-actor ack cursor. Retention is **bounded** (cf. Grok's 20-run cap) — the
  bus is not institutional memory.
- **Correlation**: `correlation_id` chains a handoff conversation; `reply_to`/`causation_id`
  build the DAG; `mission_ref`/`task_ref` link to authoritative state (references, not shared
  semantics — Constitution §12).
- **Non-authoritative invariant**: a message may *request* work but cannot *be* the work. A
  handoff becomes real only when it writes a Task (deterministic infra owns task state); the
  ReviewPolicy reviewer's authoritative act is the **task update**, the message is only the
  ping (register §31, §33). An Envelope MAY carry `ledger_ref`/`task_ref`; losing the mailbox
  loses collaboration convenience, never truth. The bus is rebuildable.
- **Machine-off-for-days** (register open-Q §3.5): mailbox lives in the daemon store on a
  node/VPS, not the laptop; if the whole daemon host is down, messages QUEUE and deliver on
  next boot — no external relay needed internally. External A2A/relay only as a *later adapter*
  for cross-host/cross-org, behind the same ActorId contract (register §34, §3.6).

### Names for the persistent named organizational actor (avoid "Bot")

| Name | One-line case |
|---|---|
| **Seat** | The durable named position at a Desk that a Role fills; the Agent merely occupies it, so mailbox/ledger/missions attach to the Seat — cleanest structural mirror of the Bot=identity / Agent=run split. |
| **Persona** | Durable named identity instantiated from a Role, carrying memory scope + preferences; already idiomatic (Buzz persona packs) and reads naturally in a UI roster. |
| **Steward** | Emphasizes end-to-end ownership of a desk's area/outcome — Grok's core "distinct area of ownership" rule made into a noun. |
| **Operative** | Mission-carrying persistent actor; fits the quant/ops register and the Goal→Mission→Task vocabulary without marketplace "teammate" softness. |
| **Principal** | The identity principal the Agent Bus addresses and that permissions/ledger/missions bind to — precise if the design leans on identity-as-authority (Buzz's model). |
| **Teammate** | Closest to Grok's own framing ("durable AI teammate with a name and a job"); self-explanatory in UI but the most generic. |

Recommendation: **Seat** (structural clarity) or **Persona** (idiom + UI legibility).

---

## Open questions this reference cannot settle
- QMX transport substrate (durable queue tech) — Buzz proves the *shape*, not the *stack*; register lists it unresolved (§3.6).
- Whether wake-on-message needs signing/authn internally (single-operator ⇒ probably not; keep `pubkey?` optional).
- Group-chat-style visible handoff as UX vs Task-Graph-as-truth boundary — needs a UI-session ruling (register §17).
- Exact retention window for mailbox events before dead-letter.
