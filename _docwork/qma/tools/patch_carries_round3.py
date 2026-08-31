"""One-off: apply the round-3 cross-file carries (dropped registry key max_in_flight_pinned_kinds; ct-49 refusals row)."""
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')
L = 'C:/Users/Mubarak/Desktop/QMX/_docwork/qma/'


def patch(p, pairs):
    s = io.open(p, encoding='utf-8').read()
    o = s
    for a, b in pairs:
        if a not in s:
            print('  MISSING in', p, ':', a[:80])
            raise SystemExit(1)
        s = s.replace(a, b)
    if s != o:
        io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
        print('patched', p)


patch(L + 'staged/docs/components/qma-daemon.md', [
    ("| Environment concurrency | `registry:environment.max_in_flight` | Per-slot lease ceiling, default 1, `ui-editable`; the `remote_host` and `desktop` kinds are pinned to 1 and uneditable as `registry:environment.max_in_flight_pinned_kinds`. [DEC-0316] |",
     "| Environment concurrency | `registry:environment.max_in_flight` | Per-slot lease ceiling, default 1, `ui-editable`; a per-kind editability property of this one variable — the `remote_host` and `desktop` kinds are pinned to 1 and `uneditable`. [DEC-0316] |"),
])
patch(L + 'staged/docs/contracts/ct-46-qma-execution-environment-job.yaml', [
    ('    - "execution_environment.max_in_flight: registry:environment.max_in_flight (default 1), ui-editable per declaration; the remote_host and desktop kinds are pinned to 1 and uneditable as registry:environment.max_in_flight_pinned_kinds (DEC-0316, DEC-0325)"',
     '    - "execution_environment.max_in_flight: registry:environment.max_in_flight (default 1), ui-editable per declaration; editability is a per-kind property of this one variable — the remote_host and desktop kinds are pinned to 1 and uneditable (AD-26 names one variable, max_in_flight) (DEC-0316, DEC-0325)"'),
    ('    - "environment.max_in_flight is a dimensionless count (registry:environment.max_in_flight, default 1, ui-editable); the remote_host and desktop kinds are pinned to 1 and uneditable as registry:environment.max_in_flight_pinned_kinds (DEC-0316, DEC-0325)"',
     '    - "environment.max_in_flight is a dimensionless count (registry:environment.max_in_flight, default 1, ui-editable); the remote_host and desktop kinds are pinned to 1 and uneditable as a per-kind property of this one variable (AD-26 names one variable, max_in_flight) (DEC-0316, DEC-0325)"'),
])
patch(L + 'staged/docs/scenarios/SCN-0014-money-path-barrier.md', [
    ("pinned to 1 and `uneditable` for those two kinds as `registry:environment.max_in_flight_pinned_kinds`, a recorded constant expressing that per-kind rule rather than a second spine variable;",
     "pinned to 1 and `uneditable` for those two kinds as a per-kind editability property of that one variable, never a second registry key;"),
])
patch(L + 'staged/docs/contracts/ct-49-qma-routine.yaml', [
    ('    - "missed-fire disposition (closed): recorded — missed fires while the daemon is down are recorded, never replayed; the only other disposition is an explicit operator-gated catch-up command (AD-24), which is not an automatic path (DEC-0328, DEC-0323)"\n  units:',
     '    - "missed-fire disposition (closed): recorded — missed fires while the daemon is down are recorded, never replayed; the only other disposition is an explicit operator-gated catch-up command (AD-24), which is not an automatic path (DEC-0328, DEC-0323)"\n    - "typed refusals on this contract\'s paths, variants of `qmf-core`\'s base (CT-04): `OperatorPrincipalRequired` (a `machine` principal writing a Routine record or requesting a missed-fire catch-up) (DEC-0323, DEC-0328)"\n  units:'),
])
print('round-3 carries applied')
