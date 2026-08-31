# Round-2 fix-seat CARRY items (verbatim seat reports), 2026-08-30


## fix seat [4]

```
All six edits applied to CT-45; YAML parses (17 invariants, 7 enums), no banned session-mechanics words, no residual "operator ruling" or invented "broker-resolved reference" auth_mode token. All three findings verified correct against spine AD-15, registry `typed_refusal_codes` (DEC-0109), qma-core.md, veto-register.md (V3/V4), changelog ★V3/★V4, and transcript-scan §4.

CHANGED: _docwork/qma/staged/docs/contracts/ct-45-qma-model-deployment-broker.yaml
- Finding 1 (major, VERIFIED): schema.enums last item — "refusal categories on this contract's paths, per registry:typed_refusal_codes: NoEligibleDeployment …" → "typed refusals on this contract's paths, variants of `qmf-core`'s base (CT-04): `NoEligibleDeployment` … `NoEligibleReviewer` … `NonLoopbackProxy` … `UnauthenticatedProxy` … `CredentialOutOfScope` …". All five are QMA variant type names (confirmed in qma-core.md §"QMA refusal variants of qmf-core's base (AD-3)"); none is a member of the seven-category `typed_refusal_codes` row, so no separate parent-category clause was needed for CT-45.
- Finding 2 (major, VERIFIED): invariant label "LOCAL-PROXY LOOPBACK BIND (operator ruling)" → "LOCAL-PROXY LOOPBACK BIND (AD-15, surfaced assumption — operator-overridable, GAP-free cheap veto V3)"; "MULTI-ACCOUNT POOLING (operator ruling)" → "MULTI-ACCOUNT POOLING (AD-15, surfaced assumption — cheap veto V4)"; provenance_note "…are operator rulings surfaced in the cheap-veto register" → "…were resolved from sources under the operator's meta-ruling delegation and are surfaced in the cheap-veto register as overridable". (veto-register Class 1 L106/L41; changelog ★V3=loopback, ★V4=pooling; transcript-scan §4 "rest on delegation + sources, not affirmative SRC-14 words".)
- Finding 3 (minor, VERIFIED): schema.enums auth_mode + schema.fields deployment.auth_mode — dropped the invented second token "broker-resolved reference"; both now read "auth_mode: `none` — the value a local-proxy Deployment carries on the QMA side …; the spine mints no other auth_mode value, and a QMA-owned credential is carried as a broker-resolved `credential_ref` on the Deployment rather than as a second auth_mode token". (AD-15 mints only `auth_mode: none`.)

REFUSED: none

CARRY: finding 1's fix also names six other lane files (out of this seat's scope — edit ct-45 only). Each restate its typed-refusal enum/field line on the CT-41/CT-42 "variants of `qmf-core`'s base (CT-04)" pattern, moving any genuine parent CATEGORY into a separate clause that cites `registry:typed_refusal_codes`; do NOT add QMA names to the `typed_refusal_codes` row.
- _docwork/qma/staged/docs/contracts/ct-40-qma-wire-envelope.yaml (schema.enums, ~L62): "typed refusals on this surface, per registry:typed_refusal_codes and variants of `qmf-core`'s base: `CursorScopeMismatch` … `UnknownHostRequest` … `OperatorPrincipalRequired` …" → "typed refusals on this surface, variants of `qmf-core`'s base (CT-04): `CursorScopeMismatch` … `UnknownHostRequest` … `OperatorPrincipalRequired` …" (all three are variants; no parent category — drop the `registry:typed_refusal_codes` claim). Keep DEC list unchanged.
- _docwork/qma/staged/docs/contracts/ct-43-qma-memory-provider.yaml (schema.enums, ~L65): "refusal categories on this port's paths, per registry:typed_refusal_codes: NoMemoryProvider (…); invalid input (…)" → "typed refusals on this port's paths, variants of `qmf-core`'s base (CT-04): `NoMemoryProvider` (a variant returned by `recall` while no provider is bound, AD-1/AD-3); plus the parent category `invalid-input` per registry:typed_refusal_codes (a `propose` carrying `admission_confidence`, or a candidate missing its mandatory scope or proposer)". Keep DEC-0317, DEC-0300, DEC-0302.
- _docwork/qma/staged/docs/contracts/ct-44-qma-knowledge-source.yaml (schema.enums, ~L62): "refusal categories on this port's paths, per registry:typed_refusal_codes: ProvenanceShapeMismatch (…); StaleSnapshot (…); unsupported capability (…)" → "typed refusals on this port's paths, variants of `qmf-core`'s base (CT-04): `ProvenanceShapeMismatch` (…); `StaleSnapshot` (…); plus the parent category `unsupported-capability` per registry:typed_refusal_codes (a ranked or semantic retrieval request while v1 ships no index)". Keep DEC-0318, DEC-0343, DEC-0302.
- _docwork/qma/staged/docs/contracts/ct-46-qma-execution-environment-job.yaml (schema.enums, ~L64): "typed refusals on this contract's paths, per registry:typed_refusal_codes: NoEnvironment (…); OperatorPrincipalRequired (…)" → "typed refusals on this contract's paths, variants of `qmf-core`'s base (CT-04): `NoEnvironment` (…); `OperatorPrincipalRequired` (…)" (both variants; no parent category). Keep DEC-0316, DEC-0323.
- _docwork/qma/staged/docs/contracts/ct-47-qma-experiment-spec.yaml (schema.enums, ~L59): entries are prose conditions, not variant names — "typed refusals on this contract's paths, per registry:typed_refusal_codes: a second qmb job placed into one environment is refused …; an approval_request … is refused" → "typed refusals on this contract's paths, variants of `qmf-core`'s base (CT-04): a second qmb job placed into one environment (single qmb door); an approval_request for a money_path_relevant candidate without the required field-level diff". Remove the `registry:typed_refusal_codes` membership claim (no parent category applies); keep DEC-0316, DEC-0313.
- _docwork/qma/staged/docs/contracts/ct-48-qma-mailbox-envelope.yaml (schema.enums, ~L62): "typed refusals on this contract's paths, per registry:typed_refusal_codes: OperatorPrincipalRequired (…); a second lead flag on a desk is a hard startup error until GAP-0071 is ruled" → "typed refusals on this contract's paths, variants of `qmf-core`'s base (CT-04): `OperatorPrincipalRequired` (a machine principal reading or answering an approval_request); a second lead flag on a desk is a hard startup error until GAP-0071 is ruled". Keep DEC-0323, DEC-0349.
```


