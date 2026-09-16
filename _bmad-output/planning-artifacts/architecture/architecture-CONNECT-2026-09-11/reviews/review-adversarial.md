# Adversarial lens — CONNECT FX paper spine

Verdict: two conformant-but-incompatible pairs found; both closable by tightening AD-1 and AD-3. No parent override.

Pairs:

1. CRITICAL — Live kind inference. Unit A stores `VenueClientKind.CTRADER` on the roster binding. Unit B infers CTRADER from any VenueId that does not start with `conformance:`. Both obey AD-1 as written ("roster names the cTrader protocol family"). A crypto or typo id still reaches LiveCTraderClient in B. Close: live kind is an explicit roster field of type VenueClientKind; absence is unsupported capability; the only string convention remains `conformance:`.

2. HIGH — Encode home. Unit A puts ProtoOA NewOrder builders in `qmf.venue.connection`. Unit B puts them in `qmn.venue.live` and still imports qmf-venue only from qmn.venue, so DEC-0241 holds. AD-3 says "complete ConnectionManager" but does not forbid a second encoder in live.py. Close: the encode functions are qmf-venue symbols; live.py translates Command to those symbols and must not compile proto messages itself.

3. HIGH — Read-back journal. Closed by AD-4 (`data quality`). If A3 is overturned, both units still cannot mint an eighth type. Residual: none if AD-4 stays.

4. MEDIUM — Partial encode. Unit A encodes all five CT-19 kinds. Unit B encodes only place_order and leaves cancel/close as sensing-only "until later stories". AD-2 already requires every kind the CT-18 declaration supports. Restate in AD-3: a kind declared in the bound CT-18 and left as sensing-only refuse is a connect bug.

5. MEDIUM — Paper without reconcile. Unit A implements submit encode but leaves reconcile() on FTR-01. AD-2 requires both encode and read-back. Already closed.

6. LOW — SessionTopology count 2 vs demo-only soak. Inherit DEC-0244; restate under AD-2.

No pair found that honors every AD and still builds a third gateway library, a local matcher, or a Bot twin.

Apply: (1) and (2) and the AD-3 sensing-only restatement; (6) as a sentence on AD-2.
