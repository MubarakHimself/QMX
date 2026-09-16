# Currency / reality-check lens — CONNECT FX paper spine

Verdict: pass. Pins are brownfield-current; newer protobuf not adopted, with a dated note.

Checked 2026-09-11:

- protobuf: integration pin ==7.36.0 in packages/qmf-venue/pyproject.toml and DEPENDENCIES.md. PyPI/Libraries.io: 7.36.0 on 2026-08-20; 7.36.1 on 2026-08-31. Spine records both and does not bump. Fit: still the qmf-venue-only runtime DEC-0141 named.
- cTrader Open API: help.ctrader.com/open-api/proxies-endpoints still lists demo.ctraderapi.com:5035 and live.ctraderapi.com:5035 for Protobuf; demo and live are separate connections. Getting-started page updated 2026-09-10. Matches TN-11 and Stack.
- CPython 3.14: inherited QMX AD-1; not re-verified as a new pin.
- No new library named (CCXT explicitly forbidden). No starter substitution.

Findings:
1. LOW / defer — 7.36.1 exists; revisit at a qmf-venue release, not this increment (already in Deferred).
2. None of the named tech is training-data-only; versions were checked against the repo and the web.