## fix seat [5]

```
Verification complete. The dry-run confirms `append: skipped (present)` — the fragment is intact in its landed state, no FAIL.

Determination: the finding is VERIFIED correct, but its in-scope remedy (Option B, rewrite the note) is disproven by evidence, so I leave the note text unchanged and CARRY the correct remedy (Option A, a git commit) to the orchestrator.

Evidence:
- `archive/agentic-spine.txt`: `?? archive/agentic-spine.txt` (untracked) in main repo working tree (55,680 bytes present on disk); entirely ABSENT from the landed worktree `C:/Users/Mubarak/Desktop/QMX-qma/archive/` (only qmf-1/3/4/5/6/7.txt, qml.txt, qmx-2.txt, recovery/ are there). Every sibling transcript is tracked in both trees (`git ls-files archive/`).
- NOT gitignored: `git check-ignore` returns "not ignored". The `.gitignore` line 14 comment "recorded raw evidence ... never committed" governs `recorder/data/` (line 15), NOT `archive/`.
- Precondition of Option B is FALSE: SRC-15 (job-spec rider, highest authority) names the transcript as intake material with no version-control exclusion; the brief mandates SRC-14 "mirrors the SRC-08/SRC-10/SRC-12 treatment" (all git-tracked); siblings are all committed. So the transcript is meant to be tracked, not "held outside the repository".
- `_docwork/qma/harvest/transcript-scan.md` exists (19,891 bytes) and is the verified-quote surface for SRC-14 (EXT-2440..EXT-2459).

---

REFUSED: `_docwork/qma/fragments/manifest.yaml` SRC-14 note edit (finding's Option B) — leave text unchanged. The note ("citation surface for the operator's own typed or dictated words only ... mirrors the SRC-08/SRC-10/SRC-12 treatment") is correct. Option B is gated on "if the operator keeps that transcript out of version control," and that precondition is disproven: the file is not gitignored (the "never committed" rule targets `recorder/data/`), every sibling transcript is committed, and SRC-15 + the brief mandate tracked treatment. Amending the note to declare the transcript "held outside the repository" as a dated fact would assert unverified operator intent and contradict the brief-mandated SRC-08/10/12 treatment.

CARRY: file `archive/agentic-spine.txt` (increment branch `docs/qma-increment`, worktree `C:/Users/Mubarak/Desktop/QMX-qma`) — orchestrator landing-step git action, not a lane-file edit and outside this seat's one-file scope. Exact change: `git add archive/agentic-spine.txt` (source at `C:/Users/Mubarak/Desktop/QMX/archive/agentic-spine.txt`, 55,680 bytes) and commit it onto the increment branch so SRC-14 resolves like SRC-08/SRC-10/SRC-12; then the 20 extractions EXT-2440..EXT-2459 cite a source every reader of the branch can open, and no fragment change is needed.
```


