---
name: 'Adversarial review 2 — AD-15..AD-21 and their seams'
type: review-adversarial
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation, updated 2026-08-20)
scope: 'AD-15..AD-21 only, plus every seam where they touch AD-1..AD-14, the Conventions table, the Stack table, and the Deferred table. Indicator/venue/risk contract detail discarded as later-sitting.'
created: '2026-08-20'
reviewer: adversarial
---

# Adversarial review 2 — the new decisions (AD-15..AD-21)

## Verdict

**The new sitting is not ratifiable as written.** AD-15..AD-21 are individually
reasonable rulings that were written without re-reading AD-1..AD-14, and the
result is seven build-blocking seams. Three of them are not "ambiguity" — they
are flat contradictions between clauses that both claim to be law: the registry
is ordered to write files that no package is permitted to own (N-01); AD-16's
record header puts two minted occurrence facts inside an identity-by-default
record, which destroys the content-addressed dedup AD-10 and AD-12 exist to
deliver (N-02); and AD-20 states a backup topology as a Rule that the Deferred
table on the same page calls "proposed-unratified … open question, not a
decision" (N-05).

The single worst outcome is N-04: **as the spine stands today, sealed research
data can leave through the raw archive, the processed room, or the nightly
bucket copy, with no refusal, no owner, and — because GAP-0016/0017 are
deferred — no detector.** The 12-month seal is the only anti-overfitting
guarantee in the entire framework, and it is currently a comment.

Of the six priority checks the operator named, five land findings. Check (f)
— DuckDB/SQLite leaking into `qmf-core` — is **clean at the letter**; the leak
that exists runs a different route (see (f) below).

Count: 22 findings — 7 CRITICAL, 10 HIGH, 5 MEDIUM.

---

## 1. Tiered finding index

| ID | Tier | Seam | One-line fix |
| --- | --- | --- | --- |
| N-01 | CRITICAL | AD-16 × AD-19 × AD-2 default-deny | Ratify `qmf-registry → qmf-data` as the first inter-library edge and add a seventh AD-19 room-role, the **registry room**, so CT-11's append-store contract owns lineage files. |
| N-02 | CRITICAL | AD-16 header × AD-10 × AD-12 × AD-8 | Amend AD-16's header: `stable id` is derived from the record's `fp1` fingerprint, `created-at` is declared occurrence/display-only, and `writer` + `sequence` are added per AD-8. |
| N-03 | CRITICAL | AD-16 internal (header lineage vs edge records) | Amend AD-16: the header carries only at-birth parent refs (identity-bearing); all later lineage lives **exclusively** in edge records, and readers never union the two. |
| N-04 | CRITICAL | AD-21 seal × AD-19 rooms × AD-20 backup × deferred GAP-0016/0017 | Amend AD-21: the seal is enforced as a `policy rejection` refusal at **every** qmf-data read boundary — raw, processed, research door, and restored backups alike — and this binds now, independent of GAP-0016/0017. |
| N-05 | CRITICAL | AD-20 rule × Deferred table × AD-15 × AD-21 | Demote AD-20's backup sentence to "the platform provides backup/restore **primitives**; scheduling, encryption keys, and topology are node/ops territory (deferred)" so the Rule stops contradicting the Deferred table. |
| N-06 | CRITICAL | AD-21 × AD-14 × AD-10 × AD-12 | Declare `correlation_id` excluded from `fp1` identity by explicit versioned declaration (AD-10), carried as a linking annotation only; causal linkage uses AD-16 typed edges. |
| N-07 | CRITICAL | AD-17 × AD-10 (`arrays are order-significant`) | Add to AD-10: multiplicity collections in registry records are canonically ordered by child fingerprint ascending unless the owning contract explicitly declares the collection order-significant. |
| N-08 | HIGH | AD-15 "writer" × AD-8 `WriterId` × AD-21 journal | Amend AD-15 to say its "writer" **is** the holder of an AD-8 `WriterId`, and AD-21 to say the journal is N streams (one per producing component), sequences gapless within a stream, cross-stream order by typed edges only. |
| N-09 | HIGH | AD-18 summary × AD-10 identity-by-default × AD-12 | Declare the plain-words summary an **identity** field explicitly in AD-18, and define the signature payload as exactly the record's `fp1` string; typo corrections mint a new record with a `supersedes` edge. |
| N-10 | HIGH | AD-21 splits × AD-8 `TradingDate` calendar identity | Amend AD-21: every split manifest pins exactly one calendar identity + version in-band, refuses rows carrying another calendar identity, and stores the seal as an explicit boundary `TradingDate` frozen against later re-derivation. |
| N-11 | HIGH | AD-19/AD-21 `source` × AD-9 `VenueId` | Define `source` in AD-19 as a core noun for data provenance, orthogonal to `VenueId`, with a stated test for when a provider is a venue; add a `corroborates` / `disagrees-with` edge type to AD-16. |
| N-12 | HIGH | AD-19/AD-20 IO surface × AD-11 six categories | Mint a seventh AD-11 refusal category, `storage failure`, now — before qmf-data is written — since categories are addable but never redefinable. |
| N-13 | HIGH | AD-19 rooms × AD-12 namespace rule | Amend AD-19: the six room-roles are instantiated **per world**; a read that crosses worlds is a `policy rejection` refusal. |
| N-14 | HIGH | AD-19 "rebuildable" × AD-5 never-lose-history | Amend AD-19: a processed artifact cited as an input by any result label is retained forever like raw; "rebuildable" licenses deletion only for uncited artifacts, and any rebuild pins the original calendar/tzdata version. |
| N-15 | HIGH | AD-15 purity × qmf-data's role | Amend AD-15 to name the exempt class: components owning an external resource (stores, recorders, adapters) are "stateful components"; purity binds pure-computation libraries only. |
| N-16 | HIGH | AD-18 card × AD-21 journal event | State that the registry promotion card is canonical and the journal's `promotion` event carries only that card's fingerprint plus `correlation_id`. |
| N-17 | HIGH | AD-17 × AD-9 × AD-12 comparability | Amend AD-17: Bot identity is its content; the Bot↔Book↔account binding is a separate dated binding record **outside** Bot identity, so one Bot runs paper and live as one artifact. |
| N-18 | MEDIUM | AD-21 × Conventions table | Rename AD-21's "calendar recorder" to "**news-calendar** recorder" to honor the spine's own never-bare-"calendar" convention. |
| N-19 | MEDIUM | AD-20 "encrypted" × AD-6 register | Either drop "encrypted" with N-05's demotion, or name the crypto dependency, its licence, and its key-custody owner in `DEPENDENCIES.md`. |
| N-20 | MEDIUM | AD-16 "JSONL-class" undefined | Pin JSONL-class in AD-16: one `fp1`-canonical JSON object per line, LF-terminated, append-with-fsync, no rewrite, rotation by size with a monotonic file ordinal. |
| N-21 | MEDIUM | AD-21 idempotent intake × AD-10 collision rule | State the intake idempotency key as `(source, source-native id, revision)` and exempt provider revisions from AD-10's collision alarm — a revision is a new artifact, not a collision. |
| N-22 | MEDIUM | AD-4 contract tests × AD-2 default-deny | Add to AD-2: a package may declare a **test-only** dependency on a contract's owning package purely to run its AD-4 contract tests, without that constituting a ratified runtime edge. |

