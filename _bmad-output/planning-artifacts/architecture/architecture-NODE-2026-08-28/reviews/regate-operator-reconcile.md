# Re-gate review — LENS: OPERATOR-RULINGS + BRIEF RECONCILE

Fresh independent lens over the amended trading-node ARCHITECTURE-SPINE.md (951 lines,
TN-1..TN-25) after the six-lens first gate (150 findings applied, fix-pass-1) and the
operator round of 2026-08-28 (four rulings applied). Read in full: the spine and the
42-entry `.memlog.md` (through entries 48 "OPERATOR RULINGS 2026-08-28" and 49
"AMENDMENTS FROM THE OPERATOR ROUND"). Scope: certify the CURRENT text against the
operator rulings and the brief's coverage lists; report only remaining divergences.

## Verdict

**CERTIFY WITH CHANGES.** The operator-ruling reconciliation is CLEAN across every
required dimension (a)-(i): the operator command line is fully purged (only `just node-…`
recipes and `qmn` as a code/import name survive), the soak is the full unattended
first-deploy warm-up week with live binding at its end, Forex Factory's free file is the
SOLE V1 news source with no paid fallback anywhere, the observability stack is a separate
zero-authority system under `qmn/deploy/observability/`, the shadow-lane seam is V1 node
work with MIS training + shadow rollout named as a follow-on epic, the extensibility /
promotion-as-click / UI-in-mind stances are present, and the A1-A39 register is complete
with owning TNs (A1 narrowed; A10/A17/A26 RULED; A39 present; A8 retired).

Two substantive findings remain, both desk-closable with no operator input: one HIGH
(a self-contradiction between the VPS egress allow-list and the now-mandatory
observability stack's image pulls / an unstated container runtime), one MEDIUM (the
Capability→Architecture Map omits three produced TNs). The rest are low.

## Dimension-by-dimension result

**(a) NO operator command line — PASS.** Grep for `CLI`, `command line`, `qmn <verb>`,
`typed door`, `Door 2` finds only: the explicit deletion/withdrawal statements (TN-1:129-130,
TN-17:481-501, R1:896, A1:912, A23:934), the negative Stack row (click "NOT TAKEN", :718),
and structural-seed/convention prose ("no command line"). No `qmn <verb>` command form
survives anywhere (grep for `qmn secrets|deploy|data|replay|registry|config|install|switch|
rollback|notify` = zero matches). The three doors are the Python API, the localhost HTTP
evidence channel, and the unix-socket powers channel (SO_PEERCRED). Deployment/provisioning
is exclusively `just node-…` recipes (22 occurrences), each stated "never a trading control,
never a product command line" (TN-1:130, TN-17:496, Ops convention:706). `qmn.venue.*` and
`qmn.service` / `qmn/…` occurrences are import/module/unit names, not invocations. CLEAN.

**(b) Soak = the full unattended warm-up week — PASS (one cosmetic residual).** TN-9:319-324,
Consistency:702, R2:898, A10:921 all state one full unattended week on the demo account,
live binding at its end, checklist unchanged. Grep `two days|2-day|first two days` finds only
lines 322 and 898, both the faithful operator QUOTE "two days to a week… I think a week is
enough and sufficient" — establishing why a week, not asserting a two-day soak. No residual
"2-day soak" claim anywhere. (Recorded as L1 below because the grep mandate names the phrase.)

