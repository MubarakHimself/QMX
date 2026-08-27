# Verification Plan — Epic 4: qmf-calendar-forex extension

- **Epic:** Epic 4 — `qmf-calendar-forex` extension (Wave 2, priority **L**). The first CT-02 market-hours calendar provider (`forex-17NY`), shipped as a versioned extension outside the seven-package roster.
- **Package under test:** `extensions/qmf-calendar-forex/` (src layout, module namespace `qmf.calendar_forex`, PEP 420 implicit). Module set observed from `coverage.json` (a data artifact) only: `__init__.py`, `_tzdb.py`, `_provider.py`, `_registration.py`, `_holidays.py`, `_bench.py`. **No source logic was read to author Section 4.**
- **Tier:** **T4 — LIGHTEST gate.** Executable scope is **L2 contract spot-check + L4 scenario participation only**, with the free **L0** static/doc gates and a small set of **L1** refusal witnesses that a pure contract-shape check cannot carry, closed by an **L6** requirements-fidelity review. A handful of tests, deliberately **not** a suite (contrast the T2 sibling plans' ~50).
- **FRs covered:** **FR-021** (the only FR in this epic).
- **Contracts:** **CT-02** (time & trading-calendar — owned by `COMP-QMF-CORE`, **implemented here as a provider**). **Consumed / preserved:** CT-04 (typed refusal — the `unavailable dependency` and cross-calendar refusals), CT-05 (`fp1` identity — the extension computes **none** of its own), CT-07 (lineage edge — the tzdata-pin-change edge recorded by the composition root, Story 4.3).
- **Author stance:** Section 4 (Independent Test List) was authored from the requirements corpus (`epics.md §Epic 4` Stories 4.1–4.3; `docs/contracts/ct-02-time-calendar.yaml`; `docs/contracts/ct-04-typed-refusal.yaml`; `docs/components/qmf-calendar-forex.md` incl. FM-1..FM-5; `docs/lenses/testing/test-strategy.md`; `docs/constitution.md`) **before any `extensions/qmf-calendar-forex/src/**` source file was opened**. Source is read-only evidence; a failing planned test is a **FINDING**, never a licence to edit source or weaken the test. The developer's own `tests/test_calendar_forex.py` and `tests/test_registration.py` are noted-as-present but are **not** this lane's tests and were not read.

> **Template-provenance caveat (load-bearing for the reader).** The two named authorities `_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` are **absent from this worktree** (`_bmad-output/test-artifacts/` does not exist — confirmed, as the sibling Epic 3 / Epic 5 plans also confirmed). The 8-section per-epic shape, the L0–L6 level architecture, and the "one behaviour, one level, lower level wins" rule are reconstructed from `docs/lenses/testing/test-strategy.md` + `docs/lenses/testing/fixtures-and-scenarios.md` (both ratified) and the P0/risk content embedded verbatim in this lane's task prompt.
>
> **Level-numbering reconciliation note.** This lane's task pins the gate as **"L2 contract spot-check + L4 scenario participation."** The sibling Epic 5 plan reconstructed a *different* index (L3 = contract, L5 = scenario) from the docs-lens level ordering. This plan **honours its own binding** (L2 = contract, L4 = scenario) and defines a coherent L0–L6 around it (Section 5). The **behaviours and gate content are identical either way**; only the level *index labels* differ. If the real `test-design-qa.md` is restored, reconcile the numbering — it is authoritative over this reconstruction.
>
> **P0/R-gate note.** The 15 P0/P1 assertions live in the absent handoff; **none is confirmed to bind Epic 4.** The risk gates below (`R-CAL-*`) are reconstructed from this epic's failure modes + the lane task's priorities. **`R-009`, named in the lane task, is unresolvable here** and, by its content ("its refusals have register entries"), belongs to the CT-31 control-window / CT-25 risk-journal surface (Epic 10), **not** to a market-hours calendar — see the Epic-Binding boundary in Section 1.

---

## Section 1 — Epic Charter & Scope-Under-Test

`COMP-QMF-CALENDAR-FOREX` is the **first market-hours calendar extension**: a separately-versioned package that implements the **CT-02 calendar-provider protocol for forex trading hours and supplies nothing else**. It lives in the workspace but **outside** the seven-package roster, on its **own SemVer ladder**, with exactly one **pinned `tzdata`** version that is forced onto the timezone path and **verified at import**, so trading dates and open-session windows stay identical across server moves, DST shifts, and tzdata updates. Its identity is the **rule set** (`forex-17NY` at a stated rule-set version) **plus the pinned tzdata version** — and only those enter fingerprints, computed by the single canonical `fp1` in `COMP-QMF-CORE`; the extension computes none of its own. (FR-021; CT-02; AR-02, AR-27; DEC-0100, DEC-0106, DEC-0108.)

**In scope (this epic, three stories):**

| Story | Title | Primary FR / CT | ACs |
|---|---|---|---|
| 4.1 | Extension scaffold + pinned tzdata + import-time tzdb verification | FR-021 / CT-02 (+CT-04) | 4 given/then blocks |
| 4.2 | `forex-17NY` market-hours provider implementing CT-02 (17:00 NY rollover + session schedule) | FR-021 / CT-02 | 5 given/then blocks |
| 4.3 | Explicit composition-root registration, identity participation, authority-boundary conformance | FR-021 / CT-02 (+CT-05, CT-07) | 4 given/then blocks |

**Epic-specific priority — a versioned rule set that stays identical across time and machines, or refuses.** The failures that matter for a calendar are all **silent-substitution** failures: a trading date derived by *formatting an instant* instead of applying the rule set; a fingerprint attested against a tzdb version the process never actually resolved; a cross-calendar `TradingDate` comparison that returns `equal` instead of refusing; a market-hours calendar quietly *answering* a day-boundary or news question it has no authority over. Verification weight therefore concentrates on **the 17:00 America/New_York accounting-rollover boundary** (the epic's correctness heart), **verify-or-refuse at import** (FM-1), and **the four authority/identity refusals** (FM-2..FM-5) — each proven as a **returned typed refusal**, never a best-effort answer and never a raised exception.

**Epic-Binding boundary — what this epic does NOT own (noted, not tested — except the duty to refuse).** The lane task's stated priorities name several concepts that, on the corpus, belong to **other epics**. Per the EPIC-BINDING RULE they are out of scope here; Epic 4's *only* legitimate relationship to them is **FM-4: refuse them as out of authority.**

| Task-named priority | Actual owner (corpus) | Epic | Disposition here |
|---|---|---|---|
| "session boundaries" (session schedule, weekend gaps, holidays) | `COMP-QMF-CALENDAR-FOREX` (Story 4.2) | **Epic 4** | **IN scope** — spot-checked |
| "dead zones (daily no-session + handover buffers)" | **CT-31** `daily_dead_zone` / `session_handover_buffer` (`COMP-QMF-RISK`) | Epic 10 | OUT — Epic 4 must only **refuse** (FM-4) |
| "news-window instrument scoping" | **CT-31** news window + currency-exposure scope; **SCN-0008** (`component: COMP-QMF-RISK`) | Epic 10 | OUT — Epic 4 must only **refuse** (FM-4) |
| "Feed has no 'actual' values … absence handled, not silently defaulted" | **COMP-CALENDAR-FEED** (news feed via CT-15); its `packages/qmf-data/.../calendar_feed.py` recorder; fail-closed is CT-31's | Epic 6 / Epic 10 | OUT — separate component |
| "R-009: its refusals have register entries" | CT-31 veto-path journaling / CT-25 risk-journal (`COMP-QMF-RISK`) | Epic 10 | OUT — Epic 4 owns no register/journal |

A market-hours calendar is one of **three distinct named calendar concepts** and is never conflated with the other two — the **day-boundary calendar** (account-scoped accounting-boundary rule) and the **news calendar** (`COMP-CALENDAR-FEED`). The forex extension answers **only market-hours questions** (`docs/components/qmf-calendar-forex.md`, DEC-0106). This boundary is not a caveat bolted on — it is the single most important thing this plan asserts about the task's priorities.

**Explicitly out of scope / deferred (not gaps in this plan):** the exact holiday set (extension-pinned data, no ratified spine list — GAP-0037 answered as *not* a core-contract gap); exact session open/close instants (session/trading-day length are "data no consumer may assume constant"); the specific pinned `tzdata` version string and rule-set version string (set at extension release, "no registry key exists yet"); Swap-Wednesday and any dated financing (explicitly dropped from V1). See Section 8.

---

## Section 2 — Authorities, Precedence & Requirement Inventory

**Precedence read (highest first):** `epics.md §Epic 4` (Stories 4.1–4.3) → `docs/contracts/ct-02-time-calendar.yaml` (Calendars block, invariants) + `ct-04-typed-refusal.yaml` + `ct-05-version-fingerprint.yaml` + `docs/components/qmf-calendar-forex.md` (FM-1..FM-5) + `docs/constitution.md` → `docs/lenses/testing/test-strategy.md` + `docs/lenses/testing/fixtures-and-scenarios.md` → (test-design-qa.md — absent, reconstructed) → (QMX-handoff.md — absent; no P0 confirmed to bind this epic).

**Requirement inventory (the map every planned test traces to):**

| Req | Source | Behaviour to prove | FM | Level |
|---|---|---|---|---|
| FR-021 / CT-02 | Story 4.1 b1 | Builds from `extensions/qmf-calendar-forex/` in src layout, own pyproject, **SemVer independent of roster lockstep**; ships **no `qmf/__init__.py`**, not published inside the `qmf.*` **roster** namespace (FM-5 boundary); declares **exactly one** pinned `tzdata` dependency | FM-5 | L0 |
| FR-021 / CT-02 | Story 4.1 b2 | On import it **forces TZPATH to the pinned tzdata**, reads the resolved tzdb version; **iff resolved == pin**, the CT-02 provider becomes ready and exposes rule-set identity + resolved tzdata version for downstream fingerprints | — | L1/L2 |
| FR-021 / CT-04 | Story 4.1 b3 | resolved tzdb **≠** pin at import → **`unavailable dependency` typed refusal**; does **not** become a usable provider; **no fingerprint attested** against the unverified tzdb | **FM-1** | L1 |
| FR-021 / AR-27 | Story 4.1 b4 | Changing the pinned `tzdata` is **at minimum a minor version bump** on this extension's own ladder | — | L0 |
| FR-021 / CT-02 | Story 4.2 b1 | Asked which trading date an instant belongs to → applies the **17:00 America/New_York** accounting rollover and returns a `TradingDate` carrying `forex-17NY` **identity + rule-set version in-band** | — | **L2** |
| FR-021 / CT-02 | Story 4.2 b1′ | **Never** derives the trading date by **formatting an instant** to a local date | **FM-3** | L1 |
| FR-021 / CT-02 | Story 4.2 b2 | Session schedule models **weekend gaps + pinned holiday set**; **session length and trading-day length treated as data, never constant**; **Swap-Wednesday not modeled** | — | L1/L2 |
| FR-021 / CT-04 | Story 4.2 b3 | Two `TradingDate`s under **different calendar identities** compared for equality → **typed refusal**; equality defined only within one identity | **FM-2** | L1 |
| FR-021 / CT-04 | Story 4.2 b4 | An **accounting-boundary (day-boundary) or news-event** question → **out-of-authority refusal** (market-hours only; those are separate named kinds) | **FM-4** | L1 |
| FR-021 / CT-05 | Story 4.2 b5 | Any calendar-derived fingerprint → **only rule set + pinned tzdata** participate, computed by the single canonical `fp1` in qmf-core; the extension computes **none of its own** | — | **L2**/L4 |
| FR-021 / CT-02 | Story 4.3 b1 | Made available via **explicit registration at the composition root through the named surface**, **never ambient package scanning**; distribution identity + version recorded to ride into downstream fingerprints | — | L1/L4 |
| FR-021 / CT-07 | Story 4.3 b2 | Re-deriving the same instant after the **tzdata pin changes** → exposed identity differs → **new distinct fingerprint + a lineage edge**, never a silent equality, earlier artifact **never rewritten** | — | **L4** |
| FR-021 / CT-05 | Story 4.3 b3 | A **binding-only** change (which venues/accounts use it) with **no rule-set change** → derived-artifact identities **unchanged** (binding ≠ rule-set identity) | — | **L2**/L4 |
| FR-021 / CT-02 | Story 4.3 b4 | Any attempt by the extension to **define a shared noun** (Venue, Account, Instrument, WriterId, TradingDate, CivilDate) → **conformance failure** at the Tier-2 gate; those are defined only in qmf-core | **FM-5** | L0/L2 |

*(FM-n = the failure-mode rows of `docs/components/qmf-calendar-forex.md`.)*

**Risk gates in scope (reconstructed — see the P0/R-gate note above):**
- **R-CAL-ROLLOVER** — the 17:00-NY accounting-rollover boundary is correct **to the nanosecond and across DST**; a trading date is **never** produced by formatting an instant (FM-3).
- **R-CAL-TZDB** — a fingerprint is **never attested against a tzdb the process did not resolve**; a pin mismatch **refuses** (`unavailable dependency`, FM-1) rather than proceeding or silently defaulting to the system tzdb.
- **R-CAL-AUTHORITY** — day-boundary / news questions are **refused** (FM-4) and cross-calendar comparisons are **refused** (FM-2); the calendar never answers outside its authority and never returns a bare `equal` across identities. **This gate is the correct in-scope treatment of the task's dead-zone / news-window priorities.**
- **R-CAL-IDENTITY** — identity = **rule set + pinned tzdata only**; a **binding** change does not change identity, a **tzdata** change does (new fingerprint + lineage edge, never a rewrite); the extension computes no `fp1` of its own (FM-5 / shared-noun boundary).

---

## Section 3 — Risk Assessment & Gates

Risk is scored on *silent-substitution likelihood × irreversibility of a wrong date/identity downstream*. A calendar's worst failures are quiet: a mis-rolled trading date, or a fingerprint that looks stable while the tzdb underneath it changed. Each headline therefore gets a **boundary or refusal assertion that names the exact returned category/identity**, not a happy-path "it returned a date."

| Risk | Failure it guards | Gate | Where proven |
|---|---|---|---|
| **R-CAL-ROLLOVER** | An instant one ns either side of 17:00 NY assigned the wrong trading date; a DST transition shifting the boundary; a date produced by `strftime` instead of the rule set | Boundary instants map to the correct `TradingDate` **carrying `forex-17NY` identity + version**, across a US DST change; the format-an-instant path is **refused/unsupported** | L2 rollover boundary (4.2-C1) + L1 FM-3 witness |
| **R-CAL-TZDB** | Import proceeds against a resolved tzdb ≠ the pin; a fingerprint attested on the system tzdb | Pin **match** → provider ready and exposes the resolved tzdata version; pin **mismatch** → **returned** `unavailable dependency`, provider unusable, **no** fingerprint attested | L1 FM-1 witness (both arms) + L0 single-pin gate |
| **R-CAL-AUTHORITY** | The forex calendar *answering* a day-boundary or news question; a cross-identity `TradingDate` equality returning `equal` | Day-boundary/news question → **out-of-authority** refusal (FM-4); cross-calendar comparison → **typed refusal** (FM-2) — never a computed answer | L1 FM-4 + L1 FM-2 witnesses |
| **R-CAL-IDENTITY** | A tzdata change silently reusing the old fingerprint; a binding change spuriously changing identity; the extension minting its own `fp1` | Only rule-set + tzdata enter `fp1` (qmf-core-computed); tzdata change → new fp + lineage edge; binding-only change → identity unchanged; extension defines no shared noun and no local fingerprint | L4 identity chain (ACC-1) + L2 identity/binding spot-check + L0 namespace gate |

**Prohibited-by-plan:** no planned test may (a) assert a **specific holiday date** or a **specific session open/close instant** as correct — the spine pins neither (Section 8); (b) assert a **specific pinned tzdata version string** or rule-set version value — set at release, no registry key; (c) exercise or assert **dead-zone / handover-buffer / news-window / feed-`actual`** behaviour as an Epic-4 responsibility — those are CT-31 / COMP-CALENDAR-FEED (Epic 10 / Epic 6); Epic 4 is asserted only to **refuse** them (FM-4); (d) assert a refusal by parsing an **exception string** — every boundary **returns** a CT-04 refusal whose `category` is asserted; (e) treat the developer's own in-package tests as evidence of requirement fidelity (that is the L6 read's job).

---

## Section 4 — Independent Test List (authored from requirements, pre-source)

Notation: `T{story}-U#` unit (L1), `-C#` contract (L2); `G#` static gate (L0); `ACC#` acceptance scenario (L4). "Assertion" states the observable pass condition. Every public boundary **returns** value-or-refusal; a refusal assertion checks the CT-04 `category` (`unavailable dependency` | the cross-calendar / out-of-authority category) + machine-readable context, **never a parsed exception string**. This is a **T4 lightest** list — a handful, weighted to the rollover boundary and the four refusals.

### Static / documentation gates (L0)
- **G1 — Extension-boundary / namespace gate.** The package builds from `extensions/qmf-calendar-forex/` in src layout with its **own** `pyproject.toml`; it ships **no `qmf/__init__.py`** and publishes no module that redefines a **roster** package; its version is **independent** of the roster lockstep ladder. *(Story 4.1 b1; AR-02, AR-07/AR-09; FM-5)*
- **G2 — Single-pinned-tzdata gate.** Exactly **one** `tzdata` version is declared as a dependency; the source declares **no** alternate/fallback tzdb path. *(Story 4.1 b1/b4; AR-27; DEC-0104)*
- **G3 — Dependency / no-shared-noun / no-own-fp gate.** The extension imports only `qmf.core` (+ its pinned `tzdata`); it defines **no** shared noun (Venue, Account, Instrument, WriterId, TradingDate, CivilDate) and calls **no** local fingerprint implementation — `fp1` is qmf-core's only. *(Story 4.2 b5, 4.3 b4; FM-5; DEC-0100, DEC-0108, DEC-0120)*

### Story 4.1 — scaffold + import-time tzdb verify-or-refuse (FR-021)
- **4.1-U1** (L1) — **FM-1 match arm.** With the resolved tzdb version **equal** to the pin, import makes the CT-02 provider **ready** and it **exposes both** its rule-set identity **and** the resolved tzdata version for downstream fingerprints. *(Story 4.1 b2; DEC-0104)*
- **4.1-U2** (L1) — **FM-1 mismatch arm (R-CAL-TZDB).** With the resolved tzdb version **≠** the pin at import, the package **returns an `unavailable dependency` typed refusal**, does **not** become a usable provider, and **no fingerprint is attested** against the unverified tzdb. *(Story 4.1 b3; FM-1; DEC-0106, DEC-0109)*

### Story 4.2 — forex-17NY provider implementing CT-02 (FR-021)
- **4.2-C1** (L2) — **Rollover boundary round-trip (R-CAL-ROLLOVER, headline).** For an instant at **16:59:59.999999999 America/New_York** the returned `TradingDate` is date **D**; at **17:00:00.000000000** it is **D+1**; the returned `TradingDate` carries `calendar_identity = forex-17NY` + rule-set version **in-band**. Repeat across a **US DST transition** (spring-forward and fall-back week) — the boundary tracks the NY zone, not a fixed UTC offset. *(Story 4.2 b1; CT-02 TradingDate + Calendars invariants; DEC-0106)*
- **4.2-U1** (L1) — **FM-3.** A request to derive the trading date **by formatting an instant** to a local date is **unsupported / refused**; the only supported path applies the rule set. *(Story 4.2 b1′; FM-3; DEC-0106)*
- **4.2-U2** (L1) — **Session schedule as data.** A weekend instant falls in a **gap** (no session), and the provider treats **session length and trading-day length as data** — a fixture with two different session lengths both resolve correctly (no constant-length assumption); **Swap-Wednesday is not modeled**. *(Story 4.2 b2; CT-02 "session/trading-day length are data"; DEC-0106)* — asserts the **shape/law**, not any specific published session time (Section 8).
- **4.2-U3** (L1) — **FM-2 (R-CAL-AUTHORITY).** Two `TradingDate`s produced under **different calendar identities** compared for equality → **typed refusal**; equality holds only **within** one identity. *(Story 4.2 b3; FM-2; CT-02 invariant; DEC-0106)*
- **4.2-U4** (L1) — **FM-4 (R-CAL-AUTHORITY — the Epic-Binding assertion).** A **day-boundary** question **and** a **news-event** question each → **out-of-authority refusal**; the forex calendar answers **only** market-hours questions and never computes a dead-zone / handover / news answer. *(Story 4.2 b4; FM-4; DEC-0106)*

### Story 4.3 — composition-root registration + identity participation (FR-021)
- **4.3-U1** (L1) — **Explicit registration, never ambient.** The provider is made available **only** via explicit registration through the named composition-root surface; it is **not** discovered by ambient scanning of installed packages, and its **distribution identity + version are recorded**. *(Story 4.3 b1; DEC-0100)*
- **4.3-C1** (L2) — **Identity = rule-set + tzdata; binding is separate (R-CAL-IDENTITY).** Under the CT-02 identity law, a fingerprint over a calendar-derived artifact incorporates **only** the rule set + pinned tzdata version; a change to the **binding** (which venues/accounts use it), with the rule set unchanged, leaves the derived-artifact identity **unchanged**. *(Story 4.3 b3; CT-05/CT-02 invariant; DEC-0108)*

### Acceptance scenario participation (L4)
- **ACC-1 — forex-calendar identity-bearing derivation chain (R-CAL-IDENTITY, R-CAL-ROLLOVER).** A bounded golden chain: the verified provider derives a `TradingDate` for a boundary instant and a `SessionWindow`; qmf-core's single `fp1` fingerprints a small derived artifact incorporating the calendar's rule-set + tzdata identity; then the **tzdata pin is changed** and the **same instant re-derived** → the exposed identity **differs**, the artifact carries a **new distinct fingerprint**, a **lineage edge** links old→new, and the **earlier artifact is never rewritten**. Asserts *identity participation + no-silent-equality + lineage*, with the component refusals already covered lower. *(Stories 4.2 b5 + 4.3 b1/b2; CT-05, CT-07; DEC-0103, DEC-0108.)* Nearest ratified downstream consumer for context: **SCN-0003** (a CT-12 split pins exactly one calendar identity) — noted, owned by Epic 3, not re-tested here.

### Requirements-fidelity review (L6)
- **L6-R1** — A senior review of the authored suite **against the requirements**, with `_provider.py` / `_tzdb.py` / `_registration.py` read as **read-only evidence** only. One question per test: *does it assert what CT-02 / the FM / the AC demand, or what the code happens to do?* Mandatory probes (each a FINDING if it fails): **(a)** the rollover boundary is asserted at the **nanosecond** either side of 17:00 **NY** and **across DST**, not at a fixed UTC hour; **(b)** the FM-1 mismatch arm asserts a **returned** `unavailable dependency` and that **no fingerprint was produced**, not merely that import raised; **(c)** the FM-4 refusal covers **both** a day-boundary **and** a news question, confirming Epic 4 only *refuses* the CT-31 / feed surface; **(d)** the tzdata-change chain asserts a **new fingerprint + lineage edge** (not just "identity string differs") and that the old artifact is untouched; **(e)** `_bench.py` and any internal module define **no shared noun** and bake in **no** session/holiday value that the contract says must be data; **(f)** no test asserts a specific holiday date, session time, or tzdata version string as correct against a non-existent spine value.

---

## Section 5 — Test-Level Assignment & Rationale (L0–L6)

**Level architecture (reconstructed; index labels honour this lane's L2=contract / L4=scenario pinning — see the reconciliation note):**

| Level | Scope | Tier |
|---|---|---|
| **L0** | static & documentation gates (import/namespace/dependency/single-pin/version-bump) | — |
| **L1** | unit **+ property** (named-behaviour, failure-mode, invariant witnesses) | tier 1 |
| **L2** | **contract conformance** — CT-02 provider public-shape spot-check | tier 2 |
| **L3** | integration — cross-component handoff | tier 2 |
| **L4** | **acceptance scenario** — golden-chain / scenario participation | tier 2 |
| **L5** | system / cross-epic E2E | tier 3 |
| **L6** | requirements-fidelity review (not a pytest node) | — |

**T4 lightest gate:** executable scope is **L2 + L4 only**, plus the free **L0** gates and the minimal **L1** refusal witnesses (FM-1/FM-2/FM-3/FM-4 and the format-an-instant path) that a contract-*shape* check cannot carry, closed by the **L6** read. **L3 and L5 are not exercised** — a calendar in isolation crosses only one seam (into qmf-core's `fp1`), which the L4 chain already carries; there is no store, venue, or multi-epic loop to integrate at this tier.

**One behaviour, one level — lower level wins (applied):**
- **Rollover boundary correctness** is the CT-02 *public output contract*, so it lives at **L2** (4.2-C1) as the round-trip; the *format-an-instant refusal* (FM-3) is a pure-unit policy decision → **L1** (4.2-U1), not re-asserted at L2.
- **The four refusals** (FM-1/FM-2/FM-4 + FM-3) are pure policy/boundary decisions needing no physical dependency → **L1** witnesses; the CT-04 *category vocabulary* is a contract-shape fact but is spot-checked inline in each witness rather than duplicated as a standalone L2 node at this light tier.
- **Identity = rule-set + tzdata, binding separate** is a CT-05/CT-02 *invariant over inputs* → stated at **L2** (4.3-C1); its *physical, end-to-end consequence* (new fp + lineage edge on a real tzdata-pin change) is exactly what a pure unit cannot show → the **one L4** chain (ACC-1).
- **Namespace / single-pin / no-shared-noun / no-own-fp** are static-structure facts → **L0** gates, not runtime tests.
- **Fidelity** (assertion matches requirement, not code) → the **L6** pass.

**Planned counts by level:**

| Level | Scope | Count |
|---|---|---|
| L0 | static/doc gates | 3 |
| **L1** | unit / failure-mode witnesses | **6** |
| **L2** | contract spot-check | **2** |
| L3 | integration | 0 (N/A at T4) |
| **L4** | acceptance scenario participation | **1** |
| L5 | system E2E | 0 (N/A) |
| **Executable total** | | **12** |
| L6 | requirements-fidelity review | 1 review pass (not a pytest node) |

*(L1 = 4.1-U1, 4.1-U2, 4.2-U1, 4.2-U2, 4.2-U3, 4.2-U4 = 6. L2 = 4.2-C1 rollover boundary, 4.3-C1 identity/binding = 2. L4 = ACC-1 = 1.)*

---

## Section 6 — Coverage & Weak-Spot Focus

Coverage floor is **80% per package**. The CT-01/CT-02 **primitive modules in qmf-core** require 100% branch — that mandate is on **qmf-core**, not on this extension (the extension *implements* a provider, it does not *define* the CT-02 primitive). **These figures come from `coverage.json` (a data artifact); no source logic was read to author Section 4.**

| File | Line | Branches missing | Signal |
|---|---|---|---|
| `.../qmf/calendar_forex/_provider.py` | 85.25% (87/96) | **9 missing** of 26 | The provider core (rollover + session schedule + the FM-2/FM-3/FM-4 refusals). 9 unexercised branches at the classic signature of **refusal arms never taken** — precisely FM-2/FM-3/FM-4 and the DST/weekend-gap paths this plan targets. |
| `.../qmf/calendar_forex/_registration.py` | 89.53% (63/68) | 4 missing of 18 | Composition-root registration (Story 4.3). Missing branches plausibly the ambient-scan-rejection / identity-recording arms (4.3-U1). |
| `.../qmf/calendar_forex/_tzdb.py` | 100% (46/46) | 0 of 8 | Import-time tzdb verify (Story 4.1 / FM-1). Fully covered by the developer's tests — the lane still asserts **both arms** independently (4.1-U1/U2) for fidelity. |
| `.../qmf/calendar_forex/__init__.py` | 100% (17/17) | 0 of 4 | Import surface. |
| `.../qmf/calendar_forex/_holidays.py` | 100% (5/5) | 0 | The pinned holiday set as **data** (5 statements) — confirms holidays are data, not logic (Section 8). |
| `.../qmf/calendar_forex/_bench.py` | 95.45% (38/38 lines, 2 branch miss) | 2 of 6 | Internal support module — **not named in any AC.** L6 probe (e): confirm it defines no shared noun and bakes in no session/holiday constant. |

**Out-of-scope sibling (do not test here):** `packages/qmf-data/src/qmf/data/calendar_feed.py` (77.6%, 41 missing branches) is **COMP-CALENDAR-FEED**, the news feed — Epic 6 / CT-15, and the home of the task's "feed has no `actual` values" concern. Its low coverage is **not** an Epic-4 finding.

**Weak-spot probes (planned; each a FINDING if it fails, never a source edit):**
- **WS-1** — Drive the **9 partial branches of `_provider.py`** by exercising *both* the rollover-D and rollover-D+1 arms across DST **and** each refusal arm (FM-2 cross-calendar, FM-3 format-an-instant, FM-4 day-boundary/news). The "refuse" arm is the one that shows as partial.
- **WS-2** — Cover the `_registration.py` ambient-scan-rejection / identity-recording arm (4.3-U1).
- **Coverage is not behaviour evidence:** a covered branch still requires its assertion to check the **returned refusal category** and the **in-band identity**, per DEC-0109/DEC-0108. Percentage never substitutes for a named-behaviour assertion; `_tzdb.py` at 100% is still asserted at the requirement level (4.1-U1/U2).

---

## Section 7 — Fixtures, Data & Environment

- **Determinism:** the CT-02 clock is injected (int64 UTC ns); **no fixture below the composition root reads the system clock**. Rollover fixtures pin **explicit UTC-ns instants** and the target NY wall boundary; DST fixtures use a **known spring-forward and fall-back date** so the boundary is checked against the zone, not a fixed offset. Equal semantic inputs replay to equal `fp1` (single qmf-core implementation; floats refused in identity).
- **tzdb fixtures (FM-1, both arms):** the **match arm** uses the extension's real pinned `tzdata`; the **mismatch arm** simulates a resolved tzdb version `≠` the pin (a controlled TZPATH / resolved-version double) and asserts the **returned** `unavailable dependency` refusal with **no fingerprint produced** — never a live tzdb swap and never a raised exception parsed for text.
- **Identity / lineage fixture (ACC-1):** derive under pin `A`, fingerprint via qmf-core `fp1`, then re-derive the **same instant** under pin `B`; assert `fp(A) ≠ fp(B)`, a **lineage edge** A→B, and that artifact `A` is **byte-unchanged**. The binding-vs-rule-set case (4.3-C1) changes only the **binding** and asserts `fp` **unchanged**.
- **Refusal harness:** boundaries **return** value-or-refusal; the harness asserts the CT-04 `category` + machine-readable context, never a parsed exception message (DEC-0109).
- **Session/holiday fixtures:** assert the **law** (weekend gap present; session/trading-day length treated as data; two different session lengths both resolve) — **never** a specific published session time or holiday date as an oracle (there is no ratified spine value; Section 8). Holidays enter as **data** from `_holidays.py`, not as asserted constants.
- **Source classes:** every fixture tagged `source-evidence | controlled-replay | synthetic`; a calendar is pure deterministic infrastructure, so **synthetic** fixtures are appropriate throughout and satisfy no trading-edge assertion (DEC-0054).
- **Env (tier 2):** the CT-02 contract spot-check runs in an **isolated per-package environment** so an undeclared import (e.g. a second tzdb source, or a roster package other than qmf-core) **fails** rather than resolving through the shared venv (DEC-0100, DEC-0102).
- **Run:** `uv run` from the worktree root (`.venv` dev group synced); property fixtures via `uv run --with hypothesis …` if hypothesis is absent.

---

## Section 8 — Execution, Exit Criteria & Untestable / Deferred

**Execution order:** L0 gates → L1 refusal/behaviour witnesses (FM-1/2/3/4 + format-an-instant + session-as-data) → **L2** rollover boundary + identity/binding spot-check → **L4** ACC-1 identity/lineage chain → **L6** requirements-fidelity review. Findings are **recorded, not fixed**; a red test that asserts a requirement the code violates is a **defect finding**, and source is never edited to make it pass.

**Exit criteria (T4 lightest sign-off for this epic):**
1. Each of the four failure modes FM-1, FM-2, FM-3, FM-4 has a passing **L1** witness that asserts a **returned** refusal category (or "unsupported"), and FM-5 has its **L0** gate.
2. The **rollover boundary** (4.2-C1) passes at the nanosecond either side of 17:00 NY **and** across one DST transition, with the returned `TradingDate` carrying `forex-17NY` identity + version in-band.
3. The **identity chain** (ACC-1) passes: tzdata-pin change → new `fp1` + lineage edge, old artifact untouched; binding-only change → identity unchanged (4.3-C1).
4. No planned test asserts a **specific holiday date, session open/close instant, or tzdata/rule-set version string** as correct (no spine value exists), and **no** dead-zone / handover / news-window / feed-`actual` behaviour is exercised as an Epic-4 responsibility.
5. The **L6** review returns no un-recorded fidelity gap — in particular probes (a)–(f).
6. Traceability complete: every test cites FR-021 / CT / AC / FM / DEC (and AR where relevant).

**Requirements judged untestable now (with reason — these are boundary/data facts, not plan gaps):**
- **U-A — The specific holiday set.** CT-02 states holidays are "in scope" but the actual list is **calendar-extension data, pinned per extension** with no ratified spine list (GAP-0037 answered as *not* a core-contract gap). Testable = holidays are **modeled as data** (`_holidays.py`) and a holiday instant falls in a non-session; **not** that any particular date is the correct holiday.
- **U-B — Exact session open/close instants.** "Session length and trading-day length are data no consumer may assume constant" (CT-02, DEC-0106). Testable = the **weekend-gap** and the **data-not-constant** law; **not** a specific numeric session-open time.
- **U-C — The pinned `tzdata` version string and the rule-set version string.** Set at extension release; "no registry key exists yet for them" (`docs/components/qmf-calendar-forex.md` Configuration). Testable = both **participate in fingerprints** and are **exposed** on the ready provider; **not** a specific version value.
- **U-D — AR-27 "minor version bump on tzdata pin change."** This is a **release-process** rule on the extension's SemVer ladder, checkable only as an **L0 documentation gate** over `pyproject.toml` / changelog at release time, not a runtime behaviour.

**Out of this epic's authority (EPIC-BINDING — noted, not tested; Epic 4's only duty is to *refuse* them via FM-4):**
- **U-E — Dead zones (daily no-session) + session-handover buffers.** Owned by **CT-31** `daily_dead_zone` / `session_handover_buffer` (`COMP-QMF-RISK`, **Epic 10**).
- **U-F — News-window instrument scoping** (currency-exposure records, widen-never-shrink, fail-closed, treated-as-affected). Owned by **CT-31** + **SCN-0008** (`component: COMP-QMF-RISK`, **Epic 10**).
- **U-G — "Feed has no `actual` values; absence handled, not silently defaulted."** Owned by **COMP-CALENDAR-FEED** (news feed via CT-15, **Epic 6**) with the fail-closed behaviour on missing data belonging to **CT-31** (Epic 10). The forex market-hours calendar has no `actual`-value concept.
- **U-H — "R-009: its refusals have register entries."** No `R-009` is defined in any authority present in this worktree (the handoff is absent). By content — journaling refused/blocked decisions on the veto path — it belongs to the **CT-31 control-window / CT-25 risk-journal** surface (`COMP-QMF-RISK`, **Epic 10**). A market-hours calendar owns **no register/journal**; its only refusals are the import-time `unavailable dependency` (FM-1) and the FM-2/FM-4 typed refusals, none of which write a register. **Unresolvable and out of scope here.**

**Plan caveat carried forward:** `test-design-qa.md` and `QMX-handoff.md` were **absent** from the worktree; the L-level index labels (L2 = contract, L4 = scenario) follow this lane's task binding and differ from the Epic 5 sibling reconstruction (L3 / L5). No P0/P1 assertion from the absent 15-item list is confirmed to bind Epic 4, and `R-009` is unresolvable. If the real handoff is restored, reconcile this plan's level numbering and P0/R-gate ids against it — they are authoritative over this reconstruction.