---

## 2. The six priority checks, answered

### (a) AD-16's JSONL lineage vs AD-19's store contracts — who owns the lineage files?

**Nobody. And no package is permitted to.** This is N-01, and it is the seam
that blocks the build.

AD-16 binds `qmf-registry` and orders it to store lineage "as JSONL-class
append files with rebuildable local indexes." AD-19 binds `qmf-data` and
declares JSONL one of four stores, "each behind a QMF-owned contract so engines
are swappable implementations," bound to CT-10/CT-11. AD-20 then binds *both*
packages and says "raw originals and lineage are kept forever."

Now apply the **Dependency direction** rule, which is default-deny: "Until an
inter-library edge is ratified, no package may depend on any package other than
`qmf-core`; adding an edge is a spine amendment." And apply AD-2's mechanic:
"every dependency (including sibling packages) is declared explicitly in that
package's `pyproject.toml`; tier-2 runs each package's tests in an isolated
per-package environment so an undeclared import fails."

So `qmf-registry` has exactly two options, and both are conformant:

- **Unit A** implements `qmf/registry/_jsonl.py` — its own appender, its own
  framing, its own index rebuilder. Obeys AD-16, obeys default-deny, obeys
  AD-6. Result: a second JSONL append implementation that is *not* behind
  CT-11, which makes AD-19's "swappable implementations" false for the one
  store the registry actually uses.
- **Unit B** imports `qmf.data`'s CT-11 append store. Obeys AD-19's
  "QMF-owned contract" intent. Violates default-deny, and fails tier 2 the
  moment the isolated per-package environment refuses the undeclared import.

Both units read the spine correctly. They produce two incompatible lineage
file formats and two index rebuilders, and a merge between two sandboxes that
built different units silently produces two lineage graphs.

There is a second, quieter half. AD-19 enumerates **six** room-roles: ingest
door, immutable raw archive, processed, journal, research door, backup. None of
them is the registry. So the lineage and record files that AD-20 promises to
keep "forever" and to back up nightly live in **no defined room** — they are
outside the storage law that was written in the same sitting. Backup coverage,
retention, migration preflight, and partitioning all address rooms; lineage is
in none of them.