**(c) Forex Factory free is the SOLE V1 source, no paid fallback — PASS.** TN-13:418-419,
registry row :681 ("no fallback slot row is minted"), R4:902, A17:928. Grep `paid|FMP|Trading
Economics|fallback slot` finds only NEGATIONS ("no paid fallback ever", "no fallback slot row
is minted", "I will not pay for news"). Refresh cadence minted: `news_calendar_refresh_cadence`
configurable, evidence every 2 h + before each session open, within the free feed's ~2
downloads/5 min limit (TN-13:419,:426, TN-18:512, registry :682). The later fallback path is a
second FREE source or agent-scraped JSON in the CT-15 intake shape. CLEAN.

**(d) Observability stack = separate zero-authority system — PASS (with the ops-prereq gap
of H1).** TN-15:458 (Prometheus/Grafana/Loki-class, zero-authority, never on a decision/
command/evidence path, compose file under `qmn/deploy/observability/`, containers permitted
for THIS STACK ONLY, Skylos IaC scan gates it, image versions pinned at the implementation
gate); Stack row :720; structural seed :777-778; Ops convention :706; :732. The node stays a
plain systemd service and is proven to run unchanged when the stack is stopped (TN-23:585).

**(e) Shadow-lane seam is V1 node work; training is a follow-on epic — PASS.** TN-19:532-534
(three built-now pieces: candidate labeler registration, shadow snapshot stream to its own
manifest prefix, comparison read model; a candidate is never a live consumer; a composition
wiring a shadow output into a governed consumer refuses to boot). MIS training + shadow
rollout is the named follow-on epic (Deferred:876-877; R-also-ruled:904). CLEAN.

**(f) Extensibility sentence present — PASS.** TN-18:513 and TN-22:572 both state: adding a
Book, BMS, bot, or a new version of any is a registry mint + roster-config change + restart
at a safe point — never code; "a change that would require node code … is a design defect in
this spine, not a story." Also R-also-ruled:904. CLEAN.

**(g) Promotion = click + separate activation, machinery silent — PASS.** TN-20:543-545
(precondition battery runs silently, server-side, against fresh state; "the operator sees
results, never machinery"; activation is a second act; approval never equals exposure);
R3:900; A26:937. CLEAN.

**(h) UI-in-mind stance where operator moments exist — PASS.** TN-17:486,:498 ("EVERY OPERATOR
MOMENT IS A FUTURE UI STORY"), Deferred:890 ("DEFERRED but never optional"), R-also-ruled:904.
CLEAN.

**(i) Assumption register — PASS.** A1 narrowed (:912), A10 RULED (:921), A17 RULED (:928),
A26 RULED (:937), A39 present (:950), A8 RETIRED (:919). Table A1-A39 complete with an owning
TN on every row (:910-950). CLEAN.

**(j) Brief coverage → Capability map + owning TN — PARTIAL (M1).** Each TN has a full spec
section, but the Capability→Architecture Map (:844-864) omits three produced capabilities from
its "Governed by" column: TN-5 (the unforked live loop + push-to-pull accumulator — the central
runtime), TN-20 (promotion and activation — operator ruling Q3), and TN-1 (identity, packaging,
base branch). See M1.

## Findings

### HIGH

**H1 — The VPS egress allow-list contradicts the now-mandatory observability stack, and the
stack's container runtime is never provisioned or pinned.**
Where: TN-16:474 (egress allow-list) vs TN-15:458 + TN-23:585 (mandatory stack) + TN-16:471
(install recipe).
TN-16:474 declares a default-deny outbound posture with an allow-list of "the venue hosts, the
notification and dead-man's-switch endpoints, the object-storage bucket, the history and
news-calendar providers, the distribution index and NTP." That list contains NO container image
registry. The observability stack (TN-15:458) ships as a compose file of pinned Prometheus /
Grafana / Loki images, and standing it up "from the checked-in compose file … for the whole
unattended week" is a SOAK-ACCEPTANCE item (TN-23:585). Under the stated egress posture the
image pulls are blocked, so the mandatory stack cannot stand up and the soak item cannot pass.
Separately, `just node-install` (TN-16:471) is said to install "the observability compose file"
but no rule states that provisioning installs or pins a container runtime (docker/podman +
compose) for the separate stack — while NFR-10's "no container requirement" is asserted for the
node. Two builders reading this diverge on whether the VPS needs a container engine and registry
egress at all.
Fix: In TN-16:474 add the container image registry (or a vendored/mirror image source) to the
egress allow-list. Add one sentence to TN-16 (and the Stack row :720) stating that provisioning
installs and version-pins a container runtime for the SEPARATE observability stack only, the
trading node keeping its no-container-requirement — e.g., "the observability stack requires a
container runtime and image-registry egress, both provisioned for that stack alone; the node
runs and passes without them."

### MEDIUM

**M1 — The Capability→Architecture Map omits TN-5, TN-20 and TN-1.**
Where: Capability → Architecture Map, :844-864.
The map is the coverage index the documentation-factory and epics-and-stories steps will read.
Its "Governed by" column cites TN-2..TN-4,6..19,21..25 but never TN-5 (the live event-slice loop
+ push-to-pull accumulator — arguably the single most central runtime capability the node
produces), never TN-20 (promotion and activation — a produced operator capability and the subject
of operator ruling Q3), and never TN-1 (node identity, packaging, base branch). Lens (j) requires
every produced capability to carry a map row with an owning TN.
Fix: add rows — "The live event-slice loop, push-to-pull accumulator, per-stream driver | `loop/`
| TN-5"; "Promotion and activation | `promotion/`, `doors/` | TN-20"; and cite TN-1 in the
"Overall system architecture" row's Governed-by column (currently TN-3, TN-4, TN-16).

### LOW (rolled into counts)

**L2 — "Where the two disagree the memlog governs" points at a memlog whose register entry is
stale.** Spine :908 names `.memlog.md` as the assumption register's authority, but the memlog's
register entry (event 40) still lists A1 as "own `qmn` command" and frames A1/A10/A17/A26 as OPEN
AskUserQuestion items; only the later append-only entries 48-49 supersede them. A reader who
stops at the register entry inherits the pre-ruling calls. Fix: either point the authority line
at "the memlog's ruling entries (48-49) as amended" or note that the spine's A1-A39 table is the
current reconciled view.

**L1 — Residual "two days" survives only as operator quotes.** Lines 322 and 898 carry "two days
to a week…" verbatim; both immediately resolve to a week and neither asserts a two-day soak.
Faithful provenance, not a divergence — recorded because the grep mandate names the phrase.

**L3 — Minor naming drift: "MIS-Live seam" vs "MIS seam."** The scope frontmatter (:7) writes "the
MIS-Live seam" while TN-19 and the body write "MIS seam" / "MIS V1 is a SEAM ONLY." Harmless;
align to one term if desired.

**L4 — "Unattended" week vs operator-performed acceptance drills.** The TN-23:585 checklist
includes items that require a present operator (operator-signed synthetic kill-line breach,
`value-status` countersign, operator `resume`, operator `resurrect`, the SO_PEERCRED refusal
test) while TN-9:322 frames the week as run "unattended … left alone." Reconciled by "unattended
is a design constraint, not a schedule note," but a one-line note that the injected-fault drills
are discrete acceptance acts distinct from the continuous unattended run would remove the
apparent tension.

## Counts

Critical 0 · High 1 · Medium 1 · Low 4 · Total 6.
