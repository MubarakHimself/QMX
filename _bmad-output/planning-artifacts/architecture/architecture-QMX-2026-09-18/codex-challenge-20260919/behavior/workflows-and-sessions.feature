@draft @specification_only
Feature: Explicit workflow semantics and isolated sessions

  Scenario: P1-WF-001 execute only the selected runnable subgraph
    Given a storyboard contains executable nodes, notes, and evidence-only relationships
    When the author selects and validates a runnable subgraph
    Then only selected executable nodes run
    And notes and non-selected nodes do not run

  Scenario: P1-WF-002 reject a shape-compatible semantic mismatch
    Given two ports accept JSON-shaped values with incompatible semantic types
    When the author connects the ports
    Then validation refuses the connection with the semantic mismatch
    And no run is created

  Scenario: P1-WF-003 apply the declared join policy
    Given three left inputs and two right inputs
    When the author selects zip, keyed join, or Cartesian join
    Then execution uses the selected cardinality and key policy
    And missing, duplicate, or late partitions are reported according to that policy

  Scenario: P1-WF-004 stop an unbounded nested cycle
    Given a nested subflow calls its parent under a bounded-cycle policy
    When the cycle exceeds its declared budget
    Then the run ends with a stable cycle-budget refusal
    And no unbounded work continues

  Scenario: P1-WF-006 keep a waiting run pinned during an upgrade
    Given a run is waiting on provider version one
    When provider version two is activated
    Then the waiting run remains pinned to version one
    And a newly started run may use version two

  Scenario: P1-WF-007 deduplicate overlapping schedule triggers
    Given a scheduled run is still active when an equivalent trigger arrives
    When the second trigger is received
    Then the declared skip, queue, coalesce, or parallel policy is applied
    And the deduplication identity is recorded

  Scenario: P1-SES-001 isolate concurrent sessions
    Given workflow, strategy, and ML sessions run concurrently
    When each session invokes an operation and retrieves history
    Then context, grants, history references, and command targets remain isolated

  Scenario: P1-SES-002 restore context after tab disconnect
    Given a session has attached work context and active versions
    When its tab closes and the operator reconnects
    Then the session context and versions are restored independently of tab identity
    And old intent is not replayed as a new command

  Scenario: P1-SES-003 hand app-use editing to authoring
    Given an app-use session requests an implementation edit
    When the request is submitted
    Then implementation is not edited by the app-use session
    And a typed change request can be handed to an authoring session

  Scenario: P1-SES-004 refuse nested grant escalation
    Given a composite app-use session contains a component requesting authoring or trading scope
    When the component requests that scope
    Then the host denies the request
    And component wishes are not unioned into the composite grant set