> **Fix (N-01):** ratify `qmf-registry → qmf-data` as the first inter-library
> edge and add a seventh room-role, the **registry room**, so CT-11's
> append-store contract owns lineage files.

---

### (b) AD-15 one-writer-per-stream vs AD-8 `WriterId` vs AD-21 journal — same concept or three?

**Three.** They are never reconciled, and the journal is the casualty. This is
N-08, with a sharp corollary that guts AD-21's stated purpose.

- **AD-8** makes `WriterId` an *identity*: "a first-class core noun: stable,
  durable, minted per (machine, role, stream), accompanied by a boot/epoch id."
  It is a per-stream identity that survives restarts.
- **AD-15** makes "writer" a *runtime exclusivity property*: "stateful
  components follow one-writer-per-stream with unlimited readers." It never
  says the acronym `WriterId`, never references AD-8, and never says whether
  one component may hold several `WriterId`s.
- **AD-21** mentions no writer at all. Its journal has "seven event types …
  linked by `correlation_id`."

**The unit pair.** The seven event types are produced by different components:
`decision` by the node/bot, `order` and `fill` by `qmf-venue`, `risk
transition` by `qmf-risk`, `promotion` by `qmf-registry`, `data quality` by
`qmf-data`, `control action` by node/ops.

- **Unit A** reads "the journal" as one stream. AD-15 then permits exactly one
  writer, so every component must funnel through a single journal writer. But
  `qmf-venue` and `qmf-risk` may not import each other or any package but
  `qmf-core` (default-deny), so the funnel type must be defined in `qmf-core`
  — while AD-21 binds the journal contract (CT-13) to `qmf-data`. The funnel
  cannot be built where it must live.
- **Unit B** reads "the journal" as seven streams with seven `WriterId`s. It
  builds cleanly. And then it cannot answer the question the journal exists to
  answer.

**The corollary, which is the real damage.** AD-21's "Prevents" line reads
"untraceable events." But AD-8 forbids the trace: `(instant, writer,
sequence)` is "a **replay-determinism device with no causal meaning** —
causality tests refuse at equal instants rather than tie-break," and "instants
alone never totally order events." Sequence is strictly increasing *per
writer*. So for a `decision → order → fill` chain written by three writers,
there is no ratified way to establish the order. `correlation_id` groups them;
it does not sequence them. **AD-21 promises a traceability that AD-8
explicitly refuses to deliver.**

Third defect in the same seam: AD-8 says sequences are "strictly-increasing,"
not gapless. A unit that mints one `WriterId` per *process* and writes three
streams through it still emits strictly-increasing sequences — with gaps. A
reader cannot then distinguish a gap-by-design from lost records, which is the
one thing an evidence sequence is for.

> **Fix (N-08):** amend AD-15 to say its "writer" *is* the holder of an AD-8
> `WriterId`, and AD-21 to say the journal is N streams (one per producing
> component) with gapless per-stream sequences, cross-stream order established
> by typed lineage edges only.

---

### (c) AD-18's plain-words summary vs AD-10's identity rules — identity or display-only?

**Undecided, and both readings are defensible and harmful.** This is N-09.

AD-10: "every contract field is **identity by default**; display-only
exclusion requires an explicit, versioned declaration in the contract — never
an implementer's judgment call."
AD-12: "**Human display names live outside identity.**"
AD-18: "a mandatory plain-words summary field readable by a non-technical
human as part of the record itself," on a "signed immutable record."

- **Unit A** applies AD-10 literally: the summary is identity, it enters
  `fp1`. Consequence: fixing a typo in a human's prose mints a new fingerprint,
  which under AD-5 is "a new artifact with its own fingerprint and a lineage
  edge to the old one" — so a typo requires a **new human signature** on a new
  promotion occurrence. Ugly, but sound.
- **Unit B** applies AD-12's "human display … outside identity": the summary is
  display-only, excluded from `fp1`. Consequence: **the signature does not
  attest the words the human read.** The summary can be swapped afterward
  without breaking the fingerprint or the signature. On the one artifact whose
  entire stated purpose is "promotions with no durable, human-legible record,"
  the human-legible part is the unattested part.

Two units, two fingerprints for the same promotion, and AD-10's collision rule
does not catch it — differing hashes are not a collision, they are two
artifacts. Cross-sandbox dedup fails silently.

**Additional hole in the same clause:** AD-18 mandates a "signed immutable
record" and *no AD anywhere defines what signing means*. AD-10 defines
fingerprints, not signatures. The signature payload, the algorithm, the key
custody, and whether the signature covers the fingerprint or the bytes are all
unstated — and asymmetric crypto is a dependency `qmf-registry` does not
currently have, with no `DEPENDENCIES.md` line (AD-6) and no owner.

