# Rubric review 2 — AD-22..AD-25 increment (indicator protocol / structure lifecycle)

**Target:** `ARCHITECTURE-SPINE.md`, increment adding AD-22 (indicator protocol), AD-23 (TA-Lib pin), AD-24 (light/heavy), AD-25 (causal structure lifecycle), closing GAP-0031..GAP-0034.
**Scope of judgment:** the increment and its integration into the existing spine. Earlier ADs (AD-1..AD-21) treated as settled and not relitigated except where the increment touches them.
**Cross-referenced:** `docs/gap-report.md` (GAP-0031..0034 definitions), `docs/contracts/ct-16-indicator.yaml`, `docs/contracts/ct-17-causal-structure.yaml`, `docs/decisions/ADR-0006-indicators-and-structure.md`.

---

## Verdict

The increment closes most of GAP-0031..0034's decision surface well — warm-up, statefulness, batch/streaming equivalence, missing-value policy, reference arithmetic, drift handling, and light/heavy classification are all concretely and enforceably ruled. But it leaves **one whole dimension that both GAP-0031 and its own CT-16 stub explicitly called out as required — indicator/structure output type/shape — completely undecided, undeferred, and unflagged**, which is exactly the kind of silent gap that lets two factory agents building qmf-indicators/qmf-structure diverge on day one. A second real gap: custom indicator/structure extensions are invoked by name ("the extension shape") but never given packaging, location, or versioning treatment the way AD-2 gave calendar extensions. Recommend closing both before treating GAP-0031/0034 as fully ratified.

---

## Findings by checklist item

### (1) Do AD-22..25 fix the real divergence points one level down, and miss none?

Mostly yes, with one major miss.

**Covered well:**
- Batch/streaming behavioral equivalence — AD-22, enforced as an AD-4 tier-2 contract test (genuinely testable, not just declared).
- Warm-up length as fingerprinted contract surface, not-ready-vs-number distinction during warm-up.
- Missing-value policy — declared, typed-refusal-backed.
- Instance identity/dedup — content fingerprint (formula+parameters+instrument+timeframe), preventing bot-count-scaled instance explosion.
- Reference arithmetic and drift — AD-23's TA-Lib pin + comparison-suite-on-upgrade + contract-format-version mint.
- Light/heavy classification — AD-24's four-bound declare-and-benchmark-prove test, gate-enforced.
- Causal lifecycle scaffolding for structure — observed-at/confirmed-at/invalidated-at, append-only, confirmed-vs-unconfirmed evidence separation, no-privileged-families.

**Missed (see Finding 1, critical):** neither AD-22 nor AD-25 defines the **output** value type/shape for indicators or structure objects — only AD-22's *input* bulk form is pinned in `qmf-core`. This is not a minor omission: GAP-0031's own question text asks about "output alignment," and the pre-increment `ct-16-indicator.yaml` stub explicitly lists "input **and output** types" and CT-17's stub lists "output shape" among the named unresolved dimensions the gap exists to close. The increment resolves the input side and the failure/warm-up semantics but is silent on what a computed value concretely *is*.

### (2) Is every new AD's Rule enforceable, and does it prevent its stated divergence?

- **AD-22:** Yes — the batch/streaming equality claim is backed by an actual tier-2 contract test; dedup-by-fingerprint and warm-up-in-fingerprint are structurally enforceable via AD-10's single fingerprint implementation.
- **AD-23:** Yes — comparison suite + contract-format-version mint on any output change is a concrete, automatable gate.
- **AD-24:** Enforceable in mechanism (declare + benchmark-prove, merge-gate refusal on failure), but see Finding 3 — the benchmark target ("the live-path latency rung") is not yet a ratified number, so the gate has no concrete value to check against until AD-13 baselines land.
- **AD-25:** Partially. The append-only / invalidated-at-never-deletes rule genuinely prevents *repainting*. But the "Prevents: ...look-ahead structure entering evidence" claim rests entirely on a family author's self-declared, precisely-stated confirmation rule — there is no CI-checkable mechanism analogous to AD-22's equality test that would catch a family whose rule secretly looks ahead. The actual causality-verification machinery (registration gate + attempt counter) is explicitly deferred to the backtesting sitting (GAP-0016/0017). This is disclosed elsewhere in the document, so it's not hidden, but AD-25's own "Prevents" line overstates what V1's Rule mechanically enforces. See Finding 5 (medium).

