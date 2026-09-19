@draft @specification_only
Feature: Discoverable capabilities and honest operation lifecycle

  Scenario: P1-CAP-001 install and discover a valid headless package
    Given a valid package declares a typed operation and its owner and version
    When an operator installs and activates the package
    Then the catalog exposes the operation through catalog, CLI, node, and app discovery
    And each projection preserves the same schema, owner, version, and effect class
    And discovery does not require a navigation pane

  Scenario: P1-CAP-002 reject an incompatible contribution atomically
    Given an active catalog index and a package with a duplicate ID or incompatible host version
    When the operator attempts activation
    Then activation is refused with a stable compatibility error
    And the prior catalog index remains usable and unchanged

  Scenario: P1-CAP-004 do not silently expand an existing session grant
    Given an app-use session has an established tool and grant set
    When a new package is activated
    Then the existing session's tool and grant set remains unchanged
    And a separate explicit re-grant is required before the new capability is usable

  Scenario: P1-CAP-005 remove a dependency used by a waiting run
    Given a waiting run is pinned to an installed provider instance used by a composite
    When the operator requests removal of that provider
    Then the system names the dependent composite and waiting run
    And the run either resolves its pinned instance or stops with an explicit dependency state
    And no replacement instance is selected silently

  Scenario: P1-CAP-006 export without private bindings
    Given an app package contains local paths, chat links, and credentials
    When the operator exports the package
    Then private paths, credentials, and chat links are excluded
    And required bindings are represented as explicit unresolved bindings

  Scenario: P1-OP-001 invoke one operation through equivalent doors
    Given one versioned pure operation is available through direct, CLI, node, and app doors
    When each door invokes it with equivalent inputs
    Then each result has equivalent semantics, errors, and provenance
    And presentation differences do not change the operation's effect

  Scenario: P1-OP-002 recover after an acknowledgement is lost
    Given an upstream side effect may have succeeded
    When its acknowledgement is lost before the caller receives it
    Then the run enters unknown or reconcile state
    And the system does not blindly retry the external effect

  Scenario Outline: P1-OP-004 cancel according to the run state
    Given a run is <state>
    When the operator requests cancellation
    Then the system returns a stable race-safe outcome for <expected>
    Examples:
      | state          | expected                              |
      | queued         | cancelled before execution             |
      | running        | cancellation requested or confirmed    |
      | non-cancelable | explicit refusal and current state     |
      | complete       | already complete with no new execution |

  Scenario: P1-OP-005 distinguish an expired artifact
    Given a completed run produced an artifact whose retention has expired
    When a consumer resolves the artifact
    Then resolution reports explicit expiry and recovery information
    And the consumer does not receive a fabricated empty result
