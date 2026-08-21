# Currency/Reality review — risk increment (AD-29..AD-41 + amendments to AD-27/AD-28)

Reviewer: currency/reality pass. Scope: every externally-checkable (web/protocol-fact) claim the
increment leans on, cross-checked against `research-risk/ctrader-sltp-amend-research.md` and, where
that dossier didn't cover a claim, against live primary sources fetched during this review
(2026-08-20).

## Method

- Re-read AD-27, AD-28 (full text, including the increment's amendments), AD-29..AD-41 in
  `ARCHITECTURE-SPINE.md`.
- Re-read `research-risk/ctrader-sltp-amend-research.md` in full (the companion dossier AD-34/AD-28
  cite by name) and diffed every spine claim against its verdicts.
- Live-fetched `https://help.ctrader.com/open-api/messages/` twice (once for
  `ProtoOAAmendPositionSLTPReq` / `ProtoOAAmendOrderReq` / `ProtoOATrailingSLChangedEvent` and the
  atomicity question, once for `ProtoOANewOrderReq`'s `stopLoss`/`takeProfit`/`relativeStopLoss`/
  `relativeTakeProfit` field text) to spot-check the dossier's transcription rather than trust it
  blind.
- Live-fetched `https://help.ctrader.com/knowledge-base/glossary/trading/` for the "Stop Out"
  definition (AD-41 claim, not covered by the SL/TP dossier).
- Live-fetched `https://github.com/spotware/openapi-proto-messages/releases` for the "integer
  release tag" claim (AD-28, pre-existing text carried into this increment's binds list).
- Searched `research-risk/*.md` and `.memlog.md` for any other citation trail behind claims not in
  the SL/TP dossier.

## Claim-by-claim verdicts

| # | Claim | Where | Verdict |
|---|---|---|---|
| 1 | `ProtoOAAmendPositionSLTPReq` — one message, absolute `stopLoss`/`takeProfit`, `guaranteedStopLoss`, `trailingStopLoss`, `stopLossTriggerMethod`, no dedicated response | AD-34 ¶2, AD-28 protection-capability bullet | Matches dossier §1 verbatim; matches live `help.ctrader.com/open-api/messages/` field text fetched this review. CONFIRMED. |
| 2 | `ProtoOAAmendOrderReq` — one message, both absolute and entry-relative forms, amends a pending order without cancel-replace | AD-34 ¶2 | Matches dossier §2; matches live fetch. CONFIRMED. |
| 3 | Absolute `stopLoss`/`takeProfit` "not supported for MARKET orders" on `ProtoOANewOrderReq`; `relativeStopLoss`/`relativeTakeProfit` as the alternative, formula `entryPrice ∓ relative...` | AD-28 protection-capability bullet, AD-34 ¶2 | Matches dossier §5; live fetch returned the exact field text ("Not supported for MARKET orders." / "Unsupported for MARKET orders.") and the exact relative formula. CONFIRMED. |
| 4 | Amend atomicity is UNDOCUMENTED in every primary source (no page/proto comment states partial-failure or transactional behavior) | AD-34 ¶3, AD-28 protection-capability bullet + verification-suite clause | Matches dossier §3 (its own explicit "no page fetched... contains any statement" finding). This review's own fresh fetch of the messages page, prompted specifically to hunt for an atomicity statement, also returned nothing. CONFIRMED (confirmed-absence, correctly scoped as UNDOCUMENTED rather than "proven non-atomic"). |
| 5 | Server-managed trailing stop exists; `ProtoOATrailingSLChangedEvent` is the push-event surface; step/distance algorithm UNDOCUMENTED | AD-34 ¶4, AD-28 protection-capability bullet | Matches dossier §4; live fetch confirmed the event's description text verbatim. CONFIRMED. |
| 6 | Guaranteed-stop class gated by account type | AD-28 protection-capability bullet | Matches dossier §1 (`guaranteedStopLoss`, "Available for the French Risk or the Guaranteed Stop Loss Accounts"). CONFIRMED, and the spine states it more conservatively ("where the account type offers one") than the dossier's specific carve-out — no overreach. |
| 7 | Spotware proto pinned by an integer release tag (AD-6 register: "latest observed 91, verified 2026-08-20") | AD-28 protocol-pinning bullet; inherited-invariants table row | Not part of this risk increment's new content (pre-existing from the venue sitting), spot-checked anyway: `github.com/spotware/openapi-proto-messages/releases` shows integer tags (91, 90, 89, 88, 86_3...). CONFIRMED, and the table's "91" figure matches what this review's live fetch just returned — genuinely re-verified, not stale. |
| 8 | "The venue's own 'stop out' means margin-call liquidation" (motivates the `venue_liquidation` / `qualifying_loss_exit` vocabulary split) | AD-41 vocabulary-split bullet; AD-33 close-reason enum (`venue_liquidation`); conventions table | **Leaned on but not researched at ratification time.** No file under `research-risk/` or the earlier `ctrader-*-research.md` dossiers cites a primary source for this. Its only paper trail is `research-risk/brief-formulas-stopout.md:530-532`, which states it under the heading **"One hazard no dossier names"** — i.e. the synthesis brief itself flags that this was asserted from general trading-domain knowledge, not sourced. This review fetched `help.ctrader.com/knowledge-base/glossary/trading/` directly: cTrader's own glossary defines "Stop Out" as "a broker-defined margin level... at which cTrader automatically starts closing open positions to prevent further losses" — so the claim **checks out as true**, but it was ASSERTED, not verified, when the spine adopted it. Flagging per the review's mandate regardless of outcome. |

## Cross-check against the dossier for overreach

Every AD-34 and AD-28 sentence that cites cTrader/Spotware facts stays at or below the dossier's own
confidence labels — nowhere does the spine upgrade an UNDOCUMENTED dossier finding to a stated fact,
and nowhere does it add a protocol claim the dossier didn't make. Specifically:
- Atomicity: dossier says UNDOCUMENTED → spine says UNDOCUMENTED + verify-or-refuse. No upgrade.
- Trailing algorithm: dossier says UNDOCUMENTED (mechanics) → spine says "UNDOCUMENTED and may never
  be assumed." No upgrade.
- Rate-limit bucket assignment (dossier §6, marked "inferred / SECONDARY-ONLY, not explicitly named
  in the docs reached") is **not asserted anywhere in the AD-29..41 text** — the spine simply doesn't
  repeat that weaker inference, which is the correct conservative choice.

One minor (non-blocking) prose observation: AD-34 ¶2 compresses two distinct primary facts into one
sentence — the "not supported for MARKET orders" restriction is a field comment on both
`ProtoOANewOrderReq` (placement) and `ProtoOAAmendOrderReq` (amend), but the sentence's "declared
placement path" phrasing reads as if it's still describing the amend message. Each underlying fact is
independently CONFIRMED-PRIMARY per the dossier and this review's live fetch; this is a legibility nit
in the spine's prose, not a sourcing gap.

## Verdict

The increment's cTrader/Spotware protocol claims (AD-34's five-command mint and AD-28's
protection-capability roster) are accurately transcribed from CONFIRMED-PRIMARY dossier findings with
no overreach beyond what the dossier verified, and this review's independent live re-fetch of
`help.ctrader.com/open-api/messages/` and the Spotware proto repo reproduced the same field text,
event definitions, and absence of an atomicity statement; the one gap is AD-41's "venue 'stop out'
means margin-call liquidation" claim, which drove real naming decisions (`venue_liquidation` vs
`qualifying_loss_exit`) but was asserted from general knowledge rather than sourced — it independently
checks out true against cTrader's own glossary (fetched this review), but should get a citation into
`research-risk/` (or a one-line addendum to an existing dossier) so it isn't the one un-sourced fact in
an otherwise fully-cited increment.

**Stale/unverified/overreaching claims:**
- AD-41 (and AD-33's `venue_liquidation` enum member, and the conventions-table naming-split row):
  "the venue's own 'stop out' means margin-call liquidation" — asserted in
  `research-risk/brief-formulas-stopout.md` under its own heading "One hazard no dossier names," no
  primary-source citation anywhere in the corpus; verified true against `help.ctrader.com/knowledge-
  base/glossary/trading/` during this review, but was unverified at the time the spine adopted it.

File: `C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/review-currency-risk.md`