## fix seat [7]

```
All five findings verified against the spine (AD-15, AD-17, AD-20, AD-23, AD-24, AD-26) and applied where they belong to the one lane file. YAML parses (33 rows), no residual bad tokens, and the `registry-variables` fragment dry-run passes (0 failures; "skipped (present)" as expected).

CHANGED _docwork/qma/harvest/variables-qma.yaml [F2] deployment.model_family notes rewritten to a single home — registered variable = the registry-homed closed enum of allowed family values (operator variable.set, AD-24); the per-Deployment assignment recast as an operator-assigned FIELD of the Deployment record under AD-15/AD-24, "not a second home of this variable"; plugin model_deployment registers with none. Confirmed by AD-26 ("write path is single per variable... declares a home of either registry or a named owning record type") and AD-26 registering "model_family values" (the enum).
CHANGED _docwork/qma/harvest/variables-qma.yaml [F3] added row mailbox.delivery_retention_window (units/type duration, component COMP-QMA-DAEMON, decision DEC-0319, configurable true, registry-homed, scope global, value declared-per-installation, notes: window value deferred GAP-0089). Confirmed by AD-23 ("only inside their registered AD-26 retention windows" for BOTH bounded streams) and AD-26 ("retention windows" registered, distinct from the Deferred-table trim thresholds).
CHANGED _docwork/qma/harvest/variables-qma.yaml [F4-scope] replaced all 22 "Scope declared-per-subsystem" with "Scope global (AD-26 pins none explicitly)" (not an AD-26 closed scope value; global for these daemon-wide registry-homed values); also fixed deployment.model_family lowercase scope. record-homed rows (quant/mission/routine/execution_environment) left with their valid closed scopes.
CHANGED _docwork/qma/harvest/variables-qma.yaml [F4-value] renamed all 19 "value: declared-per-deployment" to "value: declared-per-installation" (the token meant "per system installation", collided with the AD-15 Deployment record); after F2 no registered variable means the AD-15 Deployment record, so the declared-per-deployment retention clause applies to zero rows. Header comment updated to match the terminology.
CHANGED _docwork/qma/harvest/variables-qma.yaml [F5] kept both environment.max_in_flight rows (per F1's premise) and clarified both notes: environment.max_in_flight_pinned_kinds is "a house-recorded constant expressing AD-26's per-kind editability rule... not a second spine-registered variable name — AD-26 names one variable, max_in_flight". Confirmed by AD-26 registering one variable "max_in_flight... pinned to 1 and uneditable for the remote_host and desktop kinds".

CARRY _docwork/qma/staged/docs/components/qma-daemon.md [F1] Configuration row: change to "`registry:environment.max_in_flight` (default 1, ui-editable); the `remote_host` and `desktop` kinds are pinned to 1 and uneditable as `registry:environment.max_in_flight_pinned_kinds`" (stop calling max_in_flight itself uneditable for those kinds; reference the constant row).
CARRY _docwork/qma/staged/docs/contracts/ct-46-qma-execution-environment-job.yaml [F1] fields + units: same edit as above.
CARRY _docwork/qma/staged/docs/scenarios/SCN-0014-money-path-barrier.md [F1] Worked numbers: same edit as above.
CARRY _docwork/qma/staged/docs/contracts/ct-45-qma-model-deployment-broker.yaml [F2] lines 35, 59, 70: drop "record-homed on the Deployment record" in favour of "an operator-assigned field of the Deployment record" (align ct-45 with the single-home rewrite).
CARRY _docwork/qma/staged/docs/components/qma-daemon.md [F3] line 241: change to "only inside their registered retention windows (`registry:mailbox.delivery_retention_window`, `registry:telemetry.retention_window`), whose event-count and on-disk-size trim thresholds (`registry:mailbox.delivery_trim_*`, `registry:telemetry.trim_*`) are the GAP-0089 revisit trigger" (stop conflating revisit thresholds with the window; reference the new mailbox window row).

NOTE [F4-evidence] The finding named store.backup_cadence as carrying "Scope declared-per-subsystem"; it actually carried NO scope line. Applied the finding's intent by inserting "Scope global (AD-26 pins none explicitly)." there so it matches its sibling cadence rows and satisfies AD-26's mandatory-scope rule; no other unnamed row was touched.
NOTE [F3-asymmetry, not applied — outside findings] telemetry.retention_window was not flagged and still reads "No spine default (DEC-0322, DEC-0325)" without a GAP-0089 reference, while the new mailbox.delivery_retention_window notes GAP-0089. GAP-0089 defers BOTH bounded-stream windows; a future parity pass could add the GAP-0089 note to telemetry.retention_window.
```


