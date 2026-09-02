"""One-off: apply the five cross-file carries the round-1 fix seats left out of scope."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
L = '_docwork/qma/'


def patch(p, pairs, must=True):
    path = Path(p)
    s = path.read_text(encoding='utf-8')
    o = s
    for a, b in pairs:
        if a not in s:
            print('  MISSING in', p, ':', a[:70])
            if must:
                raise SystemExit(1)
            continue
        s = s.replace(a, b)
    if s != o:
        path.write_text(s, encoding='utf-8', newline='\n')
        print('patched', p)


# 1. ct-48 wildcard registry refs -> the two concrete rows
patch(L + 'staged/docs/contracts/ct-48-qma-mailbox-envelope.yaml', [
    ('registry:mailbox.delivery_trim_*', 'registry:mailbox.delivery_trim_event_count / registry:mailbox.delivery_trim_disk_bytes'),
])

# 2. SCN-0013 wildcard hook timeouts -> the three concrete rows
patch(L + 'staged/docs/scenarios/SCN-0013-quant-over-the-wire.md', [
    ('registry:hook.timeout_*', 'registry:hook.timeout_before / registry:hook.timeout_after / registry:hook.timeout_control'),
])

# 3. ct-43: proposer is a whitelisted suffix-less cross-reference
patch(L + 'staged/docs/contracts/ct-43-qma-memory-provider.yaml', [
    ('    - "candidate.proposer: the proposing Agent\'s ref; mandatory (DEC-0317)"',
     '    - "candidate.proposer: the proposing Agent\'s ref; mandatory (DEC-0317). `proposer` is one of the ten suffix-less cross-reference exceptions the spine\'s Consistency Conventions whitelist for the `_ref` law (AD-18), so the field keeps this name and never becomes `proposer_ref`"'),
])

# 4. SCN-0014 frontmatter gains DEC-0375 (cited in the body as dead)
patch(L + 'staged/docs/scenarios/SCN-0014-money-path-barrier.md', [
    ('decisions: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0320, DEC-0324, DEC-0301, DEC-0347, DEC-0306]',
     'decisions: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0320, DEC-0324, DEC-0301, DEC-0347, DEC-0306, DEC-0375]'),
    ('sources: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0324, DEC-0347, _bmad-output',
     'sources: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0324, DEC-0347, DEC-0375, _bmad-output'),
])

# 5. ledger-L3 DEC-0325: model_family has no AD-26 scope of its own
patch(L + 'harvest/ledger-L3.yaml', [
    ('`model_family` per-Deployment assignment | Deployment-scoped |',
     '`model_family` per-Deployment assignment | scope declared-per-subsystem (AD-26 pins no scope for it; `deployment` is not a member of the closed scope vocabulary) |'),
])

# 6. veto-register: the three job-spec-named variables the sitting declined
p = Path(L + 'harvest/veto-register.md')
s = p.read_text(encoding='utf-8')
if 'Class 4' not in s:
    s = s.rstrip('\n') + '''

## Class 4 — job-spec-named variables the sitting declined (surfaced, not minted)

| Source | What the operator's job spec names | Why the registry carries no row | The one-line veto |
|---|---|---|---|
| SRC-15 (the AD-26 variable list) | `sticky limit` and `budget hint` | Removed from AD-26 by the sitting as unowned — no owning AD, subsystem, units or default (memlog "AD-26 VARIABLE LIST CORRECTED"); their roles are carried by `continuation.max_consecutive`, `continuation.budget` and `rlm.depth_cap`. Lands in DEC-0325; changelog row V12. | "Register a sticky limit / budget hint anyway — owning subsystem X, units Y, default Z." |
| SRC-15 (the AD-26 variable list) | `journal retention` windows | The event journal is evidence — retained, backed up and never trimmed (AD-8, AD-23) — so it mints no retention or trim threshold; only the two bounded non-evidence streams (telemetry, mailbox delivery projection) carry retention/trim rows. Lands in DEC-0325; changelog row V12. | "Register a journal retention window anyway — the journal may be trimmed after N." |
'''
    p.write_text(s, encoding='utf-8', newline='\n')
    print('patched', p)
print('carries applied')
