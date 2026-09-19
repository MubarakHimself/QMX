# Operating line (this session)

This file exists so later agents do not re-learn the corrections by wandering.

## Original job

Unbounded market-intelligence / regime / placement research from the attached prompt, plus operator freedom: no instrument ceiling, no timeframe ceiling, no article-count ceiling. Use the local MQL5 article library. Produce the prompt's deliverables under this folder.

## Corrections that override the prompt's recovery geography

1. **Do not fixate on market physics.** Physics is one family. The live centre is **regime, regime change / changeover, market state, placement, filters, and related terms**. Expand, do not narrow.
2. **Stay inside this QMX folder.** Workspace is `C:\Users\Mubarak\Desktop\QMX`. The article corpus is `.worktrees/mql5-library/`. Do not inventory, copy from, or follow leads on the rest of the Desktop or other sibling projects.
3. **Do not hit mql5.com.** On-disk markdown is the evidence.
4. **Read-only on git.** Write only under this OUTPUT_ROOT. No production code. No live trading.

## Current-QMX truth (code/docs in this repo and `integration`)

- MIS is a node labeler layer. Signal snapshot goes to **Book door + KSA only**. Bots never consume it.
- SQS is **Spread Quality Sensor**, block-only, not snapshot-quality, not a regime model.
- V1 governed producers: identity, spread-state, gap-event, feed-state, SQS, degraded-sensors, fitted `liquidity_stress_v1`.
- `regime_classifier_v1` is the design story (GAP-0051). Integration already has design/corpus/labels/train/eval/register/shadow seams. Chosen family on integration is `lightgbm-multiclass`. Classes: quiet|normal|elevated|stressed. Recovered Kronos/HMM/BOCPD/MS-GARCH stay unauthoritative.
- A classification score is not a trading edge. MIS does not size, does not switch playbooks, does not own entries.

## Prior MQL5 passes to go beyond, not repeat

`workroom/research/2026-09-09_mql5-mis-regime-notes.md` fully read 12 articles.
`workroom/research/2026-09-09_mql5-mis-scalp-notes.md` fully read 12 articles.
Those 24 are leads. This run must inspect far more of the 3057 fetched articles.
