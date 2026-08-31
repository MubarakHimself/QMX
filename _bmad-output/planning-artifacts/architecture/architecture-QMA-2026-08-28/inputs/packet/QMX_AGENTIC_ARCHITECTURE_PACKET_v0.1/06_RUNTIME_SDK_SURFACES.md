# Proposed QMX In-House SDK Surfaces

This is a conceptual API map, not a concrete language/API specification.

## Core

- `qmx.role`
- `qmx.bot`
- `qmx.agent`
- `qmx.session`

## Orchestration

- `qmx.mission`
- `qmx.task`
- `qmx.graph`
- `qmx.loop`
- `qmx.hook`
- `qmx.scheduler`

## Cognition

- `qmx.prompt`
- `qmx.context`
- `qmx.memory`
- `qmx.knowledge`
- `qmx.skill`
- `qmx.rlm`

## Models

- `qmx.model`
- `qmx.provider`
- `qmx.auth`
- `qmx.proxy`

## Tools and environments

- `qmx.tool`
- `qmx.mcp`
- `qmx.workspace`
- `qmx.environment`
- `qmx.sandbox`
- `qmx.browser`
- `qmx.computer`
- `qmx.compute`

## State and evidence

- `qmx.ledger`
- `qmx.artifact`
- `qmx.experiment`
- `qmx.trace`
- `qmx.log`
- `qmx.metrics`
- `qmx.eval`

## Communication

- `qmx.mailbox`
- `qmx.message`
- `qmx.bus`

## Domain

- `qmx.backtest`
- later QMX market/trading domain contracts

## UI SDK — separate package

The UI SDK should be independently versioned from the daemon SDK.

Candidate surfaces:

- `qmx.ui.command`
- `qmx.ui.activity`
- `qmx.ui.sidebar`
- `qmx.ui.view`
- `qmx.ui.panel`
- `qmx.ui.editor`
- `qmx.ui.artifactRenderer`
- `qmx.ui.status`
- `qmx.ui.settings`
- `qmx.ui.notification`
- `qmx.ui.contextMenu`
- `qmx.ui.dashboard`
- `qmx.ui.theme`

The UI SDK talks to the daemon through typed client APIs. It should not import daemon internals.
