# Input reconcile — CONNECT FX paper spine

Load-bearing inputs vs spine. Quiet requirements that the AD structure could drop.

| Input | Landed? | Note |
| --- | --- | --- |
| Handoff: no third venue-gateway library / DEC-0241 | AD-3 | |
| Handoff: unknown live VenueId must refuse | AD-1 | tightened to explicit roster VenueClientKind |
| Handoff: submit sensing-only; honest FX paper quartet | AD-2, AD-3 | |
| Handoff: FX paper first; crypto plurality same port new CT-18 | AD-5 | no exchange pick |
| Handoff: spot FX not skipped; live-capital not an adapter skip | AD-2 | |
| Handoff: risk / crypto Book / sizing / MIS out | Deferred | |
| Handoff: UI / STRATS / loop out | Deferred | |
| Parent AD-26/27/28/35, TN-2/9/11/12/13/21/22 | Inherited table | not re-derived |
| CT-13 seven types / FTR-01 | AD-4 | data quality; DEC-0247 wording collision surfaced |
| Story 24.3 sensing-only / FTR-01 AC | AD-2, AD-3, AD-4 | architecture forbids remaining sensing-only after this increment |
| PRD section 7 forex-only | Inherited + Deferred PRD amendment | no amendment this sitting |
| PRD section 7 node runtime OOS | Conflict surfaced | DEC-0259 supersedes; factory annotates |
| 2026-09-09 packet crypto-first | Not adopted as scope | input only; A1 FX-first |
| L21 first adapter cTrader | Inherited | completion not replacement |
| L22 seam | AD-5 | |

Quiet tone: "honest" paper (no lying with a socket). Landed in AD-2 Prevents.

Nothing dropped that this altitude owns.
