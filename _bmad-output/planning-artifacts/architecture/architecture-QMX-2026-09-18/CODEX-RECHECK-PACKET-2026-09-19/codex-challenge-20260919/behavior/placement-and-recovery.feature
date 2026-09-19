@draft @specification_only
Feature: Placement, recovery, and lifecycle continuity

  Scenario: P1-PLC-001 refuse dispatch when preflight fails
    Given local GPU or remote entitlement is missing
    When an operator requests dispatch
    Then preflight reports the missing environment or entitlement
    And scheduling and cost-incurring execution do not begin

  Scenario: P1-PLC-002 make a local path portable before remote execution
    Given a remote worker is supplied a local file path
    When preflight resolves inputs
    Then the file is staged as an authorized content-identified artifact
    Or execution is refused before the worker reads the path

  Scenario: P1-PLC-004 continue a server-owned job across UI closure
    Given a remote job is server-owned and running
    When the laptop or UI closes
    Then the job continues according to its placement policy
    And reconnect observes authoritative state rather than starting a duplicate

  Scenario: P1-PLC-005 reconcile coordinator loss
    Given a worker completes while its coordinator is unavailable
    When the coordinator returns
    Then completion is reconciled from durable evidence
    And no duplicate run is created

  Scenario: P1-PLC-006 refuse an unverified restore
    Given a backup is missing a blob or has a stale index
    When restore verification runs
    Then verification fails with the missing identity or hash
    And the state is not resumed as healthy

  Scenario: P1-SKL-003 pin active work during skill activation
    Given an old session or run uses an active skill version
    When a new skill version is activated
    Then existing work remains pinned
    And use of the new version requires explicit activation or grant
