---
name: UI host readiness map
sitting: architecture-QMX-2026-09-18
---

# UI host readiness (backend contracts, not chrome)

Reference images are inspiration only.

| Surface | Backend now | Host binds | Deferred |
|---|---|---|---|
| Navigation | desks/scope_path; plugin roster query | contribution descriptor (id, title, principal) | layout |
| Commands | CT-40 seed; QMN powers; qmb CLI | AD-3 op_id | palette chrome |
| Rich views | none as ui_view | native pane vs json-render vs MCP App | GAP-0081 |
| Parameter forms | UiFlag / AD-26 | catalog-constrained forms | styling |
| Context providers | ContextCompiler refs | product-session blob (AD-8) | |
| App-use sessions | **absent** (this sitting adds) | AD-8 | |
| Events/logs | wire events; QMN evidence HTTP | snapshots authoritative | |
| Reconnect | producer_id + attach/since_seq | must not cancel jobs | |

Three presentation lanes: native QMX pane; JSON Render registered components; MCP Apps tool HTML. None own identity or permission.
