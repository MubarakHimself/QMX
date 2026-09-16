# Stage 9 mini-review — CONNECT FX paper (2026-09-11)

Role: consistency reviewer (ledger + docs + contracts; no raw sources).

Scope: DEC-0263..DEC-0268, GAP-0059/GAP-0060, FEAT-0032, ADR-0021, blast radius COMP-QMN / COMP-QMF-VENUE / COMP-CTRADER.

## Findings

1. CT-20 previously mapped position/balance read-back to a journal type named observation. That contradicted CT-13's seven types and DEC-0266. **Fixed** at desk: mapping rows now name CT-13 `data quality`; DEC-0247 is interpreted, not superseded.
2. No two live docs now disagree on FTR-01 mapping, fail-closed `VenueClientKind`, or encode locus (`qmf-venue` symbols; `qmn.venue.live` translates).
3. Dead list honored: CCXT, Hummingbot, Spotware SDK, Twisted, local matcher, Bot/Book twins, sensing-only-as-paper, unknown-live-defaults-CTRADER.
4. No new component, contract id, or dependency edge. Preflight reuse recorded in ADR-0021.
5. GAP-0059 and GAP-0060 remain deferred non-blocking. No blocking gap opened.

Blocking findings: none remaining after the CT-20 mapping fix.
