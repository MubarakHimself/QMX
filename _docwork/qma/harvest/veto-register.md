# QMA cheap-veto register (seat L4, 2026-08-29)

Every call the QMA sitting made on an **assumption or an inference** rather than a
direct operator quote, gathered so the operator can overturn any one in a single
line. Three classes are covered, per the seat spec:

1. every `.memlog.md` `(assumption)` entry (and the one inline `[ASSUMPTION]`
   tag that survived as a live call);
2. every operator-flagged withheld item (the three findings held back at
   memlog L102, re-listed as the five items at L224 / L260);
3. every `[ADOPTED ... 2026-08-28 ...]` tag that rests on an **inference** (a
   reading of the operator's words, or his silence) rather than a verbatim
   ruling.

Authority: the operator's meta-ruling (memlog L40 — *"decide, tag [ASSUMPTION],
present the finished spine for review"*) is why these are surfaced for a cheap
veto instead of blocking on an ask. The five items at L224/L260 were re-verified
in-spine as already resolved; they remain overridable. Nothing here is a
contradiction in the spine — each is a place where the operator's one word
changes the answer. Landing DECs are the L4 ruling DECs; landing GAPs are seat
L5's Deferred rows.

Line numbers are `.memlog.md` file lines (SRC-13).

## Class 1 — memlog `(assumption)` entries

| memlog line | What was assumed | Lands in | The one-line veto |
|---|---|---|---|
| L63 (`(assumption)`) / L133 (resolved) / L183 (narrowed) | That a **desk-level lead Quant exists as a persistent actor** at all — the operator was unsure ("do we have agents at a profile level?") and never ruled it directly; AD-9's Quant Ledger and AD-20's dead-letter address depend on it. Resolved [ADOPTED] by reading his ledger ruling against the granularity item. | AD-7, AD-9, AD-20; **DEC-0349**, DEC-0331, DEC-0338 | "There is no persistent desk-level lead Quant — drop the Quant Ledger and the lead flag." |
| L106 (`(assumption)`) | A **loopback-unauthenticated local proxy is accepted in v1** (the operator's existing OpenCodex workstation setup), registered as AD-26 variable `proxy.allow_unauthenticated_loopback` default **true**, ui-editable. | AD-15, AD-24, AD-26; **DEC-0344** | "Default `proxy.allow_unauthenticated_loopback` to false — refuse an unauthenticated loopback proxy." |
| L41 (inline `[ASSUMPTION]`, later removed at validation) | That **multi-account pooling under provider ToS is the operator's accepted practice** ("he already runs OpenCodex here"). Resolved by ruling QMA never pools; responsibility stays the operator's, held outside QMA. | AD-15; **DEC-0344** | "QMA must not register or route to any multi-account-pooling proxy." |

## Class 2 — operator-flagged withheld items

Held back at memlog **L102** (three findings, none applied at the time), then
carried as the five re-verified items at **L224** and **L260**.

| memlog line | What was assumed / applied from sources | Lands in | The one-line veto |
|---|---|---|---|
| L102 (1) / L140 / L182 → closed L205 | The **parent ban on `kernel` and `plugins`** was overridden for QMA with no explicit ruling in the memlog; closed from sources as **QMB/QMF/node-scoped**, so QMA adopts `plugin` and the qualified `RLM kernel`. | Conventions, Vocabulary, glossary; **DEC-0346** | "Refuse `plugin` and `RLM kernel` for QMA — use `extension` and `RLM interpreter` throughout." |
| L102 (2) → applied L104 | Reserving **`promote` for L17's live-zone act** and renaming memory promotion to **admit** and refinement promotion to **apply**. Vocabulary he cares about. | AD-18, AD-22, AD-25, Conventions closed verbs; **DEC-0345** | "Keep one verb `promote` across memory, refinement and the live zone." |
| L102 (3) → applied L105 | **Barring QMA-resolved secret values from crossing into OpenCodex's process** and refusing a local proxy that accepts unauthenticated connections (`auth_mode: none`, loopback bind). Constrains the OpenCodex setup he already runs. | AD-15, AD-24; **DEC-0344** | "Allow QMA to hand its resolved credentials to the local proxy process." |
| L224 (3) / L260 (3) | The **Windows VPS for the computer-use agent is PLANNED, not provisioned** — registered only once an `ExecutionEnvironment` of kind `desktop` exists; until then every computer-use tool fails its `check_fn`. | AD-25; **DEC-0336**, DEC-0341; **GAP-0070** | "The Windows VPS is already provisioned — register the desktop environment now." |
| L224 (2) / L260 (2) | (same as L106) the **loopback-unauthenticated proxy** default-true assumption, re-verified as resolved in-spine. | AD-15, AD-26; **DEC-0344** | "Default the unauthenticated-loopback variable to false." |
| L224 (1) / L260 (1) | (same as L41) **account pooling** as the operator's own practice, QMA never pooling. | AD-15; **DEC-0344** | "Bar QMA from any pooling proxy." |
| L224 (5) / L260 (5) | (same as L63) the **AD-7 desk-level lead Quant** as a persistent actor. | AD-7; **DEC-0349** | "No persistent lead Quant." |
| L224 (4) / L260 (4) | The **word `plugin`** adopted (ban QMB-scoped). | Conventions, Vocabulary; **DEC-0346** | "Refuse `plugin`; call it `extension`." |

## Class 3 — `[ADOPTED]` tags resting on an inference, not a quote

| memlog line | The inference (reading or silence, not a quote) | Lands in | The one-line veto |
|---|---|---|---|
| L133 | The **lead-flag [ASSUMPTION] was resolved to [ADOPTED]** by *reading* "task-level ledgers CONFIRMED correct; desk-level quant ledgers OK" against the granularity item "a desk-level lead quant keeps its own larger work ledger" — an inference from two lines, not a direct "yes, lead Quants are persistent actors." | AD-7, AD-9; **DEC-0349** | "That reading is wrong — desk-level ledgers do not imply a persistent lead actor." |
| L183 | **One lead flag per desk** and **the lead's mailbox as the undeliverable-Envelope catch-all** were INFERRED, never ruled, and now sit in Deferred; the interim rule (second flag = startup error, undeliverable → `dead_letter`) is the drafter's call, not the operator's. | AD-7, AD-20; **DEC-0349**; **GAP-0071** | "A desk may carry more than one lead flag" / "route undeliverable Envelopes to the lead, not `dead_letter`." |
| L39 | **D8 Graph/Loop/Skill adopted "from the transcript"** with the adversary hole closed by a **name split the drafter invented** (Graph Template = authored/stateless vs the daemon's Task Graph). The operator quote is "graphs, not loops" (T-4954); the *name split* is the inference. | AD-12, AD-13; **DEC-0340** | "Reject the Graph Template / Task Graph split — one 'Graph' object." |
| L43 | **D14 Knowledge adopted** because "the operator's doubt [was] resolved by ChatGPT's answer he did not refuse" — adoption rests on his **silence**, and register open-Q10 records he "never explicitly ratified it" and even asked "is a knowledge base even needed?" | AD-19; **DEC-0343** | "Drop the in-house Knowledge contract — RLM covers it; no KnowledgeSource port in v1." |
| L205 | The **`plugin` / `RLM kernel` adoption tagged "parent ban is QMB-scoped"** rests on reading `docs/glossary.md` (Kernel = retired name for qmf-core/Trading Node; "QMB is a library and a CLI, never an engine or kernel") plus "the operator uses the word himself" — an inference about ban scope, not an operator ruling on QMA's adoption. | Conventions, Vocabulary; **DEC-0346** | "The parent ban is platform-wide, not QMB-scoped — QMA may not adopt `plugin` or `kernel`." |
| L137 | The **threading node accommodation** tagged [ADOPTED 2026-08-28, T-5071/T-5081] — the operator named the threading node, but that "the plugin architecture cannot assume a zero start" is read as a ratified constraint; only its shape is unknown (Deferred). | AD-21; **GAP-0077** | "The threading node is not in scope for the QMA plugin model at all." |

## Class 4 — job-spec-named variables the sitting declined (surfaced, not minted)

| Source | What the operator's job spec names | Why the registry carries no row | The one-line veto |
|---|---|---|---|
| SRC-15 (the AD-26 variable list) | `sticky limit` and `budget hint` | Removed from AD-26 by the sitting as unowned — no owning AD, subsystem, units or default (memlog "AD-26 VARIABLE LIST CORRECTED"); their roles are carried by `continuation.max_consecutive`, `continuation.budget` and `rlm.depth_cap`. Lands in DEC-0325; changelog row V12. | "Register a sticky limit / budget hint anyway — owning subsystem X, units Y, default Z." |
| SRC-15 (the AD-26 variable list) | `journal retention` windows | The event journal is evidence — retained, backed up and never trimmed (AD-8, AD-23) — so it mints no retention or trim threshold; only the two bounded non-evidence streams (telemetry, mailbox delivery projection) carry retention/trim rows. Lands in DEC-0325; changelog row V12. | "Register a journal retention window anyway — the journal may be trimmed after N." |
