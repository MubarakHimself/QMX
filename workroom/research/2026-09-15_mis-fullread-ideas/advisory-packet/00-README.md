# Advisory packet — MIS sensing adoption

**Audience:** another agent in a design discussion with the operator.  
**Job of this packet:** say what QMX can **adopt**, how to adopt it **on existing seams**, and what to **refuse**. Not a shopping list of 3,000 articles.

**Provenance:** local MQL5 article library, full-read by section+series packs (workflow `mis-fullread` × 19 + series readers). Physics lane closed by operator. Folder parent: `workroom/research/2026-09-15_mis-fullread-ideas/`.

## Load order

1. This file (index + non-negotiables).
2. `01-LAWS.md` — if a proposal violates a law, stop.
3. `02-ADOPT.md` — the adoption list.
4. `03-HOW-TO-ADOPT.md` — literal mapping onto `integration` MIS/QMB.
5. `04-EXPERIMENTS.md` — only if the discussion is “what to try next.”
6. `05-REJECT.md` — only if someone proposes a rejected object.
7. `06-EVIDENCE.md` — article IDs and code paths when a claim is challenged.

Do not load `NEW_MIS_IDEAS.md` (4k jsonl dump) unless you need a raw line. Do not load the earlier `2026-09-15_unbounded-market-intelligence/` folder as authority; that pass was title/keyword and is superseded for **ideas**. Use it only for **current QMX code facts** (`05_CURRENT_QMX_BASELINE.md`, `07_CURRENT_MIS_CAPABILITY_MAP.md`).

## Non-negotiables (repeat of 01, so they sit in the first file)

- MIS computes a **signal snapshot**. Consumers = **Book door + KSA only**. Bots never.
- SQS = **Spread Quality Sensor** (baseline ÷ live). Not a regime model. Not news.
- `regime_classifier_v1` on `integration` is **design-only** LightGBM (`quiet|normal|elevated|stressed`). Not governed. Keep it unbound until a sitting.
- Adopted article methods enter as **shadow candidates** first. Freeze offline. No live training. No playbook switch. No sizing term.
- A classification score is not an edge. Door/sit-out metrics beat F1.

## What “adopt literally” means here

Copy the **sensing object** (state, change bit, vol coordinate, frozen latent). Do **not** copy the MQL5 Expert Advisor, Wizard Signal, money-management class, or “CNN predicts next bar.”

Integration SHA used for code facts: `8510c032496bb870824ecc5c4f807e8a4e4f167e`.
