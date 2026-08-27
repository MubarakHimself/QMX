# GOAL: Execute the QMX QA fix backlog — 35 cards, one session, unattended

You are the fix engineer for QMX, an algorithmic trading platform that will run live money.
An independent QA phase (2026-08-27) verified all 23 built epics against their ratified
requirements and produced a findings inventory, a fix-card backlog, and a set of operator
rulings. Your job: execute the ENTIRE fix backlog in this one session, self-verified,
ledger-tracked, and leave the repo one operator-click away from a stable release.
The operator is non-technical and will NOT answer questions mid-run. Everything you need is
committed on one git branch. Do not stop to ask; when a genuine ambiguity survives all
references here, record it in the ledger as BLOCKED with your reasoning and move to the
next card.

## 0. Environment and workspace (do this FIRST)

You are launched in `C:\Users\Mubarak\Desktop\QMX` — the operator's main checkout, on
branch `main`, which holds planning only. NEVER commit, switch branches, or leave any
mess in this folder. Your first action is to create your own disposable workspace:

    git fetch origin fix/qa-round-1
    git worktree add C:\Users\Mubarak\Desktop\QMX-worktrees\fix-round-1 fix/qa-round-1

The branch `fix/qa-round-1` already exists (locally and on origin, forked from
`integration` at `2c8d495`) and already contains everything: the QA artifacts under
`qa/`, the machine-battery evidence, and this very brief at `FIX-GOAL.md` in its root.
If `git worktree add` complains the branch is checked out elsewhere: run
`git worktree list`, and remove a stale `qa-audit` or `qa-mutmut` entry with
`git worktree remove --force <path>` — never touch the `QMX` main checkout entry.

From here on, the worktree `C:\Users\Mubarak\Desktop\QMX-worktrees\fix-round-1` is your
project root for the ENTIRE run; every path below is relative to it. `cd` there, run
`uv sync --group dev` (fresh venv), and after ANY restart or context loss: re-read
`FIX-GOAL.md` and `FIX-LEDGER.md` in that worktree first, then resume — trust those files
over your memory.

The repo is a uv workspace (packages/, extensions/, qml/, qmb/, tools/). Windows notes:
you never run Skylos locally (CI verifies it after your final push); the nightly mutmut
job you add in OR-10(b) is a CI YAML change executing on Linux runners, not on this
machine (sanity-running mutmut locally would need WSL and is NOT required).

## 1. Where everything is (paths relative to your worktree)

| Thing | Path |
|---|---|
| Fix cards (your backlog, ranked) | `qa/_trace/fix-cards.md` |
| Findings inventory (132 rows, adjudicated) | `qa/_trace/findings.csv` |
| Corpus verdicts on the 12 rulings | `qa/_trace/rulings-corpus-verdicts.md` |
| Original ruling write-ups | `qa/_trace/operator-rulings-needed.md` |
| Proof map (what must flip) | `qa/_trace/proof_map.md` |
| Per-epic plans / results / reviews | `qa/epics/epic_NN_slug/{PLAN,RESULTS,L6-REVIEW}.md` |
| Independent test suites (the proving tests) | `qa/tests/epic_NN/` |
| Machine-battery evidence (scanners, Skylos, Vulture, mutmut survivors, coverage) | `qa/_trace/battery/` |

## 2. Git discipline (non-negotiable)

- Work on `fix/qa-round-1` in your worktree only. `main` is untouchable — never commit to
  it, never push it. No force-push anywhere. No `--no-verify`. No amending published
  commits.
- Small commits, one card (or one coherent card cluster) per commit, message starts with
  the card id: `FC-07: ...`. No AI attribution lines in commit messages.
- When ALL cards are done and gates are green (step 6): merge `fix/qa-round-1` into
  `integration`, push `integration`, and verify the Skylos CI workflow run on that push
  succeeds (`gh run list --workflow skylos.yml --branch integration`, then wait for it;
  `gh` is installed and authenticated on this machine). `main` moves only by the
  operator's own squash-merge click — never by you.

## 3. Setup steps (in your worktree)

1. Baseline run: `uv run poe check` and `uv run poe test`.
   ambient-scan WILL FAIL at baseline — that is finding QMX-F018, one of your cards.
   Record baseline numbers in the ledger.