### (3) Could anything in the updated Deferred table let two units diverge?

One real interaction, one clean pass:

- **Real interaction (Finding 3, medium):** "Numeric performance budgets | Await first measured baselines (AD-13)" is deferred, yet AD-24 requires indicators to prove they fit "the live-path latency rung" to claim light status *now*. Two agents building indicators before the first AD-13 baseline exists have no ratified number to target and could diverge on what they're building against.
- **Clean:** "MIS fan-out wiring for heavy indicators; which indicators ship in the V1 catalog" is correctly deferred to node/documentation time without creating package-level divergence risk — AD-24 already establishes that heavy placement doesn't change the CT-16 contract ("different placement, not a different species"), so the deferral doesn't let qmf-indicators itself diverge.
- **Not a Deferred-table problem but adjacent:** extension packaging (Finding 2) isn't in the Deferred table at all — it's simply absent, which is the failure mode checklist item 6 is asking about, not item 3.

### (4) Is named tech verified-current?

Yes for the only new named tech in this increment. AD-23 states TA-Lib "0.7.1 + 0.7.1, verified current 2026-08-20"; the Stack table row matches exactly ("verified 2026-08-20"), and the frontmatter `updated: '2026-08-20'` is consistent with the sitting date. No other new dependency is introduced by AD-22/24/25.

### (5) Do the new ADs contradict or weaken any Inherited Invariant or earlier AD?

No outright contradictions found; one real tension worth flagging:

- **Tension (Finding 4, medium):** AD-22 states the bulk form of exact values — "int64 arrays plus out-of-band scale/metadata" — is "defined in `qmf-core`" as "one representation workspace-wide." The Stack table lists numpy/pandas/pyarrow as "outer packages only," implying they are excluded from `qmf-core`. AD-22 never states whether "array" means a numpy array, stdlib `array.array`, or `tuple[int, ...]`. If the natural reading (numpy) is intended, this contradicts AD-6's zero-dependency-core mandate; if a stdlib type is intended, it's never said, which undercuts the "one representation workspace-wide" promise the same sentence makes.
- Everything else checked clean: AD-22's float-off-money-path carve-out correctly cites and defers to AD-7's boundary rule; AD-22's streaming-instance ownership correctly cites AD-15 (one feeder, unlimited readers); AD-25's composability correctly cites AD-17; both AD-22 and AD-25 correctly restate the default-deny dependency rule (qmf-core only) and correctly match the dependency-direction Mermaid diagram; both correctly preserve the don't-box-in invariant by explicitly permitting plain-Python/ungoverned use outside governed evidence; AD-24's node-territory placement of heavy indicators is consistent with the framework-vs-node split invariant; TA-Lib is correctly distinguished from the "strategy-family libraries prohibited" AD-6 clause (arithmetic reference, not a strategy framework).

### (6) Is a whole owned dimension left silent — neither decided, deferred, nor flagged?

Two dimensions qualify:

- **Output value types/shape (Finding 1, critical)** — as detailed above. Not in the Deferred table, not phrased as an open question anywhere in AD-22 or AD-25, simply absent, despite being named explicitly in both GAP-0031's question text and the CT-16/CT-17 stub invariants as required content.
- **Extension packaging/versioning for custom indicators and structure families (Finding 2, high)** — AD-22 and AD-25 both invoke "the extension shape" as an established pattern ("family authoring is the primary use case of the extension shape (same shape as AD-22's custom indicators)") but never state where such an extension lives, how it's packaged, or what version ladder governs it. AD-2 set a concrete precedent for exactly this class of question (calendar extensions: separate versioned package under `extensions/`, own SemVer ladder outside lockstep) — the increment doesn't extend that precedent or explain why indicator/structure extensions don't need it. The Structural Seed's `extensions/` block still lists only `qmf-calendar-forex/`, reinforcing that this was not addressed. A related sub-gap: AD-23's drift-detection mechanism (comparison suite + contract-format-version mint) is scoped to TA-Lib-wrapped indicators only; no equivalent exists for a custom (non-TA-Lib) indicator or structure family whose code changes without its declared formula/parameter identity changing.

Checked and found adequately handled (not silent):
- Indicator catalog scope — explicitly in the Deferred table ("which indicators ship in the V1 catalog... documentation time").
- Structure family catalog beyond the seed four — explicitly in the Deferred table, governed by AD-25's precise-rule bar.
- Structure object identity/fingerprinting — not restated in AD-25, but AD-10 already binds "every registered or stored artifact" and states fields are identity-by-default; this inherits cleanly rather than being silent.

