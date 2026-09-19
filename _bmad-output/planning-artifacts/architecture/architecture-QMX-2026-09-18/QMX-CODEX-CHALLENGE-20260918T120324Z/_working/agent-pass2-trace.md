# Pass II bounded candidate trace

## Method and verdict

I traced the frozen Pass-I baseline BR families and all P1 IDs against the candidate spine (AD-1..22), contracts, journeys, requirements addendum, conflict register, stack/evaluation, UI host, implementation sequence, and operator questions. `Supported` means an explicit AD/contract/journey oracle exists; `Partial` means the semantic rule exists but the transition/oracle is only deferred, representative, or unimplemented; `Absent` means no candidate support; `Ambiguous` means competing meanings remain; `Contradictory` means candidate explicitly refuses a baseline requirement.

## BR-family trace

| Baseline family | Candidate support | First unsupported transition / evidence | Counterexample and impact | Repair option |
|---|---|---|---|---|
| BR-CAP | Partial | install→duplicate/incompatible index preservation (AD-18 in `ARCHITECTURE-SPINE.md:190`; no journey) | P1-CAP-002 can corrupt/replace an index unless atomic rebuild is specified; activation safety is unobservable | Add pack-install state machine, atomic index transaction and P1-CAP-001..006 journeys |
| BR-OP | Partial | job artifact→worker loss→partial/unknown (`CONTRACTS.md:98-112` has states but no partial-artifact contract/journey) | P1-OP-003 cannot distinguish labelled partial from failed/unknown; consumers may treat incomplete output as complete | Add artifact inventory/completeness and reconcile transitions to JobHandle contract |
| BR-WF | Partial | fan-out/join empty/missing/late/failed partition (`AD-5/6`, `CONTRACTS.md:144` only topology) | P1-WF-004/005/006/007 lack cardinality, invalidation, review-resume, trigger dedupe or concurrency oracle | Add edge mapping/join and trigger/review state contracts plus journeys |
| BR-SES | Supported (with one gap) | reconnect without replaying intent is only named in AD-8, not journeyed | P1-SES-005 can duplicate a command after reconnect; authority isolation itself is explicit (`J01`, `CONTRACTS.md:49-79`) | Add reconnect/idempotency journey and persisted last-intent marker |
| BR-DATA | Partial | exact provider disagreement/entitlement/unavailable states→recipe output (`AD-12`, `CONTRACTS.md:81-96`) | P1-DATA-002/005/007/008 can silently substitute a source or label partial weights complete | Add source-resolution and training artifact completeness/error contracts |
| BR-STR | Partial | bounded buffer overload→gap/drop handling (`CONTRACTS.md:114-128` covers phase/cancel, not backpressure/gap semantics) | P1-STR-002/003/005 have no observable policy; market-driving events may be silently dropped | Add buffer limits, gap event, dedupe/order and ref-count lifecycle schema |
| BR-MKT | Contradictory for one accepted baseline path; otherwise partial | non-Book live/node-paper deploy is explicitly refused (`AD-11`, `IMPLEMENTATION-SEQUENCE.md:34,40`) | P1-MKT-002/003/004/009 require a complete non-Book live path; candidate says wait for L36 amendment, so no support in this increment | Either mark those scenarios out-of-scope in frozen baseline or add L36 constitution amendment and non-Book command contract |
| BR-PLC | Partial | preflight→dispatch→UI/coordinator/worker failure→restore (`AD-15`, `IMPLEMENTATION-SEQUENCE.md:34`) | P1-PLC-001..006 are deferred; remote/local artifact portability and restore are not journeyed | Add placement preflight, artifact staging, failure matrix and disposable restore journey |
| BR-SKL | Partial | skill author→evaluate→install/activate and mutation execution (`AD-19`, `STACK-AND-EVALUATION.md:48+`) | P1-SKL-001/002/004 are later QA; Windows WSL requirement is documented but no executable oracle | Add skill lifecycle/evaluation contract and WSL disposable-run evidence schema |
| BR-APP (baseline app/cross-app) | Partial | package contribution→UI mount→host mediation (`AD-10/17`, `UI-HOST.md`) | P1-APP-001..008 lack a complete host lifecycle; MCP/json-render are explicitly adapters, chrome deferred | Add host contribution/reconnect/mount-dispose and composite authority journeys |

### P1 family coverage (all IDs)