2. Add a poe task in `pyproject.toml` `[tool.poe.tasks]`:
   `qa-verify = "pytest qa/tests -q"` — do NOT add `qa/tests` to the default `test` task
   (it must stay a separate gate).
3. Create `FIX-LEDGER.md` at the worktree root (commit it, update it after EVERY card,
   commit the update with the card's commit). Columns: card id | finding ids | status
   (todo / in-progress / PROVEN / blocked) | commit sha | proving test(s) | notes.
   This ledger is your compaction insurance: on any restart, re-read it FIRST and resume
   from the first non-PROVEN row.

## 4. The operator rulings — FINAL, do not re-litigate

All 12 open rulings are settled. Corpus citations are in
`qa/_trace/rulings-corpus-verdicts.md`; the residue was ruled by the operator on
2026-08-27. Apply exactly these:

- **OR-01 — Option A.** A bot-PROPOSED protective-stop tighten through the Book door is
  admissible whenever risk does not increase (ct-23:26). The breakeven-ratchet-only rule
  governs ONLY the automatic dynamic SL/TP path (docs/components/qmf-risk.md:103). The two
  Epic-10 guards must reflect this split; re-point the two tests that encoded the false
  contradiction.
- **OR-02 — trial.** Sweep combos default to `role=trial` (DEC-0165; docs/components/
  qmb.md:79,:95) — change the `run_sweep_batch` default from `confirmation`. Re-point the
  four tests that pinned the old default: `T20-323` (drop/restate its `len(bar)==4`
  count), `T20-314`, `T20-316(f)`, `T20-PIN-01`.
- **OR-03 — typed refusal.** `DataDrivenClock` exhaustion returns a typed refusal
  (unavailable-dependency class), never raises. Fix the boundary bug while there
  (`>` vs `>=` at the cursor check — mutation testing proved it unpinned; see
  `qa/_trace/battery/mutmut/`). Re-point test `E1-U41`: no exact-message pins (unratified
  surface), assert the refusal category. Same ruling class applies to qmf-venue
  `observation_journal_event_type` raising `ValueError` (finding QMX-F020): convert to a
  typed refusal.
- **OR-04 — split.** `logic/` in qml is legitimate (seed-of-intent,
  docs/components/qml.md:112) — no code change, note only. `host/` shipping impure code
  inside the pure wheel is real (AD-15): execute its card as specified in fix-cards.md.
- **OR-05 — Option A.** `invalid input` must NOT cross the CT-14/CT-26 backup/restore
  boundaries: validate arguments BEFORE the boundary so only `storage failure` and
  `policy rejection` cross. Restore the test's forbidden-category set to all five.
- **OR-06 — Option A (REMOVAL, not gating).** `register_bot_definition` and
  `install_bot_definition_kind` are unauthorized wiring of a defined-unwired contract
  (ct-33:9). Remove them from qml's public surface (delete or clearly quarantine as
  non-exported internal scaffolding with a `defined-unwired` comment); update the shipped
  example `qml/examples/conformant_bot_usage.py` so it no longer drives a mint. The CT-33
  document is CURRENT — do not edit it. The mint will be built later at the QMB
  composition root.
- **OR-07 — Option A.** Financing journal events map onto CT-13's existing
  `risk transition` type, following the ratified treasury precedent (ct-13:19). No new
  event type.
- **OR-08 + OR-09 — derived parity, Epic 16 owns it.** Replace the hand-maintained
  `CAPABILITY_LIBRARY` catalog with a reconciler that DERIVES the capability list from
  both door surfaces programmatically; the `data generate` / `has_generator_config`
  Python-door gap (QMX-F016) is fixed as part of the same card.