> **Fix (N-09):** declare the plain-words summary an identity field explicitly
> in AD-18 (satisfying AD-10's "explicit, versioned declaration" bar), and
> define the signature payload as exactly the record's `fp1` string.

---

### (d) AD-21 splits-on-trading-dates vs AD-8 TradingDate-carries-calendar-identity — which calendar?

**Unstated, and the omission makes multi-venue splits undecidable and the seal
mobile.** This is N-10, and it has three independent teeth.

AD-21: "boundaries on trading dates or instants, **never civil dates**."
AD-8: "`TradingDate` carries its calendar identity and version in-band;
equality is defined only within one calendar identity; **cross-calendar
comparison is a typed refusal**." AD-9 makes six venues normal, not special.

**Tooth 1 — undecidable classification.** A split manifest bounded on a
`TradingDate` in `forex-17NY v3` cannot classify a row whose `TradingDate`
carries a different calendar identity; the comparison is a typed refusal per
AD-8. Unit A pins one calendar and refuses (or silently drops) every other
venue's rows. Unit B carries a per-calendar boundary map. Both conform; the two
manifests fingerprint differently and assign **different train/test membership
for the same declared intent**. AD-21's "fingerprinted" makes both auditable
and neither correct.

**Tooth 2 — "12-month" is inexpressible in the ratified vocabulary.** AD-8's
core time vocabulary is "Instant, CivilDate, TradingDate, Duration (signed
int64 ns), Interval, SessionWindow." There is no month. So a unit implementing
"the 12-month seal" must either do `CivilDate` arithmetic — which AD-21 bans as
a boundary — or use `365 × 86400 × 10⁹` ns, which is not twelve months across a
leap year. Two units, two seal boundaries, differing by a day, both conformant.

**Tooth 3 — the seal boundary moves under tzdata.** AD-8 puts the tzdata
version into calendar identity and into fingerprints; AD-5 says re-deriving
under a newer calendar/tzdata version "produces a new artifact with its own
fingerprint." A `TradingDate`-bounded seal therefore *re-derives* on a tzdata
bump, and AD-2 says a tzdata pin change is "at minimum a minor bump" on the
extension's own ladder — outside lockstep, so it can happen without any roster
release. The seal boundary shifts, and data that was inside the no-peek lock
can fall outside it. **A no-peek lock whose boundary drifts is a leak.**

> **Fix (N-10):** every split manifest pins exactly one calendar identity +
> version in-band, refuses rows carrying another calendar identity, and stores
> the seal as an explicit boundary `TradingDate` frozen against re-derivation.

---

### (e) GAP-0016/0017 deferral vs AD-21's research door — can data leave for research with no gate at all?

**Yes. Today, a fully conformant implementation ships with no gate whatsoever.**
This is N-04, the worst finding in the review.