## fix seat [10]

```
CHANGED: _docwork/qma/fragments/gap-report.yaml — GAP-0070 body row citation pair `(`DEC-0336`, `DEC-0341`)` -> `(`DEC-0324`, `DEC-0316`)` (AD-25 deployment envelope + AD-17 `NoEnvironment`). Frontmatter `decisions` list reconciled to match: added DEC-0324, removed now-orphaned DEC-0336 and DEC-0341 (DEC-0316 already present). Finding VERIFIED against sources before applying: gaps.yaml GAP-0070 note names only AD-25 + AD-17; qma-daemon.md L189/L253/FM-5, ct-46 (x2) and SCN-0014 Branch A all govern GAP-0070 with DEC-0316/DEC-0324; DEC-0341 ("no execution tool at any account role") is unrelated to provisioning a desktop environment. Dry-run `apply_fragments.py --root C:/Users/Mubarak/Desktop/QMX-qma --dry-run --only gap-report` = 0 failures, EXIT=0 ("skipped (present)" expected, no FAIL). DEC-0336/DEC-0341 now occur 0 times in the file.

CARRY: _docwork/qma/fragments/changelog.yaml — apply the same finding to the cheap-veto register row V8 ("AD-25; DEC-0336, DEC-0341; GAP-0070"): replace citation pair `DEC-0336, DEC-0341` with `DEC-0324, DEC-0316`, yielding "AD-25; DEC-0324, DEC-0316; GAP-0070". Keep DEC-0336 in that fragment only where the deployment envelope itself is the point. If changelog.yaml's `frontmatter_add decisions` list carries DEC-0336/DEC-0341 solely for this V8 row, reconcile it the same way (add DEC-0324; drop DEC-0336/DEC-0341 only if cited nowhere else in that fragment). Not applied here — different lane file, out of this seat's scope.

REFUSED: none.
```


## fix seat [12]

