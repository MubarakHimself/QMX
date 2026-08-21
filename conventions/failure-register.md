# Failure-register convention (NFR-11)

**This is a Tier-1 artifact obligation on every subsequent story in this
workspace.** Whenever a package story delivers a **designed failure mode** — any
condition the code is built to detect and handle (a typed refusal, a retry, a
degraded state, a blocked stream) — that package ships a **failure-register
entry alongside its tests**. The entry is written for someone who was **not in
the design room**: a maintainer or an operator reading it cold must understand
what broke and what to do.

A designed failure with no register entry is an **incomplete story**, the same
way a missing test is.

## Where it lives

Alongside the package's tests, as `packages/<pkg>/FAILURES.md` (or
`extensions/<pkg>/FAILURES.md`). One file per package; append one entry per
designed failure mode. The scaffold created in Story 1.1 declares no failure
modes yet, so no `FAILURES.md` exists until the first real behavior lands.

## Required fields (every entry)

| Field | What it answers |
|---|---|
| **Failure class** | What kind of failure is this? (e.g. `invalid input`, `unavailable dependency`, `storage failure`, `transient venue failure` — align with the CT-04 refusal categories where the failure surfaces as a typed refusal.) |
| **Detection** | How is it detected, and where? What signal or check fires. |
| **Auto-recovery / retry semantics** | Does anything retry or self-heal? Under what condition, how many times, with what backoff — or explicitly "no automatic retry". |
| **Visible degraded state** | What state does the system sit in while degraded? What is still allowed, what is blocked (e.g. "command stream blocked until explicit resolution"). |
| **Notification tier** | Who is told and how loudly — silent/log, operator-visible, alarm. |
| **Product-user affordance** | In plain words for the end user: **what failed, why, can I retry, and what does a retry do?** |

## Entry template

```md
### FR-<n>: <short name of the failure mode>

- **Failure class:** <category>
- **Detection:** <how/where detected>
- **Auto-recovery / retry:** <condition + limits, or "none">
- **Visible degraded state:** <what is blocked / still allowed>
- **Notification tier:** <silent-log | operator-visible | alarm>
- **Product-user affordance:** <what failed, why, can I retry, what a retry does>
```

## Why

Failures are part of the contract, not an afterthought. Recording them in a
consistent, plain-language shape keeps the platform legible to humans and agents
(L5) and gives operators a real answer at 3 a.m. instead of a stack trace.