Lower-severity silences noted (Findings 6–8 below) but judged not to rise to "whole dimension" status at this altitude.

### (7) Internal consistency: frontmatter vs body vs Deferred vs Conventions

Clean. Specifically checked:
- `binds` list contains GAP-0031..0034 and CT-16/CT-17, matching each new AD's own `Binds:` line; CT-08 correctly *excluded* from binds since AD-18 only claims "CT-08-adjacent."
- `scope` line correctly adds "indicator/structure invariants" and GAP-0001..0034 with the 0016/0017 carve-out preserved.
- Conventions table's new row ("structure 'family' = chart-object type, never a strategy/bot/Book grouping") matches AD-25's body text verbatim in meaning.
- Structural Seed comments for `qmf-indicators/` and `qmf-structure/` correctly cite AD-22/23/24 and AD-25 respectively.
- Dependency-direction Mermaid diagram shows `IND --> CORE` and `STR --> CORE` only, matching both new ADs' "depends on qmf-core only" statements and the default-deny rule.
- No banned vocabulary ("kernel", "plugins", "engine" for backtesting, "exam") introduced by the new ADs.
- No new Deferred-table row contradicts a new AD's body text.

---

## Findings summary

| # | Severity | Finding |
| --- | --- | --- |
| 1 | **Critical** | Indicator and structure **output** value type/shape is never defined — only indicator *input* bulk form is pinned in `qmf-core`. Named explicitly as required by GAP-0031 ("output alignment") and by the CT-16/CT-17 stub contracts ("input and output types," "output shape"), yet absent from AD-22/AD-25, the Deferred table, and any open-question flag. Highest-risk divergence point for the two units this increment targets. |
| 2 | High | Custom indicator/structure extension packaging and versioning is invoked ("the extension shape") but never specified — no location, no SemVer treatment analogous to AD-2's calendar extensions, and no AD-23-equivalent drift-detection mechanism for non-TA-Lib-anchored custom arithmetic or structure logic. |
| 3 | Medium | AD-24's light/heavy gate benchmarks against "the live-path latency rung," a number that doesn't exist yet — Deferred table defers "Numeric performance budgets" to first AD-13 baselines. Gate is real but currently unaimed. |
| 4 | Medium | AD-22's "int64 arrays" bulk form "defined in `qmf-core`" is not pinned to a concrete stdlib type; if numpy is intended it contradicts AD-6's zero-dependency core, and either way "one representation workspace-wide" isn't actually pinned to one concrete type. |
| 5 | Medium | AD-25's "Prevents: ...look-ahead" claim has no CI-checkable enforcement mechanism (unlike AD-22's equality test) — it rests on author self-declaration; the real causality-verification machinery is deferred to GAP-0016/0017. Disclosed elsewhere, but the AD's own Prevents line overclaims. |
| 6 | Low | Multi-timeframe indicator/structure inputs are architecturally unaddressed (single-timeframe implied by the fingerprint's `timeframe` component, never confirmed as the only shape). |
| 7 | Low | NaN/invalid-float output handling (as opposed to missing *input*) is unspecified for indicator arithmetic. |
| 8 | Low | Structure object's unconfirmed→confirmed transition mechanics (in-place field addition vs new-artifact-with-lineage-edge) is inferable from AD-5's re-derivation pattern but never stated for structure specifically. |

**Counts:** critical 1, high 1, medium 3, low 3.

---

## What's genuinely solid about this increment

- AD-22's batch/streaming equality law is backed by a real, automatable contract test — not just a declared aspiration.
- AD-23's drift-handling (comparison suite, contract-format-version mint on any output change, dual-reference registered artifacts) is a concrete, well-specified mechanism with a correctly cited precedent (TA-Lib 0.7.1's own MACD/MACDFIX/TRIX/ULTOSC period=1 change).
- AD-24's four-bound light/heavy test replaces "vibe" classification with a testable, per-configuration, merge-gate-enforced rule.
- AD-25 correctly threads the needle on family taxonomy (chart-object type, never strategy/bot/Book vocabulary) and correctly keeps the door open for operator-authored SMC/ICT-class families as first-class peers rather than second-class extensions.
- Dependency direction, Conventions table, Structural Seed, and frontmatter binds/scope are all kept in lockstep with the new ADs — no drift between the increment's parts.