```
All seven edits applied; file parses cleanly (22 entries, DEC-0329..DEC-0350 intact). This is a harvest YAML, so parse-validation is the required check (no apply_fragments dry-run needed).

```
CHANGED: _docwork/qma/harvest/ledger-L4.yaml
  - DEC-0345 rationale (finding 1, major): "Operator ruling 2026-08-28 (memlog L104, one of the three findings withheld for him at L102 and resolved per the meta-ruling)" -> "Resolved from sources under the operator's meta-ruling delegation 2026-08-28 (memlog L104, one of the three findings withheld at L102; a vocabulary call the operator owns and can overturn in one line, cheap-veto V7)"; "Operator ruling" dropped. Verified: memlog L102 (withheld, none applied), L104 (no operator attribution), changelog V7=DEC-0345.
  - DEC-0342 rationale (finding 2, major): "(operator 2026-08-28, memlog L42)" -> "(ChatGPT-transcript row 43 adopted by the sitting, memlog L42 — no operator ruling behind it)". Verified: memlog L42 "(ADOPTED from transcript row 43, NOT amended)" no operator tag; transcript-scan §4 places it under agent/ChatGPT inference.
  - DEC-0344 rationale (finding 3, major): "the operator rulings applied at validation (memlog L105 local-proxy custody, L194 pooling and loopback and optional model_family)" -> "the validation-pass resolutions of the two assumption tags (memlog L105 local-proxy custody, L194 pooling, loopback default and optional model_family) — resolved from sources under the meta-ruling and surfaced as cheap vetoes V3/V4/V5". Verified: L105 no operator attribution, L106/L41 assumption tags, changelog V3/V4/V5=DEC-0344.
  - DEC-0338 statement (finding 4, minor): "('makes no architectural sense')" -> "('In an architectural sense, that does not make any sense')" (accurate-quote option). Verified: transcript-scan D1; EXT-2447 quote field holds the verbatim.
  - DEC-0336 statement (finding 5, minor): "('90% of the time, like most harnesses')" -> "('most or 90% of the time these agents are going to be working on my machine here, like most harnesses')" (accurate-quote option). Verified: transcript-scan D2; EXT-2456 quote.
  - DEC-0339 rationale (finding 6, minor): "(memlog L30 'everything gets hooks')" -> "(memlog L30; his own words, EXT-2453: 'everything we create here, we have to have hooks for it')" and "'too agentic'" -> "'too well agentic'". Verified: transcript-scan quote 15 + D5; EXT-2453 quote.
  - DEC-0340 rationale (finding 7, minor): "Adopted from the transcript (operator 2026-08-28 'already answered in the transcript, look it up', memlog L39) with AD-12/AD-13..." opening + name-split clause -> "Adopted by the sitting from the ChatGPT design transcript after the operator declined to re-answer D8 and directed it to the transcript (memlog L39), with AD-12/AD-13, the packet-delta cut of the 11-loop re-centring, and T-4954 ('we have to have a few graphs noted down, not loops'); the Graph Template vs Task Graph name split is the drafter's adversary fix, not an operator ruling (cheap-veto V9)." Verified: transcript-scan D6, veto-register Class 3 L39, changelog V9=DEC-0340.

REFUSED: none (all seven findings verified correct against memlog/transcript-scan/veto-register/changelog).

CARRY: _docwork/qma/harvest/extractions-L4.yaml (another lane file — not edited here)
  - line 59 (EXT-2369 summary), finding 5: replace "('90% of the time, like most harnesses')" with "('most or 90% of the time these agents are going to be working on my machine here, like most harnesses')".
  - line 109 (EXT-2377 summary), finding 3: replace "operator rulings applied L194" with "validation-pass resolutions of the two assumption tags L194 (cheap vetoes V3/V4/V5)".
```
```


## fix seat [13]

```
CHANGED: _docwork/qma/fragments/changelog.yaml | finding=major/ratified-by-operator-overstatement | verdict=CONFIRMED | line 15 (lands docs/changelog.md L19) intro paragraph: "ratified by the operator under his I-draft-operator-ratifies mode" -> "ratified by delegation under his I-draft-operator-ratifies mode" | evidence: transcript-scan.md §4 ("there is no turn in which the operator read back or approved the spine's AD text. Ratification is by delegation"); DEC-0329 statement (harvest/ledger-L4.yaml) says only "drafted under the sitting's 'I draft, operator ratifies' mode"; staged ADR-0020 L16/L75 say "ratified by delegation". Only occurrence of "ratified by the operator" in the file; line 21 ("FINAL under the sitting's I-draft-operator-ratifies mode") is not an overstatement and was left untouched (no scope widening). YAML parses OK; apply_fragments dry-run --root QMX-qma --only changelog = 0 failures, "skipped (present)" (expected — --root reads the worktree's already-landed fragment/tree).

CARRY: _docwork/qma/fragments/stage-state.md | line 12 change_mode `change:` value: "ratified by the operator under the sitting's I-draft-operator-ratifies mode" -> "ratified by delegation under the sitting's I-draft-operator-ratifies mode" | same finding, second lane file outside this seat's single-file scope; verified present verbatim at that line and warranted by the same evidence (DEC-0329 / ADR-0020 / transcript-scan §4).
```
