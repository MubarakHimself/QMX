@draft @specification_only
Feature: Catalog completion scenarios

  @pass2_added
  Scenario: P2-CAP-007 retain the last usable index after partial rebuild
    Given a contribution index rebuild fails after partial validation
    When the rebuild reports corruption
    Then the prior complete index remains active
    And the partial index is not published

  @pass2_added
  Scenario: P2-SES-009 preserve session grants across package refresh
    Given a session has explicit grants for one package version
    When the package is refreshed
    Then the session keeps its prior grant set
    And new scopes require explicit approval

  @pass2_added
  Scenario: P2-SES-010 refuse a stale session command target
    Given a restored session references a retired account or instance
    When it attempts an operation
    Then invocation is refused with the stale target identified
    And no replacement target is inferred

  @pass2_added
  Scenario: P2-DATA-010 reject incompatible recipe revisions
    Given a recipe pins a source revision whose schema has changed incompatibly
    When execution preflight runs
    Then the recipe is refused with the schema mismatch
    And no silent field remapping occurs

  @pass2_added
  Scenario: P2-OP-006 resume a paused operation from durable state
    Given an operation is paused after a durable checkpoint
    When the operator resumes it
    Then completed effects are not repeated
    And progress continues from the checkpoint

  @pass2_added
  Scenario: P2-WF-009 preserve partial workflow outputs
    Given one workflow branch succeeds and another branch fails
    When the workflow reaches a terminal state
    Then successful outputs are labelled partial
    And the aggregate is not reported as fully successful

  @pass2_added
  Scenario: P2-SES-011 require approval after reconnect
    Given a session reconnects while a run awaits approval
    When the run is displayed
    Then its evidence and pending decision are restored
    And reconnect does not imply approval

  @pass2_added
  Scenario: P2-OP-007 refuse a retry with an unknown side effect
    Given an operation timed out after an external side effect may have succeeded
    When retry is requested
    Then the system requires reconciliation or explicit override
    And it does not issue a blind duplicate

  @pass2_added
  Scenario: P2-DATA-011 retain lineage through model promotion
    Given a model is promoted from a pinned dataset and evaluation artifact
    When the model is bound to a consumer
    Then dataset, weights, evaluation, and binding identities remain traceable

  @pass2_added
  Scenario: P2-CAP-008 refuse removal of a pinned in-flight version
    Given an in-flight run is pinned to a capability version
    When removal of that version is requested
    Then removal is refused or deferred with the run identified
    And the run is not retargeted

  @pass2_added
  Scenario: P2-MKT-011 block handover after a partial fill
    Given an external order has a partial fill and unresolved remainder
    When command ownership handover is requested
    Then the residual order state is recorded
    And handover blocks until reconciliation or approval

  @pass2_added
  Scenario: P2-OP-008 distinguish cancellation from interruption
    Given a running operation is interrupted by worker loss
    When its state is reconciled
    Then the result is interrupted or unknown rather than cancelled
    And recovery options identify the last durable checkpoint

  @pass2_added
  Scenario: P2-CAP-009 export an unavailable dependency honestly
    Given an exported package references an unavailable provider
    When another installation imports it
    Then the dependency is shown as unavailable
    And invocation cannot report successful execution

  @pass2_added
  Scenario: P2-PLC-007 restore only after cross-store verification
    Given a restore contains inconsistent job and artifact records
    When verification compares their identities and lineage
    Then restore remains blocked
    And inconsistent state is surfaced for repair

  Scenario: P1-CAP-003 recover a failed activation migration
    Given installation completed but its activation migration fails
    When activation reaches the migration error
    Then installed and active states remain distinct
    And rollback or a precise recovery action is reported

  Scenario: P1-OP-003 retain a labelled partial artifact after worker loss
    Given a job produced one artifact before its worker failed
    When the run reaches a terminal state
    Then the artifact is listed as partial with its completeness status
    And the run is not reported as fully successful

  Scenario: P1-WF-005 ignore layout-only changes
    Given a validated workflow has a stable semantic graph
    When only node positions or display names change
    Then no semantic dependency is invalidated and no recomputation starts

  Scenario: P1-SES-005 prevent history from retargeting a command
    Given retrieved history mentions a different account
    When the operator issues a command for the current account
    Then the command binds the explicit current account target
    And the historical mention is retained only as evidence

  Scenario: P1-SES-006 preserve specialist ownership
    Given a specialist produces a result behind a copilot surface
    When the operator inspects the result
    Then specialist identity, ownership, and evidence remain visible

  Scenario: P1-DATA-002 distinguish same ticker identities
    Given the same ticker exists at two venues or currencies
    When an operation selects an instrument
    Then venue, currency, and instrument identities remain distinct
    And no target is selected from ticker text alone

  Scenario: P1-DATA-005 record heterogeneous recipe alignment
    Given a recipe combines sources with different timezones, calendars, and sparse data
    When the recipe executes
    Then alignment policy, exclusions, and leakage checks are recorded

  Scenario: P1-DATA-006 compare side-by-side model versions
    Given two model versions use the same pinned recipe
    When both evaluations complete
    Then weights, evaluations, and consumer bindings remain distinct and comparable

  Scenario: P1-STR-003 expose bounded-buffer overload
    Given a slow consumer fills a bounded stream buffer
    When overload occurs
    Then the declared block, drop, spill, or disconnect policy is observable
    And any loss is evidenced

  Scenario: P1-STR-005 prevent replay from becoming a live command
    Given a replay event reaches a trading-capable consumer
    When the consumer evaluates the event
    Then replay provenance prevents live-command interpretation absent explicit policy

  Scenario: P1-MKT-002 validate a complete non-Book composition
    Given a complete non-Book trading composition has its own accounting and risk semantics
    When it is validated and simulated
    Then it succeeds without dummy Book or BMS records

  Scenario: P1-MKT-004 keep commands targeted across accounts
    Given the same symbol is available through two brokers and accounts
    When one credential is revoked during command preparation
    Then every command remains explicitly targeted
    And another account is not substituted

  Scenario: P1-MKT-005 transfer a flat command owner sequentially
    Given the predecessor is stopped and flat
    When an approved handover completes
    Then exactly one command owner is recorded before and after the transition

  Scenario: P1-MKT-006 record a known residual position
    Given a predecessor has a known residual position at handover
    When the new owner is prepared
    Then the residual is recorded and handled explicitly
    And the system does not assert that the account is flat

  Scenario: P1-MKT-008 do not unfill on software rollback
    Given the new owner has produced a fill
    When software rollback is requested
    Then the fill remains in external evidence and positions
    And rollback does not claim to reverse it

  Scenario: P1-MKT-009 block stale-process authority
    Given an old process restarts after ownership transferred
    When it attempts a command
    Then stale local state cannot restore command authority

  Scenario: P1-MKT-010 refuse ambiguous intelligence writers
    Given two intelligence versions claim one production command role
    When deployment is validated
    Then explicit arbitration and consumer pinning are required
    And ambiguous writers are refused

  Scenario: P1-PLC-003 recover interrupted staging safely
    Given remote staging is interrupted or a supplied path escapes its allowed root
    When staging resumes or validates the path
    Then no partial or unauthorized read occurs
    And the state is cleanly resumable or explicitly refused

  Scenario: P1-APP-001 consume a saved artifact across apps
    Given App A exposes a saved artifact to App B
    When App B resolves the artifact
    Then content identity, version, and authorization are checked
    And private implementation paths are not imported

  Scenario: P1-APP-002 call an exported operation with declared semantics
    Given App B calls an exported operation from App A
    When the call is made
    Then meaning, cardinality, timing, effects, errors, cancellation, and reentrancy follow the declaration

  Scenario: P1-APP-003 attribute partial multi-app workflow failure
    Given a workflow coordinates multiple independently usable apps
    When one app fails after another succeeds
    Then the partial result attributes the failure to its app
    And the workflow is not reported as wholly successful

  Scenario: P1-APP-004 make shared dependency instance choice visible
    Given a composite pins two apps sharing provider P
    When the composite is configured
    Then shared versus independent provider instances and compatible versions are visible

  Scenario: P1-APP-005 keep an old composite run pinned
    Given App B has a waiting run using provider version one
    When App A upgrades provider P to version two
    Then App B's run remains pinned to version one
    And settings do not leak across instances

  Scenario: P1-APP-006 report a missing composite component
    Given a composite component becomes unavailable
    When the composite is inspected or invoked
    Then degraded state names the missing component
    And whole-app success is not reported

  Scenario: P1-APP-007 compute by identity rather than display label
    Given a shared parameter has a display value distinct from its identity
    When the parameter is renamed
    Then computation continues to use the identity field

  Scenario: P1-APP-008 reject a conflicting parameter cycle
    Given shared parameters form a cycle or have conflicting writers
    When validation runs
    Then a deterministic validation error is returned
    And no oscillating execution begins

  Scenario: P1-SKL-001 scope a skill that steals a neighbor prompt
    Given a skill passes its happy prompt but activates for a neighboring specialist request
    When activation evaluation runs
    Then the evaluation fails or the skill scope is corrected

  Scenario: P1-SKL-002 reject a self-judged stub success
    Given a skill author or model judge reports success for its own stub
    When an independent artifact or tool oracle evaluates it
    Then the false green result is rejected

  Scenario: P1-SKL-004 isolate Windows mutation evaluation
    Given mutation evaluation is requested on Windows with a shared worktree
    When the evaluation is prepared
    Then it is refused there and requires a disposable WSL copy
    And baseline, survivors, invalids, timeouts, errors, and raw logs are preserved

  @pass2_added
  Scenario: P2-SES-007 reject a stale credential at invocation
    Given a session retains a credential that has become stale or revoked
    When it invokes the operation
    Then preflight refuses the invocation with an explicit credential state
    And no alternate credential is selected silently

  @pass2_added
  Scenario: P2-STR-006 preserve stream ownership after UI disposal
    Given a subscription is owned by a durable consumer and displayed in a UI tab
    When the tab is disposed
    Then the subscription remains available to its durable consumer
    And UI disposal does not cancel shared work

  @pass2_added
  Scenario: P2-WF-008 resume a paused run without duplicating completed effects
    Given a workflow is paused after a completed effect and before its next step
    When the operator resumes it
    Then the completed effect is not repeated
    And the run continues from its durable checkpoint

  @pass2_added
  Scenario: P2-SES-008 require explicit approval after reconnect
    Given a session reconnects while a run is awaiting human approval
    When the operator reviews the resumed run
    Then the approval decision and evidence are shown
    And reconnect does not imply approval

  @pass2_added
  Scenario: P2-DATA-009 refuse a recipe with a stale entitlement
    Given a recipe's source entitlement has expired since it was authored
    When execution preflight runs
    Then execution is refused with the entitlement state
    And no substitute source is selected silently

  @pass2_added
  Scenario: P2-INT-001 preserve partial review truth
    Given a review has one real branch and one stubbed-success branch
    When aggregate completion is calculated
    Then the review is marked partial or unverified
    And the aggregate is not presented as fully successful
