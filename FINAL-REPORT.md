# QMX QA Fix Round 1 — Final Report

**For the operator. Plain words.** All 35 fix cards from the 2026-08-27 QA phase
are done and proven. Every fix was locked in by a test that failed before the fix
and passed after it, without that test being weakened. The full evidence trail is
in `FIX-LEDGER.md` (one row per card, with the commit and the proving tests).

## What was fixed, card by card

| Card | What was wrong | What changed | Proof | Commit |
|---|---|---|---|---|
| FC-01 | A safety rule ("never block a risk-reducing exit") existed in code but nothing ever called it | Every path that can withhold an act now runs through the guard; risk-reducing acts survive every control | Epic-10 exit-preservation tests | `0ae38ec` |
| FC-02 | A nested config could smuggle a forbidden replay-clock setting past the guard | The guard now sees the outer settings before any merge | T23-PIN-03 | `f1bfb4b` |
| FC-03 | Downloaded price data threw away its exact bid/ask money values | The exact values are persisted with the stored observation | Epic-18 money pins | `06ef7a2` |
| FC-04 | If a batch of runs partly failed, the killed runs vanished with no record | Every reaped run gets exactly one ledger line | Partial-spawn disk pins | `86945bd` |
| FC-05 | An unauthorized "register a bot" backdoor shipped in the bot-authoring library | Removed entirely (operator ruling OR-06); the mint will be built later at the proper place | Wiring-absence pin | `bd7d4b3` |
| FC-06 | Sealed (no-peek) data could be read by lying about your position | The seal now checks the data's own timestamps, not just the caller's claim, on every read path | Five-path seal quantifier | `57ec359` |
| FC-07 | A network failure could crash through the data boundary instead of being reported | All three transport seams return a typed refusal instead of raising | 15 transport-raise tests | `8bee56d` |
| FC-08 | An oversized number could crash a statistics boundary | Size is checked before conversion; a typed refusal instead of a crash | T22-PIN-01, three arms | `ad224b0` |
| FC-09 | A euro target could be compared against a dollar result as bare numbers | Cross-currency/unit comparisons are refused | T21-309 | `88e3add` |
| FC-10 | Synthetic data silently mis-scaled prices 100x when source and target scales differed | Exact conversion with the factor recorded, or a refusal — never a silent rescale | T23-PIN-02 (tightened first) | `7cee389` |
| FC-11 | The results artifact was missing its declared chart data | Charts (incl. monthly grids and distributions) and trade references ship inside the artifact | Machine-readable-series test | `1653639` |
| FC-12 | Commission was never charged on any real run (the cost step was wired to nothing) | The run loop's handler now runs fill → slippage → cost | Cost-recorder test | `b214b97` |
| FC-13 | The two product doors (CLI and Python) could drift apart behind a hand-maintained list; one capability was already missing | Parity is now computed from the doors themselves; the missing capability published | T-16.5 pins | `4501e16` |
| FC-14 | A download read the real wall clock deep inside the library (non-reproducible windows) | The clock is injected at the top; the library never reads time itself | Clock pins + clean ambient scan | `c44b4cc` |
| FC-15 | Data fingerprinting was hand-copied in two places (silent fork risk on upgrade) | One implementation in the core library; a widened detector guards it | E1-I03 detector | `e7cd22c` |
| FC-16 | One public venue function crashed on bad input instead of refusing | Typed refusal; the whole public surface is now swept programmatically | 63-function boundary sweep | `75f9df6` |
| FC-17 | Impure process-spawning code shipped inside the pure bot library | Moved to the backtesting host package; the pure wheel verified clean | Wheel inspection tests | `2fd9377` |
| FC-18 | The data catalog answered from its own notes instead of the stored data | Coverage, sides and counts derive from the persisted observations (+ example aligned) | Requirements-first pins | `699652a`, `d161642` |
| FC-19 | Secret references accepted account data embedded in them | Only opaque minted references are accepted; nothing rejected is echoed back | Opacity pins | `36473da` |
| FC-20 | Two packages had no failure register; one register was incomplete | All three registers complete, six required fields per entry, gates parse them | Six-field register gates | `410f2ec` |
| FC-21 | The venue package shipped no reference examples | Two executable examples on the sibling convention, with a runner test | Epic-8 examples gate | `47c1c56` |
| FC-22 | Identity artifacts carried no contract version stamp | Version-stamped identity for all five artifacts | E1-C11 incl. CT-03 | `e50187d` |
| FC-23 | A backup error path crashed on a reserved key instead of returning the error | The adapter's context is namespaced before remapping; refusals return | Both adapter-remap reds | `7476c5b` |
| FC-24 | The footprint mapping path silently dropped unknown fields | Unknown top-level fields are refused, same as the strict path | Unknown-field pin | `09e1fd6` |
| FC-25 | The execution composition's version number never changed when the composition changed | The version derives from the actual bound ports and their order | Bound-set version test | `85373a3` |
| FC-26 | "grade" and underscore-spelled composite scores slipped past the no-composite guard | Separator-normalised matching plus the missing tokens | Composite guard pin | `e9e4a26` |
| FC-27 | An unknown veto door or reason was silently counted under a new name | Unknown doors and reasons are refused, vocabulary closed | Unrostered-door/reason pins | `1c11982` |
| FC-28 | numpy was used but not declared as a dependency; the scanner couldn't see it | Declared and pinned; the scanner now sees dynamic and non-first-party imports | Declared-imports test | `93c31f7` |
| FC-29 | Download progress never showed an ETA | A deterministic, clock-free ETA on every sample | Monotonic-ETA test | `afd8131` |
| FC-30 | The per-run randomness seed was thrown away at the slippage boundary | The seed reaches the model interface (future stochastic models reproducible by construction) | Seed-plumbing test | `90cb43a` |
| FC-31 | Six confirmed-dead symbols | Deleted (or unused required-parameter bindings renamed away); dead-code scan now finds zero | Vulture zero at min-80 | `0430549` |
| FC-32 | Four money/time boundaries were unpinned by tests; the replay clock crashed on exhaustion | All four pinned; the clock (and the shared clock contract) returns a typed refusal, never raises | Mutation pins + refusal tests | `8ed4d2b`, `3fcfcc8` |
| FC-33 | The factory's merge gate never ran the four safety scanners | The gate runs the full check sequence and is pinned against regressing | Config-pin test | `2e3bb63` |
| FC-34 | Quality gates were set to "anything goes" sentinels; the QA battery was one-off | Ratchets locked at today's numbers; a permanent CI battery (check + vulture + nightly mutation testing) | Gate values + battery workflow | `cd31883` |
| FC-35 | QA lanes ran without their authority documents present | The authority tree ships in the worktree; a gate fails any lane whose brief names a missing authority | Lane-entry gate + kill-probe | `40dbd1b` |

