@draft @specification_only
Feature: Attributed data, streams, and command ownership

  Scenario: P1-DATA-001 preserve provider disagreement
    Given two providers disagree for the same field and time window
    When a consumer requests the data
    Then values and warnings remain attributed to their providers
    And the system does not silently merge them

  Scenario: P1-DATA-003 preserve historical results after source revision
    Given a completed run used source revision one
    When the provider publishes a correction as revision two
    Then the old result remains unchanged
    And a rerun has a new identity with a comparison to both revisions

  Scenario: P1-DATA-004 distinguish truncation from empty data
    Given a preview reaches its row cap
    When the consumer inspects the result
    Then truncation is reported distinctly from empty, unavailable, denied, and complete results

  Scenario: P1-DATA-007 reject incomplete returned weights
    Given a GPU job reports success but its returned weights are missing or truncated
    When promotion is requested
    Then the run is not promotable
    And completeness and content-hash failure are visible

  Scenario: P1-DATA-008 catalogue a non-trading artifact
    Given a clustering or report job produces a data/ML artifact
    When the job completes
    Then the artifact is catalogued and reusable
    And no bot, Book, or BMS wrapper is required

  Scenario: P1-STR-001 mark replay to live explicitly
    Given a subscription begins in replay and then reaches live
    When the live boundary is crossed
    Then replay-complete, cursor, and live phase are observable
    And each event retains event-time and receive-time provenance

  Scenario: P1-STR-002 surface duplicate and gap conditions
    Given a reconnect delivers a duplicate and leaves a sequence gap
    When the consumer resumes
    Then duplicate identity is deduplicated
    And the gap is surfaced or replayed rather than represented as false continuity

  Scenario: P1-STR-004 cancel one shared-feed consumer
    Given two consumers share one feed
    When consumer A cancels
    Then consumer B continues receiving events
    And ownership and reference count remain correct

  Scenario: P1-MKT-001 preserve default Book/BMS semantics
    Given the default Book/BMS composition is configured
    When it is run under regression and comparability checks
    Then its accounting and command semantics remain unchanged

  Scenario: P1-MKT-003 keep intelligence modes explicit
    Given an intelligence component is absent, shadow, optional, or active
    When a composition is validated
    Then its selected mode is explicit
    And shadow output cannot silently become production command input

  Scenario: P1-MKT-007 block unknown external order state
    Given an external order outcome is unknown during handover
    When a new owner requests command authority
    Then reconciliation or manual approval is required
    And no automatic retry or new-owner assumption occurs
