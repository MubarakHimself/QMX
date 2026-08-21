# QMB Architecture Spine — Rubric-Walker Review

Reviewer lens: **Rubric Walker** — judge the DRAFT QMB spine against the good-spine
checklist. Does it fix the real divergence points for the factory agents who will
build QMB, and miss none? Is every B-id's Rule enforceable and does it prevent its
stated divergence? Could anything under Deferred let two units diverge? Is named tech
verified-current? Does any B-id weaken an inherited AD? Is every dimension this altitude
owns decided / deferred / open — **especially the operational envelope**? Any
operator-dictated capability with no governing B-id?

Date: 2026-08-20. Read in full: QMB spine; QMF parent spine AD-1..41; intake INDEX,
rulings-for-backtesting, backtesting-direction-position (the spine's cited companion).

---

## Verdict

The spine nails the domain divergence points — the thirteen intake dossiers map cleanly
onto fourteen enforceable B-ids, named tech is verified-current, and no B-id contradicts
an inherited AD — but it leaves the **operational envelope's load-bearing centre
ungoverned**: the snapshot + sync-hub state model the operator dictated (DC-2) exists only
as an undecided diagram box, and QMB's own keystone artifact (the resolved run-config) is
never assigned a versioned contract identity.

---

## What holds (stated so the gate can see the review was thorough, not padding)

- **Coverage of the domain-divergence axis is genuinely complete.** Each intake spec's
  "one axis of divergence" has a governing B-id: clock seam → B-2; three fill/slippage/fee
  ports + split-candle → B-6; config compiler → B-3; adaptive sampler → B-8; provenance
  taint → B-7; canonical artifact vs PNG-throwaway → B-10; same-library research → B-9;
  fetch-at-runtime data → B-11; process-per-run → B-5; stream sets → B-12; MC/significance/
  walk-forward → B-14; distribution → B-13; doors → B-1. No domain divergence point from
  the INDEX is unmapped.
- **B-ids are mostly enforceable with a named mechanism**, not vibes: B-1 door parity =
  a tier-2 contract test; B-3 = schema-validated fixed-precedence compilation; B-4 =
  WriterId-scoped fragment files (and it correctly notes single-file append is non-atomic
  on Windows / only PIPE_BUF-atomic on Linux — a real trap caught); B-13 = the `uvx`-is-not-
  importable trap is called out so agents don't provision sandboxes the wrong way.
- **Named tech verified-current (my lens's explicit check):** click 8.4.2 (PyPI, released
  2026-06-24) matches exactly; optuna 4.9.0 (released 2026-06-01) is the current stable and
  the spine correctly refuses the 5.0.0rc pre-release; CPython 3.14 inherited. The click
  "pyreadiness ✗ is a metadata artifact" note is accurate. Pass.
- **No B-id weakens an inherited AD.** B-2's frontier clock is explicitly *not* AD-8's
  monotonic diagnostic kind; B-6 honours AD-8/AD-41's "financing/admin fee, swap only
  colloquially"; B-10's versioned metric set mirrors AD-41/AD-23 (arithmetic change = format
  mint); B-5's "no Ray/Docker/daemon" reinforces AD-6 + GAP-0006; B-13's two ladders honour
  AD-5. "Dukascopy primary" in B-11 is a *source* not a *venue*, and the parent already names
  it as a source in AD-21 — so it does not breach AD-9's no-named-broker rule.
- **The Deferred list does not open a divergence hole on the fidelity axis.** Because B-6
  forces every pre-GAP-0048 fill to the single `optimistic` taint value, there is only one
  legal fidelity identity until the taxonomy is ratified — two agents cannot mint two
  incompatible taxonomies in the interim. That seam is held correctly.
- **Sandbox *provisioning* is well governed** (better than a typical domain draft): package
  channel (B-13), data provisioning (B-11), concurrency bound (B-5) all name it explicitly.

---

## Findings (most-severe first)

### 1. HIGH — The sync-hub / registry-snapshot state model (DC-2) is ungoverned: no B-id owns it, and it is neither decided nor deferred

The spine's third mermaid diagram draws `HUB[(sync hub: registry + ledger files)]` with the
laptop and the 12–14 sandbox processes syncing to it and `HUB --> BUCKET`. **No B-id, no
Deferred row, and no Consistency-Convention governs it.** The Structural Seed has a `ledger/`
module but nothing for snapshot or hub-sync.

This is not a peripheral concern. The spine's own cited companion
(`backtesting-direction-position.md` §1, §3) calls the state-synced agent interface "the
**load-bearing centre of what you dictated**" and rules it as **DC-2**, which fixes four
things a factory agent cannot invent consistently on its own:

