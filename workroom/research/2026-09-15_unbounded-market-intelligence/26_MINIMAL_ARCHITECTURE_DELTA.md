# 26 — Minimal architecture delta

Do **not** add a market-physics subsystem.

What already exists and should be reused:

- Snapshot + closed consumers
- Shadow seam + `shadow_composition_fp`
- Offline train/eval/register refuse-paths
- QMB three lanes + robustness/sweep
- SQS and CT-31 left alone

**Smallest change if experiments E1–E3 are wanted:**

1. Keep `regime_classifier_v1` **unbound**.
2. Register experiment labelers as **shadow candidates only**.
3. Add **one optional snapshot field later**, after a sitting: either a class from a frozen artifact **or** a `cp_prob`/`cusum_stop` bit — not both in V1.
4. Book door gains a **policy** (skip / refuse) that reads that field. Policy is not MIS.
5. No bot consumption. No sizing term. No playbook switch.

Anything larger (new contracts CT-MIS-*, qmf-mis library, physics multipliers, ensemble voter) is **not** minimal and is not implied by this research.