## Gates at the finish line

- **`uv run poe check` — fully GREEN**, all ten steps: format (608 files),
  lint, pyright (0 errors), the full test suite (**3,932 passed, 14 skipped,
  86.86% coverage**, per-package and contract-module floors held including the
  100% branch floor on the money/time contract modules), the tools suite
  (340 passed, 98.42% coverage), and all four tier-1 scanners clean
  (money-path, ambient-clock, mock-data, secret).
- **`uv run poe qa-verify` — GREEN across all 23 epic suites** (plus the new
  lane-entry authority gates, which run first), with exactly one red: the
  by-design QMX-F107 item listed below. Two long-standing epic-2
  permanently-red probes were deleted on the backlog's own instruction
  (superseded by FC-05), and the epic-15 spawner scan now recognises
  `qmb.host` as the ratified composition-root home FC-17 moved the sandbox
  runner into.
- Merge and CI: `fix/qa-round-1` fast-forwarded into `integration` and pushed.
  **Both workflows are GREEN on the final push (`e874256`)**: Skylos passes at
  the new ratcheted gate numbers, and the new QA Battery's first real runs
  passed end-to-end on the Linux runner (full check sequence + the vulture
  dead-code gate). Closing that loop surfaced and fixed four last items: the
  battery's pyright job is pinned to the ratified tier-1 platform (Windows);
  the `qa/` verification corpus itself is held outside the Skylos scan scope
  (the ruled gate numbers were computed over the shipped tree, which it sits
  outside); the new vulture gate's baseline read is containment-checked; and —
  good news — the committed dead-code baseline ratcheted from 4 straight to
  **zero**, because FC-31 cleared every corroborated finding. The nightly
  mutation job gets its first live validation on tonight's cron.

## Deliberately-unproven list (by design, not failures)

- **QMX-F107** (`test_t18_1a_no_qmb_authored_second_data_layer_FINDING`, Epic 18):
  the download path keeps a small dedup ledger file of its own. Recorded as a
  finding, ruled out of this backlog (low severity, UNPROVEN). This is the only
  deliberately-red QA test.
- **Stochastic slippage draw** (part of FC-30): the seed plumbing is proven; the
  "same seed reproduces the same random draw" half stays UNPROVEN because no
  stochastic model exists yet — proving it would have meant faking one.
- **Three rounding mutants** (FC-32): mathematically equivalent mutants
  (unreachable branch), recorded so the nightly mutation job never reopens them.

## Notes the operator should know

- The factory merge-gate edit (FC-33) had exactly one line of room: the gate's
  `test` slot now runs the full `poe check` instead of the factory's own
  `adws/tests`. That is what the config's own instructions call for, and it is a
  net strengthening — but it is a replace, not an add. Say the word if you want
  it revisited.
- The Skylos dead-code ratchet stays at 80 for now; the card's follow-up ratchet
  to ~74 should be set after the first CI run reports the actual post-cleanup
  count (Skylos cannot run on this Windows machine).
- The nightly mutation job and the Ubuntu-side battery jobs get their first real
  validation on the CI runner; everything checkable locally was checked locally.

## Where to click

Compare and squash-merge when you are ready:
https://github.com/MubarakHimself/QMX/compare/main...integration

main moves only by your squash-merge click.