- registry snapshots are **immutable and fingerprinted**;
- the hub is the **single merge point** ("the hub import is the single merge point");
- a **`registry_as_of` instant + snapshot fingerprint on every label**, with a **stale-
  evidence refusal** when a run cites a ref a fresher snapshot shows superseded;
- **multi-sandbox write-back**: each sandbox writes its own WriterId-scoped stream,
  identical-fingerprint arrivals are idempotent accepts, **label-differing float artifacts
  are R-7 lineage siblings (never AD-10 collisions)**, true collisions refuse + alarm.

The QMB spine carries only a fragment of this: B-13's label field "registry-state as-of
(Book/BMS fragment fingerprints)" and B-4/B-5's *ledger*-fragment merge. It never states the
**registry** snapshot's immutability, the hub's role, the `registry_as_of` staleness refusal,
or the registry write-back/merge sibling-vs-collision rule. The Capability map row "'CLI
updates when I create a Book'" points only at the config compiler (B-3/B-13) — the artifact
that *reads* the registry — not at the mechanism that *delivers* the registry to a sandbox
and reconciles what sandboxes mint back.

**Why it matters at this altitude:** this is exactly the operational-envelope surface a
domain-focused draft skips ("the sync hub's ownership"), and it is the single most divergence-
prone thing left open. Two factory agents building QMB's distribution/sync layer will each
invent a snapshot format, a staleness rule, and a write-back merge — and the staleness
*refusal* is an AD-11 refusal the **library** must raise and the snapshot fingerprint is a
**label** field the library must stamp, so the semantics belong to QMB, not purely to ops.