- **CAP:** P1-CAP-001..006 — partial; AD-2/3/18 and implementation Slice 1 cover discovery/export, but duplicate IDs, migration failure, open-session grant stability, uninstall dependants, and secret stripping lack complete transition oracles.
- **OP:** P1-OP-001..005 — P1-OP-001/002 supported by AD-3/21 and JobHandle unknown state; P1-OP-003..005 partial (partial artifacts, cancel races, expiry/recovery not fully contracted).
- **WF:** P1-WF-001..007 — P1-WF-001/002/003 supported by AD-4..6; P1-WF-004..007 partial/absent (join policy, rerun dependency invalidation, human-review evidence/resume, trigger dedupe/concurrency).
- **SES:** P1-SES-001..006 — P1-SES-001..004 and 006 supported by AD-8/9 and J01; P1-SES-005 partial (reconnect intent replay has no journey).
- **DATA:** P1-DATA-001..008 — P1-DATA-001/003/004/006 supported in AD-12/13 and J06/J13; P1-DATA-002/005/007/008 partial (provider disagreement, placement, weight completeness, unavailable/entitlement states).
- **STR:** P1-STR-001..005 — P1-STR-001 and 004 supported by stream contract/J17; P1-STR-002/003/005 partial (ordering/gaps, backpressure, reconnect/unsubscribe details).
- **MKT:** P1-MKT-001..010 — P1-MKT-001, 005, 006, 007, 008, 010 supported/partially supported by AD-11/14 and deployment contract; P1-MKT-002/003/004/009 are contradictory or absent because AD-11 explicitly refuses live/non-Book until L36 amendment; command binding/arbitration still needs executable traces.
- **PLC:** P1-PLC-001..006 — partial/deferred under AD-15 and implementation “Later”; no full preflight/failure/restore evidence.
- **SKL:** P1-SKL-001..004 — partial/deferred under AD-19 and stack plan; no lifecycle or mutation-run oracle.
- **APP:** P1-APP-001..008 — partial; AD-10/17 define modes and host boundaries, but no complete host journey for contribution discovery, mount/dispose, reconnect, or composite refusal.

## First unsupported transitions (ordered)

1. **P1-CAP-002:** pack validation/index rebuild → atomic preservation of previous usable index. Candidate names install/enable/rollback but no state/transaction contract (`ARCHITECTURE-SPINE.md:190`, `IMPLEMENTATION-SEQUENCE.md:11-19`).
2. **P1-OP-003:** artifact emitted → worker dies → partial inventory plus terminal unknown (`CONTRACTS.md:98-112` has no completeness/inventory field).
3. **P1-WF-004:** fan-out → join with empty/missing/duplicate/late/failed partitions (`CONTRACTS.md:144-146` only says DAG).
4. **P1-STR-003:** bounded buffer saturation → explicit backpressure/no silent market-event loss (`CONTRACTS.md:114-128` lacks buffer/drop/gap fields).
5. **P1-PLC-001:** placement preflight → portable artifact staging → dispatch; explicitly deferred (`IMPLEMENTATION-SEQUENCE.md:32-34`).
6. **P1-SKL-004:** mutation run → WSL disposable evidence; only principle/documentation exists (`ARCHITECTURE-SPINE.md:196`, `STACK-AND-EVALUATION.md:48+`).

## Pass-II-only additions learned

The candidate adds several constraints not present in the frozen Pass-I scenario baseline: `change_request` staging (AD-8/`CONTRACTS.md:66-79`); four explicit cross-app composition modes and intersection authority (AD-10); dummy Book prohibition and separate `ResolvedRunConfig`/`UngovernedWorkConfig` (AD-11); recipe identity as output release fp1 plus CT-07 lineage (AD-12); product-session journal projection and durable task-graph persistence as the only daemon additions (AD-16); UI contribution DTOs with JSON Render/MCP Apps as non-authoritative presentation adapters (AD-17/`UI-HOST.md`); first-party trust and hard dependency errors on enable (AD-18); WSL-only current mutmut execution on disposable copies (AD-19); Portfolio Manager as display label while retaining `desk_slug=pm`/`pm-coordination` (AD-22); and explicit refusal of live non-Book trading pending L36/operator answer (`OPERATOR-QUESTIONS.md:10-26`). These additions improve authority and identity precision but create the BR-MKT contradiction and leave several P1 transition oracles deferred.

## Repair priority

Before implementation beyond Slice 1, add executable contract/journey rows for CAP atomic install, OP partial artifacts, WF joins/triggers/review, STR backpressure/gaps, PLC preflight/restore, and SKL evidence. Resolve Q1/L36 by either narrowing the frozen P1-MKT scope or amending the constitution; otherwise the candidate cannot truthfully claim complete scenario support.
