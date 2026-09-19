---
name: Copilot, apps, Artifact Library
sitting: architecture-QMX-2026-09-18
---

# Copilot, Artifact Library, and app orchestration

## Artifact Library

**Stays** a projection over listed `fp1` kinds (Workbench AD-3). Upgrade is **discovery**, not a new database.

| Rail | Identity | Search |
|---|---|---|
| Artifact | fp1 + kind | `qmb.library.search` |
| Knowledge | source/snapshot/locator | CT-44 |
| Contribution | plugin_id:local_id | `published_contributions` concatenate |
| Hypothesis | research_ref | `qml.research` only |

UI may show one “Library” chrome over typed hits. It must not collapse kinds.

## Mini-apps

A mini-app is a **named grouping**: pack id + version + exported operations + optional views + copilot profile. Identity of the grouping is the installed instance, not a registry kind. Headless packs are valid: they appear as workflow steps without navigation.

## Copilot

One product identity: QuantMind / QMX Copilot.

| Profile | May | Must not |
|---|---|---|
| Authoring | Create/revise workflows, code, packs, skills using **granted** tools | Inherit another session’s account target or full toolset |
| App-use | Inspect, invoke exposed ops, permitted runtime inputs, specialists, change request | Edit implementation, install, elevate, retarget accounts |

Discovery: host-published operation descriptors ∩ grants ∩ health. Installing an extension does not rewrite copilot core instructions and does not widen existing sessions.

Skills to adapt (not blindly install): discover capabilities; author a composition; investigate an app result; hand off improvement; author domain components; design a data recipe; create/evaluate a skill; package an app; plan a deployment. Skill text cannot self-grant.

## Hermes transfer (what to copy vs refuse)

Copy: schema vs handler split; config vs plugin state; additive compatibility; doctor/validate on enable.  
Refuse: full-trust portable plugins as QMX policy; missing-dep warning-and-continue; undeclared capability use.

## PM terminology

Role **label**: Portfolio Manager. `desk_slug=pm` and `pm-coordination` unchanged until GAP-0083.
