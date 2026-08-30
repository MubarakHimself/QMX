# Plugin Architecture

## Intent

Plugins must extend QMX without forcing core rewrites.

The plugin architecture should support daemon, UI, worker/runtime, skills, tools, and configuration while preserving strict host ownership of lifecycle and compatibility.

## One logical plugin, multiple optional entries

A logical plugin package may contain:

```text
plugin/
  manifest
  daemon/
  ui/
  worker/
  skills/
  tools/
  hooks/
  loops/
  graphs/
  migrations/
  assets/
```

Not every plugin needs every entry.

Examples:

- Memory provider: daemon only.
- Artifact viewer: UI only.
- Backtesting integration: daemon + worker + UI.
- Research source plugin: daemon + tools + optional UI.
- New graph pack: graph definitions + optional settings UI.

## Plugin manifest

Candidate fields:

- id
- version
- name
- description
- QMX SDK compatibility
- daemon entry
- UI entry
- worker entry
- provides capabilities
- requires capabilities
- optional capabilities
- permissions
- settings schema
- migrations
- contributions
- lifecycle hooks
- assets

## Capability model

Plugins should contribute capabilities through stable contracts rather than importing private internals.

Examples:

- `memory.provider`
- `model.provider`
- `tool.provider`
- `compute.provider`
- `browser.provider`
- `artifact.renderer`
- `graph.definition`
- `loop.definition`
- `ui.navPanel`
- `ui.settingsSection`

## Lifecycle

Study Cordis heavily here:

- mount
- dependencies pending
- activate
- register reversible effects
- disable
- unload
- reload
- upgrade
- rollback

Every contribution should have a disposer/unregistration path.

## Upgradeability

Plugin upgrade must consider:

1. manifest compatibility
2. SDK version compatibility
3. config migrations
4. state/data migrations
5. daemon compatibility
6. UI-bundle compatibility
7. worker compatibility
8. rollback if activation fails

Development mode should support hot reload where safe.

## Trust tiers

Recommended design:

### Tier 1 — Declarative

Can contribute configuration, commands, schemas, settings descriptors, static graph/loop definitions.

### Tier 2 — UI-sandboxed

Can render extension components but not access daemon internals directly.

### Tier 3 — Runtime plugin

Can register daemon services/tools/providers behind explicit permissions.

### Tier 4 — Worker/host plugin

Can run code near files/processes/compute and requires stronger trust.

Avoid BB's full-trust-by-default model for all third-party extensions.

## Plugin-install UI

The UI is only the control surface.

When a user installs/enables/disables/upgrades a plugin:

```text
UI
 -> daemon plugin manager
 -> validate manifest
 -> check compatibility
 -> resolve permissions/dependencies
 -> install/activate
 -> daemon publishes new extension catalog
 -> UI loads/refreshes declared UI contributions
```

The UI never mutates runtime internals directly.