**Smallest fix:** add a B-id (e.g. "B-15 — Registry snapshots + dumb sync hub; honest
staleness") carrying DC-2's four commitments, or, if the hub *deployment* is being pushed to
the node/ops sitting, add an explicit Deferred row that still pins the QMB-side semantics
(snapshot immutability + fingerprint, `registry_as_of` label field, stale-evidence refusal
on superseded ref, write-back sibling/collision rule) and cite where the deployment lands.
Right now it is drawn but undecided — the one state a spine must never leave a load-bearing
dimension in.

### 2. HIGH — The resolved run-config, QMB's keystone identity artifact, is never assigned a versioned contract identity (AD-5) or AD-10 field classification

B-3 makes the resolved run-config the centre of QMB's identity system: its fingerprint "is
the ledger key," and the Consistency-Conventions run-identity row makes "run id = fingerprint
of the resolved run-config + occurrence id." So the compiled resolved artifact is a
first-class, identity-bearing serialized artifact — a *new* artifact class produced by
compilation, distinct from the Book/BMS template fragments that feed it.

Yet B-3 specifies neither of the two disciplines the parent spine mandates for exactly such
artifacts:

- **AD-5:** "Every serialized contract carries its own integer format version stamped into
  every artifact; a format version's meaning never changes." Nothing in B-3 stamps the
  resolved config with a format version. Evolve the schema and old ledger entries become
  unreadable — "a system unable to read its own history," the precise failure AD-5 exists to
  prevent.
- **AD-10:** "every contract field is identity by default; display-only exclusion requires an
  explicit, versioned declaration." B-3 does not classify the resolved config's fields into
  identity vs display. If two agents classify a field differently (e.g. a timestamp or an
  output-dir path that should be occurrence/display), the *same run conditions* yield two
  different run-ids / ledger keys — and per AD-10's own warning the hashes *differ rather
  than collide*, so the ledger's collision detector never sees it.

B-3 cites "JSON-Schema-class per QMF AD-30 template discipline," but AD-30 governs the *Book/
BMS templates* (the fragments), not the *compiled resolved output*. The resolved artifact is
a derived compilation with its own identity surface, and that surface is unspecified. The
parent solved the analogous problem for templates in AD-30 (numbers inline, identity-bearing,
field classification declared); QMB's resolved config needs the same treatment and the spine
does not give it.

**Smallest fix:** in B-3, state that the resolved run-config is a versioned contract (own
integer format version per AD-5) whose fields carry AD-10 identity/display classification —
so its fingerprint (the run id and ledger key) is computed one way by every door and every
agent, and old ledger entries stay readable across schema evolution.

### 3. MEDIUM — B-4's ledger merge-view / "the Book sets the bar" read is not world/role-scoped, risking an AD-12 / AD-19 cross-world read

B-4 states the ledger "as read is a merge view over the fragments, and it is what 'the Book
sets the bar' reads," and the inherited row keeps "world=replay is QMB's legal world now …
paper=world live." Two inherited ADs constrain that exact read and the spine leaves the
scoping unstated:

- **AD-19:** rooms are instantiated **per world**; "a read that crosses worlds is a `policy
  rejection` refusal." A single merge-view over fragments from `world=replay` and `world=live`
  (paper) runs is a cross-world read.
- **AD-12 / AD-32:** the admission bar gates live money, no paper *role* may gate live, and
  "parity is structural." QMB produces `world=replay` evidence; whether such evidence may feed
  a `world=live` bar depends on the bar's declared `evidence_requirements.world` — it is not
  automatic, and B-4 presents the ledger→bar feed as if it were clean.

The spine claims to own this seam ("it is what the Book sets the bar reads") but never
reconciles it with the world/role scoping AD-12/AD-19/AD-32 impose. In v1 the risk is latent
if QMB is effectively single-world (replay), but the spine explicitly admits `paper=world
live` into QMB, at which point the merge crosses worlds and the bar-read touches the
live-money gate.

**Smallest fix:** in B-4, state that the ledger merge-view and the bar-read resolve **within
one world-and-role-scoped namespace** (AD-12/AD-19), and note that `world=replay` evidence
satisfies a `world=live` bar only where the bar's `evidence_requirements` declares it — so an
agent does not build a merge that silently crosses worlds.

### 4. LOW — The cited companion (DC-5) names the CLI command `qmx`; the spine names it `qmb`

`backtesting-direction-position.md` DC-5 — a companion this spine cites and inherits — rules
"CLI command `qmx`." The spine names product = QMB, command = `qmb`, throughout, and hangs its
whole "vocabulary law" on that name. `qmb` is internally coherent and probably the later
operator choice (and avoids colliding with the framework name QMX), but a factory agent
reading the cited companion will find `qmx` and could diverge on the single most visible
surface — the product face. Confirm which is canonical and, if `qmb`, mark DC-5 superseded so
one name travels downstream.

### 5. LOW — B-3's precedence places the Book and BMS config fragments at one tier with no tie-break or disjoint-keyspace guarantee

B-3's precedence is "invocation flags > run spec > **Book config fragment + BMS config
fragment** > workspace defaults." Book and BMS fragments sit at the *same* tier. AD-29 gives
them disjoint authority (Book: admission/sizing/doors/leash/profile; BMS: accounting/
constraints/KSA/reporting), so in principle their config key-spaces don't overlap — but the
spine never states that, so a same-key collision between the two fragments has undefined
resolution. An agent hitting one has no rule.

**Smallest fix:** state either that Book and BMS fragment key-spaces are disjoint by
construction (a collision is an `invalid input` refusal) or which fragment wins — so the "fixed
precedence" is fixed at every tier, including the one where two fragments coexist.

---

## Checklist trace (for the gate)

- Fixes the real divergence points for factory agents, misses none? **Domain axis: yes,
  complete. Operational-envelope axis: no — the sync hub / snapshot state model is missed
  (Finding 1).**
- Every B-id's Rule enforceable, prevents its stated divergence? **Yes, with named
  mechanisms — except the resolved-config identity surface B-3 leaves open (Finding 2).**
- Anything under Deferred let two units diverge? **No — the fidelity-taint collapse to a
  single `optimistic` value holds the GAP-0048 seam. But two live-but-ungoverned surfaces sit
  *outside* the Deferred list (the sync hub, Finding 1; the resolved-config version, Finding
  2) — undecided, not deferred.**
- Named tech verified-current? **Yes — click 8.4.2, optuna 4.9.0, CPython 3.14 all confirmed.**
- Any B-id weaken/contradict an inherited AD? **No outright contradiction. Two unstated
  scopings risk one (Finding 3: ledger world-scoping vs AD-12/19/32).**
- Every dimension this altitude owns decided/deferred/open — operational envelope especially?
  **Deployment (diagram only), sandbox provisioning (well covered, B-11/13/5), monitoring
  (inherited AD-14), backup (inherited AD-20, drawn as bucket). The one operational dimension
  neither decided nor deferred is the sync hub's ownership (Finding 1) — the exact gap the
  lens is told to hunt.**
- Operator-dictated capability with no governing B-id? **Yes — the state-synced agent
  interface + multi-sandbox write-back (DC-2), the operator's declared centerpiece
  (Finding 1).**

---

Review written to:
`C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/reviews/review-rubric.md`
