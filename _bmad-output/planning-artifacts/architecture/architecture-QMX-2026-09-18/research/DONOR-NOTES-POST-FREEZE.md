---
name: Donor workflow notes
arrived: after candidate freeze qmx-workflows-arch-2026-09-18-a
workflow: qmx-workflows-stage-a-donors (wf_01a0b3c99a417113ad6735d5a143d029)
status: complete — 6 notes — does not mutate frozen spine hashes or the Codex ZIP
---

# Donor notes (post-freeze)

These arrived after `CODEX-CHALLENGE-INPUTS.zip` was sealed. They **confirm** the frozen ADs; they do not reopen Stage A. Stage C may fold them as extra evidence.

| Reference | Confirms spine | Do not copy |
|---|---|---|
| **Hermes** plugins / desktop / dashboard | Manifest vs schema vs handler vs register; config vs plugin state; `dispatch_tool` as real invocation | Warning-and-continue missing deps; capabilities as consent without sandbox; in-process full-trust; register-crash-and-continue; three UI runtimes as one PluginContext |
| **n8n** | Descriptor vs instance graph vs execution; explicit connections; draft vs published; Code node is a runner, JSON does not execute | Embed n8n (SUL/OEM); treat Board layout as execution graph; Retry-On-Fail as same-task mutation |
| **JSON Render v0.20.0** | Catalog-constrained UI; host supplies implementations | Every pane as a spec; catalog as authority; pin as daemon dep |
| **MCP Apps SEP-1865** | Sandboxed tool HTML; host intercepts tools/call | Native panes as `ui://`; iframe as domain runtime |
| **mutmut 3.8.0** | Fork/WSL; `apply` writes disk; score ≠ architecture | Product dependency; apply on shared worktree |
| **OpenBB** | Provider fetchers ≠ widgets.json/apps.json; shared parameters as bindings | OpenBB runtime; conflating provider with presentation |

Frozen AD-17/AD-18/AD-19 already match this split. No spine amendment required from this run.
