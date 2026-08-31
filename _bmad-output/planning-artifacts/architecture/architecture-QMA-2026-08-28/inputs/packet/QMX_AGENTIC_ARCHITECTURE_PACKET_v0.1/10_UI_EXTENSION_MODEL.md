# UI Extension Model

## The simple mental model

The QMX UI is a **stable shell with named extension points**.

Plugins do not own the shell.

The shell owns:

- layout
- navigation
- lifecycle
- keyboard/command routing
- resizing
- persistence of UI state
- compatibility
- permissions
- plugin enable/disable/update
- error containment

Plugins contribute content.

## Stable UI shell

Candidate host surfaces:

```text
Activity Bar
Sidebar
Primary Workspace / Editor
Secondary Panel
Bottom Panel
Status Bar
Command Palette
Settings
Notifications
Context Menus
Artifact Views
Dashboard Widgets
```

The exact visual design is a later UI session.

## Contribution points

Candidate API:

```text
registerCommand()
registerActivityItem()
registerSidebarView()
registerWorkspaceView()
registerPanel()
registerBottomPanel()
registerStatusItem()
registerSettingsSection()
registerArtifactRenderer()
registerContextMenu()
registerDashboardWidget()
registerTheme()
```

## Three classes of UI contribution

### 1. Declarative

Best default.

Examples:

- settings fields
- commands
- navigation items
- menu items
- badges
- schemas
- table definitions
- simple forms

These can be safely upgraded and are UI-framework independent.

### 2. Sandboxed component

For richer custom views:

- backtest visualizer
- research evidence graph
- experiment explorer
- trace viewer
- chart/replay surface

The plugin receives a typed UI client and scoped daemon APIs.

### 3. Trusted host/native extension

Rare.

Used only where a component genuinely requires host/native capabilities.

Avoid making ordinary plugins native dynamic libraries.

## Critical Rust consideration

If QMX uses a **pure native Rust UI**, arbitrary hot-loadable third-party UI components become substantially harder because Rust dynamic ABI is not a stable plugin boundary.

Therefore, if rich runtime-installable UI plugins are a major requirement, investigate one of:

1. **Rust/Tauri host + web component extension surface**
2. **Rust host + WASM/component-model UI plugins**
3. **Declarative UI schema for most plugins + a small set of trusted compiled views**
4. another stable cross-language component boundary

Do **not** design the plugin system around loading arbitrary Rust `dylib` UI modules unless the architecture agent can justify the ABI/versioning strategy.

## Logical plugin with daemon + UI

A plugin may have both daemon and UI contributions.

Example:

```text
Backtesting Plugin
  daemon:
    registers backtest service/tools
  worker:
    launches compute
  ui:
    adds Backtests sidebar
    adds report renderer
    adds settings
```

They communicate through the QMX daemon contract, not shared process memory.

## Install/update flow

```text
User clicks Install/Update
        ↓
UI sends command
        ↓
Daemon Plugin Manager
        ↓
manifest + compatibility + permissions check
        ↓
install/migrate/activate
        ↓
daemon publishes Extension Catalog update
        ↓
UI loads/refreshes declared contributions
```

If activation fails:

- previous version remains/rolls back where feasible
- UI shows diagnostic
- daemon remains healthy

## Plugin Settings

This directly supports the desired workflow:

- install an MCP
- enable a tool
- add a model provider
- configure a memory backend
- attach a capability to a Role
- enable a graph
- add a UI panel

without manually editing QMX internals.

The settings UI is a view over typed daemon/plugin configuration schemas.

## UI visibility of backend state

Anything operationally important should be inspectable:

- Agents/Bots
- Missions/Tasks
- graphs
- loops currently active
- hook blocks/approvals
- ledgers
- traces/logs
- model/provider health
- worker/compute state
- plugin versions
- tools/MCPs
- memory/context diagnostics where appropriate

UI is an observability/control surface, not the runtime itself.