AD-19 names a "**split-governed** research door." AD-21 supplies split
manifests and says "the 12-month seal is a no-peek lock … the sealed period
gets one logged final look and is never silently recycled." Neither clause
states **an enforcement point, a refusal category, an owner, or a failure
mode**. AD-11's `policy rejection` category exists and would fit — nothing
binds the door to return it. AD-12 supplies write separation ("a non-live world
may never write into the live evidence namespace") and no read separation.

**The unit pair.**

- **Unit A** builds the research door as a read API taking a split-manifest
  fingerprint and returning `policy rejection` for out-of-manifest reads.
- **Unit B** builds the research door as a Parquet directory the researcher
  points DuckDB at — which is precisely what AD-19 names DuckDB for ("local
  analytics") — with the split manifest as advisory metadata alongside.

Unit B violates no clause of AD-15..AD-21 and leaks the sealed period on day
one.

**And the seal is escapable even in Unit A.** The seal is scoped to one room;
the facts are not. AD-19's raw archive holds the same period. AD-19's processed
room is "always rebuildable from raw," so a researcher can *reconstruct* the
sealed period without touching the door at all. AD-20 puts a nightly copy of
everything in an object-storage bucket with a "documented restore path" and
"automated sample-restore tests" — the restored copy carries no seal. Four
routes to the sealed data; one of them is governed.

**And nothing can detect the peek.** GAP-0016 (look-ahead registration gate)
and GAP-0017 (attempt counter) are deferred, with the memlog recording the
consequence as knowingly accepted: "artifacts registered before that sitting
will lack causality evidence (not retroactively reconstructible)." So there is
no gate at registration and no tally of attempts. The only remaining
detector would be the journal — and **"one logged final look" maps to none of
AD-21's seven event types**; `data quality` and `control action` are both
wrong, and event types are addable but not redefinable, so guessing now is
expensive later.

The operator accepted losing *causality evidence*. What is actually being lost
here is different and larger: **the seal itself.** That is not a backtesting
concern that can wait for the backtesting sitting; the archive being written
between now and then is the archive that gets peeked at.

> **Fix (N-04):** the seal is enforced as a `policy rejection` refusal at
> every qmf-data read boundary — raw, processed, research door, and restored
> backups alike — and this binds now, independent of GAP-0016/0017; the "one
> final look" is a named `control action` subtype.

---

### (f) AD-19 DuckDB/SQLite vs AD-6 zero-dep core — any leak into core?

**No leak at the letter. Confirmed clean.** DuckDB is a PyPI package and sits
in `qmf-data` per AD-19's binding line; `sqlite3` is stdlib; Parquet's pyarrow
is listed in the Stack table as "outer packages only." AD-6's rule —
"`qmf-core` takes zero outside dependencies (stdlib only)" — is not violated by
anything AD-19 or AD-20 says. AD-13's "`qmf-core` imports in well under one
second" survives intact.

**But there are two indirect paths worth stating, neither of which is the one
the check was looking for:**

1. **Into the registry, via N-01.** The paradigm line says "runtime concerns
   enter through protocols the core defines," and AD-3 says "seams are
   `typing.Protocol`s." AD-19's stores are seams ("swappable implementations"),
   so the paradigm points at `qmf-core` defining them — but a store Protocol
   must name the row/table/schema types it moves. A unit that types those
   signatures with pyarrow puts pyarrow in `qmf-data`'s **public type
   surface**, so every CT-11 consumer inherits it under pyright-strict. Resolve
   N-01 by ratifying `qmf-registry → qmf-data`, and the registry — the package
   the sandbox model most wants light — inherits pyarrow and duckdb
   transitively. **Recommendation:** when ratifying N-01, require CT-11's
   protocol signatures to be stdlib-typed at the boundary.

2. **Into `qmf-registry`, via AD-18's signature.** See N-09: "signed immutable
   record" implies asymmetric crypto in a package that currently declares
   nothing, with no `DEPENDENCIES.md` entry. Same for AD-20's "encrypted"
   backup (N-19).

---

## 3. Further unit pairs — new decisions against old law

### N-02 (CRITICAL) — the registry header breaks content-addressed dedup

AD-16's common header is "kind, **stable id**, contract format version,
**created-at**, lineage references." Two of those five are minted occurrence
facts, and AD-10 says "every contract field is identity by default."

AD-12 exists to make this impossible: "the computation identity is
content-derived (from label parts) **so identical work from two sandboxes
deduplicates and merges**; the occurrence record (when/where/by whom it ran) is
separate provenance **outside identity**." AD-8 agrees: "the identity of a
stored record is its AD-10 fingerprint."

- **Unit A** mints `stable id` as a UUID and `created-at` from the injected
  clock, both identity by default. Two sandboxes computing the byte-identical
  artifact produce two records with two fingerprints. **Dedup fails, merge
  produces duplicates,** and this is the exact defect the prior review logged
  as F-22 ("random run ids and content-addressed merge cannot both be true"),
  reintroduced by the new sitting through a different door.
- **Unit B** derives `stable id` from the fingerprint and declares `created-at`
  display-only. Dedup works — and Unit B has made an implementer's judgment
  call on a display-only exclusion, which AD-10 forbids in as many words.

**Third defect, same header:** AD-8 requires "every record stream carries a
per-writer strictly-increasing sequence" and AD-14 restates it — "journals and
every evidence stream store int64 UTC ns + writer + sequence per AD-8." AD-16's
enumerated header has **no writer and no sequence**. A unit following AD-16's
"tiny common header" literally produces registry records with no ordering key
and no gap detection.

> **Fix (N-02):** `stable id` is derived from the record's `fp1` fingerprint,
> `created-at` is declared occurrence/display-only, and `writer` + `sequence`
> are added to the header per AD-8.

### N-03 (CRITICAL) — AD-16 gives lineage two homes, and the header's copy can never be complete

AD-16 puts "lineage references" in the record header **and** defines lineage as
"append-only typed edge records." One fact, two storage locations, no stated
precedence.

The contradiction is structural, not stylistic. Records are immutable, and
lineage **accrues** — a `supersedes` edge is minted long after the superseded
record was written. The header therefore *cannot* hold complete lineage, ever.
So a reader must union header refs with edge records, and the two can disagree
(Unit A writes parents only in the header; Unit B writes them only as edges;
Unit C writes both and they drift). Meanwhile the header copy is
identity-by-default, so it is frozen into the fingerprint while the edge set
keeps growing.

> **Fix (N-03):** the header carries only at-birth parent refs
> (identity-bearing); all later lineage lives exclusively in edge records;
> readers never union the two.

### N-05 (CRITICAL) — AD-20 ratifies what the Deferred table calls unratified

Two clauses on the same page, both stated as law:

- **AD-20 Rule:** "Backup is an inbuilt platform feature: nightly, encrypted,
  versioned, off-machine (object-storage bucket), with automated sample-restore
  tests and a periodic full-restore rehearsal. **Topology:** trading-node VPS
  records and syncs down; workstation holds the working archive; the bucket
  catches nightly copies."
- **Deferred table:** "Deployment topology, infra strategy, operations envelope
  (**incl. the proposed-unratified nightly object-storage backup**) | Node/ops
  sitting — **open question, not a decision**."

A reader cannot tell whether the nightly bucket backup is law. This alone
blocks ratification.

It is also **internally impossible as an "inbuilt platform feature."** AD-15:
"QMF never spawns threads or background work — the application owns all
concurrency," and "async APIs exist only at the venue network edge, never in
core or the libraries." AD-21: "applications own **scheduling**, retries,
supervision, and UI." "Nightly" is a schedule and "off-machine" is network I/O
from a library. Every clause of the new sitting says QMF cannot do this;
AD-20 says it is inbuilt.

> **Fix (N-05):** demote AD-20's backup sentence to "the platform provides
> backup/restore **primitives**; scheduling, encryption keys, and topology are
> node/ops territory (deferred)."

### N-06 (CRITICAL) — `correlation_id` is a log id doing evidence work

AD-14 introduced `correlation_id` for **logs**, and went out of its way to
separate the two worlds: "**Logs are not journals:** operator/diagnostic log
text renders timestamps as UTC ISO-8601 … journals and every evidence stream
store int64 UTC ns + writer + sequence."

AD-21 then makes that same field the journal's structural link: seven event
types "linked by `correlation_id`."

- **Unit A** generates `correlation_id` the way log correlation ids are
  generated — a fresh UUID per request/tick. It is identity by default
  (AD-10), so it enters every journal record's fingerprint. **Two replays of
  the same decision produce different fingerprints.** Replay determinism and
  cross-sandbox dedup both die.
- **Unit B** makes it deterministic and content-derived so replay reproduces
  it — at which point it is no longer a correlation id, and AD-14's logging
  contract (one id following one event across components, including components
  outside QMF) is broken.

> **Fix (N-06):** declare `correlation_id` excluded from `fp1` identity by
> explicit versioned declaration, carried as a linking annotation; causal
> linkage in journals uses AD-16 typed edges.

### N-07 (CRITICAL) — multiplicity has no canonical order, and AD-10 says order is identity

AD-17: "a Bot contains one-or-more confluences; a confluence contains
one-or-more levels, triggers, and confirmations; components may compose."
AD-10's `fp1` recipe: "**arrays are order-significant.**"

Confluences are semantically unordered — they are conditions that co-occur.
AD-17 never says whether these collections are sets or sequences.

- **Unit A** stores confluences in author order. Bot `[A,B]`.
- **Unit B** canonicalizes by sorting on child fingerprint. Bot `[B,A]`.

Same bot, two fingerprints, no dedup, no merge — the failure AD-10's "Prevents"
line names first ("two conformant implementations disagreeing"). Composition
makes it worse: AD-17 permits "several levels forming one composite level," and
nothing says whether flattening a composite preserves identity, so a
structurally identical bot expressed flat and expressed composite are two
artifacts.

> **Fix (N-07):** multiplicity collections in registry records are canonically
> ordered by child fingerprint ascending unless the owning contract explicitly
> declares the collection order-significant.

### N-11 (HIGH) — `source` and `VenueId` are two identity axes that were never introduced to each other

AD-19 makes `source` a first-class bitemporal field ("every external fact
carries event-time, known-at, **source**, and revision"). AD-21 leans on it
hard: "Tick sources are separately identified (Dukascopy history vs broker
feed) … disagreements between sources stay visible with lineage, never merged."
AD-9 says "instrument identity is (venue, venue's own symbol)."

- **Unit A** mints Dukascopy as a `VenueId` (AD-9 permits nothing else for a
  distinct legal entity). Then Dukascopy-EURUSD and broker-EURUSD are **two
  distinct instruments** — so by construction they cannot "disagree," and
  AD-21's disagreement-preservation clause has no subject.
- **Unit B** treats `source` as an attribute on a single instrument, which is
  what AD-19/AD-21 read like — and violates AD-9's identity rule, mixing two
  providers' records into one instrument's history, which is precisely what
  AD-9's "Prevents" line forbids ("two brokers' records mixing").

Compounding: AD-16's edge vocabulary is `parent / derived-from / supersedes /
promoted-from / occurrence-of`. **None of them expresses "these two facts
disagree."** So even a unit that wants to obey AD-21's "stay visible with
lineage" has no edge type to write.

> **Fix (N-11):** define `source` in AD-19 as a core noun for data provenance,
> orthogonal to `VenueId`, with a stated test for when a provider is a venue;
> add `corroborates` / `disagrees-with` to AD-16's edge types.

### N-12 (HIGH) — the new storage surface has no refusal category

AD-11's categories are fixed and enumerated: "invalid input / unsupported
capability / unavailable dependency / stale evidence / policy rejection /
transient venue failure," and "Categories are addable in later versions, **never
redefined**." AD-19 and AD-20 then add the largest I/O surface in the
framework.

A disk-full write, a corrupt Parquet footer, a `database is locked`, a failed
fsync, a truncated JSONL tail — none of these fits any category. `transient
venue failure` is venue-scoped by name; `unavailable dependency` means a
missing dependency, not a full disk. AD-11 also forbids the escape hatch:
"exceptions … never carry refusals across a package boundary," and DuckDB,
pyarrow and `sqlite3` all signal by exception.

Unit A files disk-full as `unavailable dependency`; Unit B as `transient venue
failure`; Unit C raises through the boundary. Three conformant-ish units, three
behaviors, and because categories can never be redefined, whichever one ships
first is permanent.

> **Fix (N-12):** mint a seventh AD-11 category, `storage failure`, now —
> before `qmf-data` is written.

### N-13 (HIGH) — six rooms, and no world

AD-12 is emphatic: "a non-live world may never write into the live evidence
namespace … **Identity distinctness alone does not deliver world separation —
storage separation does.**" AD-19 then defines the storage model — six
room-roles — and never mentions `world`.

Unit A instantiates a full set of six rooms per world (multiplying AD-20's
backup, retention, and migration surface by the number of worlds). Unit B keeps
one set of rooms with a `world` column, which is exactly the identity-only
separation AD-12 rejects by name. AD-19 licenses both.

> **Fix (N-13):** the six room-roles are instantiated **per world**; a read
> crossing worlds is a `policy rejection` refusal.

### N-14 (HIGH) — "always rebuildable" is a licence to destroy cited evidence

AD-19 calls the processed room "always rebuildable from raw," which in AD-20's
retention economy is the justification for keeping raw and lineage forever but
not processed.

But AD-5 says re-deriving "under a newer calendar/tzdata version produces a
**new artifact with its own fingerprint** … never a rewrite, never a silent
equality." So the rebuild is *not* the same artifact after any tzdata bump —
and AD-2 lets extensions bump tzdata off the lockstep ladder.

Unit A deletes processed artifacts to reclaim space, trusting rebuildability.
After the next tzdata bump, every AD-12 result label that cited those processed
fingerprints as **input fingerprints** points at artifacts that exist nowhere
and can no longer be produced. That is a direct breach of AD-5's "QMF never
loses the ability to read old stored evidence" — through a door the spine
labels safe.

> **Fix (N-14):** a processed artifact cited as an input by any result label is
> retained forever like raw; "rebuildable" licenses deletion only for uncited
> artifacts, and any rebuild pins the original calendar/tzdata version.

### N-15 (HIGH) — AD-15's purity rule has no carve-out for the package built to do I/O

AD-15: "library functions are pure and deterministic; stateful components
follow one-writer-per-stream." `qmf-data`'s entire job — intake, appends,
migrations, backups — is impure by definition.

Unit A reads store handles as "stateful components," exempt. Unit B reads
"library functions are pure" as binding on `qmf-data`'s public API and builds
an effect-returning design where qmf-data *describes* writes for the
application to perform. These are two different architectures for the same
package, and AD-15's text supports both.

> **Fix (N-15):** name the exempt class in AD-15 — components owning an
> external resource (stores, recorders, adapters) are "stateful components";
> purity binds pure-computation libraries only.

### N-16 (HIGH) — a promotion is written twice, in two schemas, with no canonical owner

AD-18 reserves "a promotion-occurrence card kind" in the registry. AD-21 lists
`promotion` among the journal's seven event types. Neither references the
other; neither is declared canonical.

Unit A writes only the card. Unit B writes only the journal event. Unit C
writes both, and they drift — different fields, different fingerprints, two
answers to "was this promoted." This is the prior review's A-2 defect ("the
risk journal is written twice, in two encodings") recurring at a new seam.

> **Fix (N-16):** the registry promotion card is canonical; the journal's
> `promotion` event carries only that card's fingerprint plus `correlation_id`.

### N-17 (HIGH) — AD-17's binding rule makes paper and live two different Bots

AD-17: "one Bot binds to exactly one Book." AD-9: "Books bind to accounts," and
each account has a role (live / demo / paper-validation / paper-benched /
prop-firm). AD-12's stated purpose for the account-role mechanism: "paper/demo
runs are `world = live` and **stay comparable to live for alpha-decay
sensing**."

Chain them. Running the same strategy on a paper account and a live account
requires two Books, which requires two Bots, which under AD-10 are two
artifacts with two fingerprints. **The comparability AD-12 built the world
model to preserve is destroyed by AD-17's binding rule** — the paper bot and
the live bot are not the same bot, so there is nothing to compare across.

> **Fix (N-17):** Bot identity is its content; the Bot↔Book↔account binding is
> a separate dated binding record **outside** Bot identity, so one Bot runs
> paper and live as one artifact.

---

## 4. Smaller contradictions (MEDIUM)

- **N-18 — the spine breaks its own naming rule.** The Conventions table bans
  bare "calendar": "'market-hours calendar' / 'day-boundary calendar' / 'news
  calendar' — **never bare 'calendar'**." AD-21 writes "The **calendar
  recorder** keeps provider-native identity and revisions." A unit could
  reasonably build a market-hours-calendar recorder. *Fix:* rename to
  "news-calendar recorder."
- **N-19 — "encrypted" has no owner.** AD-20 mandates encrypted backups; no
  crypto dependency, licence line (AD-6), or key-custody owner exists anywhere.
  *Fix:* drop it with N-05's demotion, or register the dependency and name the
  key owner.
- **N-20 — "JSONL-class" is undefined.** AD-16 uses the phrase without pinning
  framing, encoding, durability, rotation, or whether `fp1`'s canonical-JSON
  rules (sorted keys, NFC, no nulls) apply to lineage lines. Two units, two
  file formats, and merges that can't read each other. *Fix:* pin it — one
  `fp1`-canonical JSON object per line, LF-terminated, append-with-fsync, no
  rewrite, rotation by size with a monotonic file ordinal.
- **N-21 — idempotent intake has no key, and AD-10 may alarm on normal
  revisions.** AD-21 mandates "idempotent intake" without naming the
  idempotency key. Worse, AD-19 says external facts carry revisions and
  "corrections are appended" — while AD-10 treats "same hash, differing bytes"
  as "refused and alarmed." A provider revision under a reused id will trip the
  collision alarm. *Fix:* state the key as `(source, source-native id,
  revision)` and exempt provider revisions — a revision is a new artifact, not
  a collision.
- **N-22 — AD-4's contract tests need dependencies AD-2 forbids.** AD-4: contract
  tests are "owned by the contract's owning package, **run by producer and all
  consumer packages at tier 2**." Default-deny forbids the consumer from
  declaring the dependency, and AD-2's isolated per-package tier-2 environments
  make the undeclared import fail. Latent before this sitting; live now that
  AD-16 makes `qmf-registry` a consumer of `qmf-data`'s contracts. *Fix:* AD-2
  permits a **test-only** dependency on a contract's owning package, which is
  not a ratified runtime edge.

---

## 5. Attacks I declined as later-sitting territory

Per the review brief, these were found and deliberately not pursued:

- Indicator protocol shape, TA-Lib pinning, structure families (AD-13/Deferred
  → indicator sitting).
- Venue adapter contract, order state machine, cTrader BID/time verification
  (GAP-0035..0038 → venue sitting).
- Book/BMS internals, exit mechanics, position sizing, SQS, stop-out
  (GAP-0039..0046 → risk sittings).
- Full Bot/QML schema contents — AD-17 constrains cardinality only, and that
  constraint is what I attacked (N-07, N-17), not the schema.
- Simulated-time typing and the `world = simulated` unlock (backtesting
  sitting). Note that N-04 is *not* in this bucket: the seal governs data being
  written **now**, not backtesting.
- Numeric performance budgets (AD-13, awaiting baselines).
- Node/ops monitoring stack selection (AD-14 obligation already binds).

---

## 6. What I would change before this spine ships

Ranked by cost of getting it wrong, cheapest first:

1. **N-05** — one sentence. Demote AD-20's backup rule to primitives. Removes a
   flat self-contradiction between the Rule text and the Deferred table.
2. **N-12** — one word. Add `storage failure` to AD-11 now; categories can
   never be redefined, so this is free today and permanent tomorrow.
3. **N-02 / N-03** — amend AD-16's header. Derive `stable id` from the
   fingerprint, mark `created-at` occurrence-only, add `writer` + `sequence`,
   and move accruing lineage exclusively into edge records. Without this the
   registry cannot deduplicate, which is the reason the registry exists.
4. **N-06 / N-07** — two identity declarations. Exclude `correlation_id` from
   `fp1`; canonicalize multiplicity collection order. Both are one-line
   additions that prevent permanent, unfixable identity forks.
5. **N-01** — the structural one. Ratify `qmf-registry → qmf-data` as the first
   inter-library edge and add the registry room-role. This is a spine
   amendment by AD-2's own rule, so it must be an operator decision, not an
   implementer's.
6. **N-04** — the one that matters most. Bind the seal to a refusal at every
   qmf-data read boundary, now, independent of the GAP-0016/0017 deferral. The
   operator accepted losing causality *evidence*; he has not been told he is
   also currently losing the *seal*.
