# TODO: contract verification (blocked 2026-08-18 by API overload — run first thing next session)

One REPORT-ONLY agent (Opus). It must not edit anything except writing its report file.

Task: verify that the revised `kernel-contract-draft.md` (~130KB, "Revision note" near top, laws K15–K19, OPEN-25–28) actually covers all 20 must-fix findings from its adversarial critic.

Steps for the agent:
1. Read the critic's findings: in `C:/Users/Mubarak/.claude/projects/C--Users-Mubarak-Desktop-QMX-agentic-system-planning/4846cf54-4514-4698-a84c-8d3cd2de22b0/subagents/workflows/wf_7aad5cd3-20f/journal.jsonl`, find the `{"type":"result"...}` line for agentId `a08b99a1a8431c00d` — its result object holds `mustFix` (20 items, issue+where) and `niceToHave` (20 items). (If that session directory is gone, the critic's full output is also quoted in the exported session transcript.)
2. Read the revised `kernel-contract-draft.md` in full, plus `research/qma-extensibility-dossier.md` where an item names it.
3. Per mustFix item: ADDRESSED / PARTIAL / MISSED with located evidence.
4. Check for SILENT DECISIONS: one-way doors decided in prose instead of registered as OPEN items in Part C — list any.
5. One line per niceToHave: handled / unhandled / declined.
6. Write the report to `research/raw/contract-verification.md` with a summary header: counts, silent-decision list, and a "leftovers before ratification" section.

Rules: read/write only inside `agentic-system-planning/` (plus the one journal file); the only file written is the report; vocabulary "mind", never "bot".

After the report: settle its leftovers, then proceed to Step 3 ratification (agenda in map.md Status section).
