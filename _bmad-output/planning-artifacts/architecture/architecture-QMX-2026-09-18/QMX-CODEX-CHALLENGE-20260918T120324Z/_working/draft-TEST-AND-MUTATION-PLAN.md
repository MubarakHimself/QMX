# Test and mutation plan (draft)

## Gate order

Run bounded tests in this order; a pass is evidence for the named behavior only, never architecture ratification.

1. **Graph safety:** self-loop, 3-cycle, duplicate/disconnected edges; compiler and registration parity; A→B completion schedules B with deterministic mapping.
2. **Durability:** materialize graph, edges, leases, and job evidence; restart; recover through the sole sqlite writer; verify backup/restore on disposable state.
3. **Wire/session:** authenticated command reaches exactly one owner; typed refusal; grant intersection; durable context revision/CAS; reconnect does not replay intent; idempotency key survives restart.
4. **Contribution/index:** valid headless package discovery; duplicate/incompatible rejection preserves prior index; migration failure separates installed/active; missing dependency is typed unavailable; removal names dependants and protects pinned runs.
5. **Operation truth:** direct/CLI/node/app/copilot semantic parity; partial artifact inventory; unknown upstream outcome; cancel-vs-complete race; artifact expiry.
6. **Workflow:** messy storyboard executes selected subgraph only; typed edge cardinality; fan-out/join empty/late/failed partitions; retry failed branch without duplicating successful effects; review evidence/resume; trigger dedupe/concurrency.
7. **Data/ML:** provider disagreement attribution; entitlement/unavailable/empty/truncated distinction; recipe pins revisions and leakage-sensitive fields; incomplete weights fail; local-to-remote staging is explicit/refused.
8. **Streams:** replay boundary, live handoff, event/receive times, ordering/dedupe/gaps, bounded backpressure, shared subscription cancellation.
9. **End-to-end bounded journey:** real QML governed artifact → QMB compile → QMN paper/conformance, with provenance and no synthetic Book/BMS records for non-trading work.
10. **Trading regression:** default Book/BMS remains unchanged; explicit command binding and handover/reconciliation. Keep non-Book live path blocked until operator/constitution amendment.

## Mutation plan

Mutation is a test-strength probe, not a requirements generator and not proof of trading safety. Prefer targeted semantic mutants: reverse a grant intersection to union; drop idempotency key; accept self-loop; skip successor dispatch; mark partial artifact complete; suppress gap event; replay an acknowledged command; substitute provider revision; erase venue/account binding; and make a UI disconnect cancel durable work. Each mutant needs a test that fails for the intended reason and a retained survivor/equivalent/invalid/timeout/error classification.

On Windows, `mutmut` is optional and current support requires WSL/fork behavior. If run, copy the candidate/code to a disposable isolated WSL workspace; never mutate or share the worktree. Preserve baseline, mutation scope, raw logs, tool/version, environment, timeout, and classifications. If WSL or dependency setup is unavailable, record “not run,” not green.

## Evidence and false-green controls

- Separate source-inspection assertions from runtime integration tests.
- Do not treat CT-07 ExperimentSpec successor tests as task-graph control-flow proof.
- Do not report QMA as green while its pinned environment is blocked.
- Keep existing QMF/QMB/QMN suites as regression gates, but require one cross-component journey.
- For every test record owner, contract ID, setup identity, expected oracle, observed state, and whether behavior is existing or proposed.
- Retest after candidate changes; never use a candidate review as evidence of executed behavior.
