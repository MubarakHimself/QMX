# QMX — performance-first agent workspace

Status: PAUSED pending platform-wide agentic-system study, 2026-09-14. The user subsequently requested grounding in current QMX documentation, emphasizing department-level interaction and the breadth of agents across the platform. Do not execute this layout brief as the next design pass. User preferences below remain captured; the specific arrangement is an unapproved historical proposal.

## Current user direction

- During agent work, code should rarely be the default view. Start with a meaningful representation of the bot and its performance; make changes/diff available on demand.
- The FC/FIFA-card analogy means bot identity, attributes and measured performance. It does not prescribe a sports-card visual style or a synthetic overall score.
- The Codex/Hermes/Manus pattern of substantial conversation plus an independent right work surface is useful. The new Codex screenshot specifically shows Review, Terminal, Browser and Files entry points.
- Preserve the useful lower comparison area, developing it into what-if scenarios.
- The present left-side arrangement needs reconsideration. User authorization to lead remains active, with economical usage and focused editing preferred.
- The supplied Stitch screenshot demonstrates an element menu with Edit text, Edit with AI and Delete. Its existence is observed; execution through automation has not been tested.

## Proposed arrangement

```text
Compact global entry · Open environment tabs
┌──────────────────┬────────────────────────┬────────────────────────────────────┐
│ Local navigation │ Agent conversation     │ Independent work surface           │
│                  │                        │ Performance | Changes | + tools    │
│ Current work     │ Brief / discussion     │                                    │
│ Sessions         │ Decisions / run updates│ Bot identity + version + state     │
│ Runs             │ Links to evidence      │ Evidence / equity / drawdown       │
│                  │                        ├────────────────────────────────────┤
│ Collapsible      │                        │ What-if scenarios                  │
│                  │ Composer               │ Baseline vs selected alternatives  │
└──────────────────┴────────────────────────┴────────────────────────────────────┘
```

The compact global launcher and open-environment tabs retain different jobs. Local navigation contains work in the active environment; it does not duplicate the entire global menu.

The existing tall chat column is a conversation, not a navigation sidebar. Move it into the central working position. Provide a modest local session navigator that can collapse to a drawer while examining dense results. Initial sizing to test at desktop width: 48px global entry, 200px local navigator, approximately 430px conversation, remainder for the work surface. On a laptop, collapse local navigation before squeezing all tools. These measurements are hypotheses, not tokens or a final responsive contract.

## Right work surface

Performance is the default for the selected bot. Changes is an alternate view of that same bot/version, not an unrelated context. Files, Browser, Terminal and additional tools open within the same host; their exact tab/launcher presentation remains to test. Selecting a tool replaces or deliberately splits the working surface rather than automatically adding another narrow permanent column.

The performance view combines a compact identity block and useful evidence:

- Bot name, selected version, strategy family and market coverage.
- Explicit operating/evaluation state, without conflating bot definition, experiment result and deployed instance.
- Return, drawdown, risk-adjusted return and trading activity appropriate to the selected evidence.
- Visible sample period, cost assumptions and whether evidence is in-sample, out-of-sample, paper or live.
- One generous chart with switches for equity, drawdown and cost sensitivity; avoid keeping a squeezed chart beside an always-visible editor.

No artificial overall rating. Metrics are evidence under stated conditions, not inherent quality attributes or promises. Missing evidence remains missing.

## Lower what-if surface

Retain the baseline and list alternatives such as changed costs, date windows, sizing or instrument subsets. Show what changed, execution state, differences from baseline and a clear selected scenario. Explicit Run comparison action starts a new calculation when necessary. Distinguish filtering existing results from a full rerun. Pending scenarios have no computed outcomes.

Selecting a scenario updates the upper evidence view. Its baseline/version/dataset stay explicit. A scenario does not silently overwrite the bot. Applying parameter or code changes is a separate action whose semantics need reconciliation with the backend.

## Agents, environments and extensibility

This arrangement targets substantial agent sessions. It is not a mandatory layout for Trading, Portfolio or every Research activity. Other environments may prioritize their own tools and summon the agent surface when useful.

The bot, its run/result and the conversation need persistent references so different environments can open the same work without duplicating it. Agents and bots are distinct identities. A specialist session may open as another work-surface tab; no mandatory permanent third chat column.

Additional tools need a place to open, a visible work context and a way to return to the originating task. This is a user-facing expectation, not a new plugin API or a claim about implemented backend capabilities. Persistence, access, concurrent changes and run lifecycle remain questions for Grok.

## Economical next edit

Work on one copy of the refined Stitch screen. Structural changes precede element copy edits:

1. Rebalance local navigation, central conversation and right host together. Do not try to fix these structural relationships by rewriting individual labels.
2. Replace the editor-plus-skinny-chart region with Performance as the selected work-surface tab; retain Changes as an accessible alternative.
3. Replace the current code block with the bot identity/evidence composition and enlarge the chart.
4. Adapt the lower table into baseline/scenario comparison with honest pending states.
5. Use element editing for remaining labels, composer copy and card details. Avoid whole-project regeneration and unrelated styling changes.

A useful review checks opening Changes and returning to Performance without losing scenario context; selecting a scenario; collapsing local navigation; maximizing/restoring the right surface. Static artwork cannot establish those behaviors.

No new design generation or production implementation was performed for this correction. DESIGN.md and EXPERIENCE.md remain unfinalized. New screenshots are preserved in imports with agent-workspace-correction-2026-09-14 prefixes.
