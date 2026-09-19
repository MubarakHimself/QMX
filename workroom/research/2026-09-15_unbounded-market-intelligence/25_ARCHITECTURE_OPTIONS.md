# 25 — Architecture options (research, not a sitting)

| Option | What changes | Pros | Cons | Verdict this pass |
|---|---|---|---|---|
| **A. Do nothing to architecture** | Only run E1–E3 in QMB ungoverned/shadow | Uses existing seams | GAP-0051 stays unpaid | Default until E1 fails baselines |
| **B. Shadow-only class + Book policy later** | Candidate labeler + door policy after sitting | Minimal (`26_`) | Still need a sitting for governed field | Preferred if E1 or E3 wins |
| **C. Changeover bit instead of class** | `cp_prob` / CUSUM on snapshot | Matches “changeover” language; cheap | Not a state, only a break | Preferred if E2 wins and E1 doesn’t |
| **D. Dual: class + break** | Two fields | Expressive | Two ways to smuggle authority; flicker | Only if both E1 and E2 independently win |
| **E. Restore physics stack** | New sensors + sizing term | None evidenced in-repo | Absent estimators; law clash | **Reject** |
| **F. Bots consume snapshot** | Reopen DEC-0204 | Matches some articles | Explicitly forbidden | **Reject** |
| **G. New qmf-mis library** | Extract MIS from node | None | DEC-0089 killed it | **Reject** |

Option A is allowed. The research may conclude **no architectural change**.
