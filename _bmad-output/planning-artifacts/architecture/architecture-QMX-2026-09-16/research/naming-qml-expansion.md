# Naming — QML expansion (not a second language)

Date: 2026-09-16  
Status: proposal — one recommended set  
Scope: product nouns only. QMF = framework; QML / QMB / QMA = libraries. No new COMP.

## Banned

STRATS (as QMX product language), second language, COMP-LIB, Knowledge Base, “primitives” as a brand.

## Recommended set

| Slot | Name | Notes |
|---|---|---|
| Mill inside QML (module/surface) | **research** | Stage 0 of QML authoring. Filters noise → structured **hypotheses**. Lives under QML (`qml.research` / research surface), not a sixth library. Pair with Stage 1 **declaration** (existing CT-33/34 + Python + QL-8). |
| One DNA A–I package | **hypothesis** | One package = one **hypothesis** (also a **research candidate** / **research artifact** until graduated). Incomplete / hole-bearing packages stay hypotheses — never invent exits to “complete” them. |
| Dictionary entries | **dictionary entry** | Plain term, not a brand. Role-neutral vocabulary cited into a hypothesis. Not a registry kind, not CT-16. |
| `Stats/` folder | **seed corpus** | Import tree only. Canonical files outside QMX git; QMA may snapshot; QML may cite into origin. Not product language. |

## Lifecycle (existing nouns)

`seed corpus` → cite → **hypothesis** (ungoverned research candidate) → **graduation** (L33 / QL-8: lineage to originating **research artifact**) → **declaration** + logic → QMB lanes → human promote.

## Rejected for product use

| Avoid | Why |
|---|---|
| STRATS / strategy DNA / STRAT-ids as product nouns | Staging mill language; seed-corpus ids may remain on disk only |
| Primitive (brand) | Corpus field jargon; say **dictionary entry** |
| Knowledge Base / COMP-LIB | Graveyard / Workbench AD-1 |
| Second language / revived `.qml` DSL | DEC-0172; Stage 0 is QML research, not a dialect |

## One line

**QML research** mills **hypotheses** from **dictionary entries** in the **seed corpus**; graduation yields a **declaration**.