- **OR-10 — ratchet + permanent battery (operator-ruled).**
  (a) In `pyproject.toml` `[tool.skylos.gate]`: set `max_dead_code = 80` and
  `max_quality = 4084` (replace the 1000000 sentinel; keep the explanatory comments,
  updating them to record the 2026-08-27 ratchet ruling: never worse than today, ratchet
  down as families clear).
  (b) Make the QA battery PERMANENT repo infrastructure: extend the CI so every push to
  `integration` runs — Skylos (already there), Vulture (fail if counts exceed a baseline
  file you create from today's numbers in `qa/_trace/battery/vulture/`), and the four
  tier-1 scanners (`uv run poe check`). Add mutation testing pragmatically: a
  nightly-scheduled (cron) CI job running mutmut on qmf-core exact.py + chrono.py with a
  kill-rate floor at today's 68% (see `qa/_trace/battery/mutmut/`); config lives in the
  repo.
  (c) Factory gate repair (finding QMX-F036): add `uv run poe check` to the quality
  commands in `adws/adw_sssf_config/sssf.config.yaml`. This is the ONLY permitted edit
  under `adws/` — touch nothing else there.
- **OR-11 — keep the seed wired.** `slip_fill` stops discarding `seed` (`del seed` goes);
  thread the per-run seed to the slippage-model interface so a future stochastic model is
  reproducible by construction. The proving test asserts the plumbing reaches the model
  boundary; the stochastic-draw requirement itself stays recorded UNPROVEN (nothing random
  exists yet) — do not fake a stochastic model.
- **OR-12 — stamp deferred.** In `docs/contracts/ct-17-*.yaml` ONLY: mark the sloped-
  evaluation clause (line ~25) and the family snapshot/restore clause (line ~31) as
  deferred with a GAP id, copying the exact deferral pattern CT-16 uses for its numeric
  rungs. This is the ONLY file under `docs/` you may edit in the entire run.

## 5. Executing the cards

Order: the 4 CRITICALs first (QMX-F001..F004), then HIGH by the fix-cards.md ranking, then
the rest. Read each card in `qa/_trace/fix-cards.md` plus its findings.csv rows plus the
relevant L6-REVIEW.md section before touching code. The L6-REVIEW files are the
adjudicated truth; raw per-epic findings.csv rows they overturned are already excluded
from the consolidated inventory.

Per card:
1. Ledger → in-progress.
2. Run the card's proving test(s) — confirm FAILING (if a proving test is marked
   TO-BE-WRITTEN, write it first, requirements-first from epics.md/docs contracts, and
   confirm it fails).
3. Implement the surgical fix. Stay inside the card's scope; no drive-by refactors —
   EXCEPT: when a card opens one of the complexity hot-spot files
   (`qmb/src/qmb/data/download.py`, `qmb/src/qmb/data/catalog.py`,
   `qmb/src/qmb/results/charts.py`, `qmb/src/qmb/config/compiler.py`), you may
   split/simplify the function you are already editing (ruled: quality debt is worked as a
   side effect of cards, never as a campaign).
4. Proving test must now PASS — UNEDITED. The only tests you may modify are the ones the
   rulings in section 4 explicitly re-point, and tests adjudicated wrong-expectation in
   the L6-REVIEW of that epic (fix them to assert the requirement, then they must pass).
   Never weaken an assertion to get green.
5. Local gates for the touched packages: `uv run poe test`, `uv run poe check`,
   `uv run pyright`, `uv run poe lint`, plus `uv run poe qa-verify` scoped to the affected
   epic's qa tests. All green (ambient-scan goes green once its card lands).
6. Commit (card id first), ledger → PROVEN with sha.

Laws that prevent known traps (your fixes must obey the same laws the findings enforce):
no floats on the money path; no ambient clock reads below composition roots; every public
callable returns a value or a typed refusal; no mock/placeholder data in shipped source.
The ~64 UNPROVEN findings and ~23 verification-debt rows in findings.csv are NOT your
scope — the 35 cards only.

## 6. Finish line (all mandatory)

1. Every ledger row PROVEN (or BLOCKED with reasoning — aim for zero).
2. Full suite green: `uv run poe test` (3,899+ tests, coverage floors hold),
   `uv run poe check` fully green (all four scanners), `uv run poe qa-verify` green except
   tests whose findings are ruled UNPROVEN-by-design (list them in the report).
3. Merge `fix/qa-round-1` into `integration`, push `integration`, verify the Skylos CI run
   passes with the new ratcheted gate numbers (see section 2 for how).
4. Write `FINAL-REPORT.md` at the worktree root, plain words for a non-technical
   operator: per-card table (card, what was wrong, what changed, proving test, commit),
   gates summary, the UNPROVEN-by-design list, anything BLOCKED and why, and the compare
   link `https://github.com/MubarakHimself/QMX/compare/main...integration`.
   End with: "main moves only by your squash-merge click."

Work autonomously, use your sub-agents freely for parallelizable cards (disjoint files
only — the ledger is the single coordination point), and keep every promise in this file
literally. Good hunting.
