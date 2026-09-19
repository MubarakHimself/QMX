# Department layout study 02

**Superseded in part by user review.** A is a promising starting point; B's presentation and C's permanent combination of performance, task graph and coordination are not accepted. Follow [the active agent/Library correction](agent-library-course-correction-2026-09-14.md). The recommendation below is historical, not the next design brief.

2026-09-14 · Working prototype, not an adopted design or production implementation.

Open [department-layout-prototype.html](department-layout-prototype.html) directly in a browser. It is a self-contained file with no downloads, dependencies, external fonts, analytics or network calls. The bottom switcher chooses three structural alternatives. The `variant` query parameter accepts A, B or C; switching updates it. Current work selection remains in memory across switches; refreshing resets everything except the URL-selected variant.

## Question

How does a department become a useful place to coordinate durable work, while an individual investigation can host substantial evidence and agent interaction without forcing every QMX world into one layout?

The prototype follows the user's latest authorization to start concrete ideas using the expanded QMX inventory and MCP Apps research. Existing source: [platform inventory](qma-current-system-ux-inventory-2026-09-14.md), [MCP Apps / modular workspaces](mcp-apps-and-modular-workspaces-2026-09-14.md), and current user directions in the canonical memlog. It does not promote the earlier paused performance-first brief or generated Stitch exports into design authority.

## Three propositions

| Variant | Structure and priority | Tradeoff to inspect |
| --- | --- | --- |
| A / Department room | Department-local navigation, mission list, attention request, persistent members and scheduled work. Open a mission to investigate. | Better overview and accountability; opening work costs one transition. Does this feel like entering the department's world? |
| B / Conversation + tools | Department navigation stays visible; substantial discussion sits beside an independent evidence host and scenario table. | Immediate discussion/evidence comparison; three columns compete on a laptop. |
| C / Evidence workbench | Tools and task graph take the canvas; ownership and events sit beside them. Discussion opens as a temporary side panel. | More room for research; discussion is less continuously visible and the open overlay temporarily covers some evidence. |

Working recommendation: A is a plausible department entry; B and C may be alternative arrangements within an investigation rather than mutually exclusive application shells. This is a new proposition, not a user selection. The prototype does not implement arbitrary pane dragging or user-defined layout persistence.

## Suggested five-minute exploration

1. Start in A. Inspect Hermes or Lyra to distinguish a persistent member from current execution. Open the cost investigation.
2. In B, choose EUR/USD and then SPY. Completed evidence appears for EUR/USD; queued SPY has no invented performance numbers.
3. Open Source, then Performance. Hide the evidence tool and reopen it: the instrument and view selection remain in memory.
4. Switch to C. Inspect tasks 02 and 03 in the concurrent group. Open Discussion and add a local draft. No message leaves the file.
5. Simulate connection loss from the study toolbar. The interface keeps the last confirmed running snapshot and labels current status as unconfirmed. No job is cancelled or restarted.
6. Enter Portfolios. Switch between Crypto systematic and FX diversified. Open linked research to return to the same investigation with the relevant instrument selected.

## Deliberate boundaries

- The small global rail and opened-world tabs persist. The Portfolio world has its own local structure; it is not a clone of the Research screen.
- The Portfolios label is a product exploration. It does not rename QMA's documented Product Manager role or create an approved backend Desk.
- Strategy identity and measured performance are distinct from agent/member identity. No invented aggregate agent score is used.
- The department Handoffs view is an illustrative aggregation of member mailboxes. It does not resolve the backend department-addressing or lead/catch-all question.
- Remote placement, connection state and task state remain different concepts. The diagram and event log are explicitly snapshots.
- Native and MCP App candidate labels identify intended extension seams. All surfaces are plain local HTML; no MCP host, sandbox bridge or protocol conformance is implemented.
- Portfolio target weights are illustrative and sum to 100% within each mandate. They are not live holdings, optimization outputs or execution instructions.
- The example only covers a narrow investigation. RLM kernel inspection, worker migration, memory browsing, approval execution, a general graph editor, autonomous-loop editing and full department coverage remain unexplored.

## Validation and delivery

Embedded JavaScript passes Node's syntax check. The file is self-contained and was queued for opening in the Codex file panel. This pass did not browser-render or exercise the interactions; viewport fit and runtime interaction behavior still need visual review. Earlier browser URL-policy denial of the previous local study was not bypassed to verify this one.

No paid design generations were used. No production code, backend contracts, DESIGN.md or EXPERIENCE.md were changed. Provisional color and typography support legibility only; no visual system is selected. Keep this prototype in `.working` until the user chooses which behavior and layout to carry forward.
