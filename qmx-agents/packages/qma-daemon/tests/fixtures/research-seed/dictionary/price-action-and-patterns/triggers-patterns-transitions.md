# Candidate primitives — triggers, patterns, and transitions

This candidate set is deliberately event-centred. A trigger event records an observable market transition; it is not an order, fill, position, or entry instruction. Pattern objects remain distinct from their completion/break events. None of the cited terminology sources establishes trading edge.

| Family | Entries |
|---|---:|
| Price-level interaction | 10 |
| Liquidity/failure language | 6 |
| Market structure | 6 |
| Momentum, range, and volatility | 6 |
| Candlestick and short bar sequences | 9 |
| Chart-pattern objects and completion | 9 |
| Derived-series operations | 5 |
| Volume, order flow, and order book | 6 |
| Ordered compound events | 3 |
| **Total** | **60** |

## touch — Level touch

- **Family:** Price-level interaction.
- **Aliases:** contact; tag; hit.
- **Definition:** Price reaches a defined reference price or zone boundary.
- **Boundaries:** A touch says neither that price crossed nor rejected the reference; it is not an order action.
- **Observable inputs:** Timestamped bid/ask, last-trade, or OHLC price; a pre-existing reference and its price basis.
- **Recognition semantics:** Record when the chosen price field first intersects the reference band during an observation window; retain intrabar versus bar-close status.
- **Parameters/profiles:** `reference`, `price_field`, `zone_tolerance`, `evaluation_mode`; all `source-stated` when supplied, otherwise `unresolved`.
- **Eligible roles:** trigger, confirmation, location interaction, management observation.
- **Market/data constraints:** Bid, ask, midpoint, and chart last price can produce different touches, especially with spread.
- **Transfer notes:** Portable to Forex and crypto spot; specify broker/exchange feed.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** A zone touch and a line touch are different geometric tests.

## rejection — Level rejection

- **Family:** Price-level interaction.
- **Aliases:** rejection candle; refusal; defended level.
- **Definition:** Price enters or reaches a reference area and then moves away on the original side without a specified sustained acceptance beyond it.
- **Boundaries:** A wick alone is only a candidate rejection; a failed breakout additionally requires a prior break attempt and return criterion.
- **Observable inputs:** Reference, OHLC/ticks, close location, subsequent path.
- **Recognition semantics:** Require contact plus departure away from the level; a binding selects same-bar, next-bar, or multi-bar confirmation and direction.
- **Parameters/profiles:** `rejection_distance`, `completion_window`, `close_requirement`, `direction`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, veto, exit/management prompt.
- **Market/data constraints:** Intrabar rejection may disappear in OHLC aggregation.
- **Transfer notes:** Portable to Forex and crypto spot.
- **Evidence/status:** Hammer-like wick rejection is a common candlestick reading; see https://www.investopedia.com/terms/h/hammer.asp. Terminology remains discretionary.
- **Uncertainty/variants:** “Defended” can imply participant intent that price data cannot prove.

## breach — Reference breach

- **Family:** Price-level interaction.
- **Aliases:** penetration; violation; pierce; cross-through.
- **Definition:** Price trades at least partly beyond a defined line, zone edge, swing, or range boundary.
- **Boundaries:** A breach is an event of traversal, not a confirmed breakout, BOS, or acceptance.
- **Observable inputs:** Reference geometry and tick/OHLC path.
- **Recognition semantics:** Detect first movement beyond the selected boundary using a stated price field; preserve maximum penetration and whether the bar closed beyond.
- **Parameters/profiles:** `boundary`, `price_field`, `minimum_penetration`, `intrabar_or_close`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, prerequisite, invalidation observation, confirmation input.
- **Market/data constraints:** A feed’s bid/ask convention materially affects threshold breaches.
- **Transfer notes:** Portable, subject to broker/exchange quote provenance.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Some authors call every breach a “break”; this dictionary reserves confirmation for separate entries.

## close-through — Close beyond reference

- **Family:** Price-level interaction.
- **Aliases:** body close through; decisive close; close outside.
- **Definition:** The selected bar closes on the opposite side of a reference from its pre-event side.
- **Boundaries:** It does not itself establish duration of acceptance, follow-through, or a market-structure classification.
- **Observable inputs:** Bar close, reference, prior-side state.
- **Recognition semantics:** At completed-bar evaluation, compare close with the reference/band and require the prior state to be on the other side.
- **Parameters/profiles:** `bar_timeframe`, `close_price_basis`, `zone-edge_rule`, `minimum_close_distance`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation, state-transition input.
- **Market/data constraints:** Requires completed bars; chart close differs across decentralized spot-FX feeds.
- **Transfer notes:** Portable; record broker or exchange and bar construction.
- **Evidence/status:** Close-based confirmation is a published convention in SMC descriptions, e.g. https://dailypriceaction.com/blog/smc-market-structure.
- **Uncertainty/variants:** “Decisive” may mean any close, body percentage, or multiple closes depending on methodology.

## acceptance-beyond-reference — Acceptance outside reference

- **Family:** Price-level interaction.
- **Aliases:** hold outside; acceptance; established beyond.
- **Definition:** A breach is followed by specified evidence that price remains or trades predominantly beyond a reference.
- **Boundaries:** Not synonymous with the first close-through; it is a later persistence state, not proof of market intent.
- **Observable inputs:** Reference, sequence of closes/ranges/time spent, optionally volume.
- **Recognition semantics:** After a breach, evaluate a source-defined hold rule such as consecutive closes, elapsed time, or lack of reclaim.
- **Parameters/profiles:** `hold_window`, `acceptance_measure`, `minimum_distance`, `reclaim_timeout`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, filter, trigger, invalidation state.
- **Market/data constraints:** Time-at-price needs tick data; bar proxies lose path detail.
- **Transfer notes:** Portable; exchange volume may support the reading in crypto, but is venue-local.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Auction-market “acceptance” is often more specific than retail close-count usage.

## breakout — Confirmed upside/downside breakout

- **Family:** Price-level interaction.
- **Aliases:** breakdown (downside); range break; escape; release.
- **Definition:** A reference boundary is breached in a stated direction and meets the binding’s confirmation condition.
- **Boundaries:** “Breakout” is direction-neutral here; it is not automatically a chart-pattern completion, structural BOS, or entry.
- **Observable inputs:** Reference object, price path, completion rule, optional activity data.
- **Recognition semantics:** First identify a bounded object/reference, then apply a declared confirmation basis: intrabar, close-through, acceptance, or follow-through.
- **Parameters/profiles:** `object_type`, `direction`, `confirmation_basis`, `window`, `minimum_penetration`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation, exit/management prompt.
- **Market/data constraints:** Gaps and thin books may leap a boundary without trading every intervening price.
- **Transfer notes:** Portable. Exchange-volume confirmation from equities/futures does not transfer as a fact to spot FX.
- **Evidence/status:** Pennant literature distinguishes an object from its breakout; see https://www.investopedia.com/terms/p/pennant.asp.
- **Uncertainty/variants:** Some methods require a close; others treat a stop-triggered intrabar print as breakout.

## failed-breakout — Failed breakout or breakdown

- **Family:** Price-level interaction.
- **Aliases:** false breakout; fakeout; bull trap (upside); bear trap (downside).
- **Definition:** A prior breakout attempt fails its stated hold/follow-through criterion and returns to the former side or range.
- **Boundaries:** A failed breakout concerns a boundary; an SFP is the narrower prior-swing version; it does not prove anyone was trapped.
- **Observable inputs:** Boundary, breach, closes/path after breach, timeout.
- **Recognition semantics:** Detect a confirmed or attempted break, then a reclaim/re-entry within a binding-defined window; retain both event timestamps.
- **Parameters/profiles:** `initial_break_basis`, `failure_basis`, `failure_window`, `reference`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, veto, invalidation.
- **Market/data constraints:** Fast markets need tick history to distinguish one print from an accepted excursion.
- **Transfer notes:** Portable; no centralized volume assumption for Forex spot.
- **Evidence/status:** Bull/bear traps are commonly defined as failed upside/downside breakouts: https://phemex.com/academy/bull-trap-vs-bear-trap.
- **Uncertainty/variants:** “Quickly” and “decisively” have no universal duration threshold.

## reclaim — Reference reclaim

- **Family:** Price-level interaction.
- **Aliases:** recover level; regain; re-entry; close back inside.
- **Definition:** After price is on one side of a reference, it crosses or closes back to the prior/reference-favored side.
- **Boundaries:** Reclaim is an event; sustained holding after it is a separate acceptance/retest question.
- **Observable inputs:** Reference, prior-side state, price path and close.
- **Recognition semantics:** Require a prior loss/breach and then a stated recovery basis, normally a cross or close back across the reference.
- **Parameters/profiles:** `lost_side`, `reclaim_basis`, `completion_window`, `hold_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation reversal, management observation.
- **Market/data constraints:** Must pin the reference to a feed and timeframe; zone reclaims need an edge or midpoint rule.
- **Transfer notes:** Portable to Forex and crypto spot.
- **Evidence/status:** A reclaim is commonly described as a lost level recovered and held; see http://moomoo.com/community/feed/stock-education-101-2026-18-53-trading-the-reclaim-when-116478155948037.
- **Uncertainty/variants:** Some SMC material calls a reclaim CHoCH; this candidate does not conflate them.

## retest — Post-event retest

- **Family:** Price-level interaction.
- **Aliases:** pullback test; throwback (after upside break); pullback (after downside break).
- **Definition:** After a break, reclaim, or departure, price returns to interact with the implicated reference.
- **Boundaries:** A retest is a revisit, not evidence that the level held; it is not necessarily an entry event.
- **Observable inputs:** Original event/reference, subsequent path, interaction outcome.
- **Recognition semantics:** Register a return to the reference after separation, while preserving event order and then separately label hold, rejection, or failure.
- **Parameters/profiles:** `origin_event`, `minimum_separation`, `retest_window`, `touch_basis`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, location interaction, management.
- **Market/data constraints:** On short timeframes a retest may occur entirely inside one higher-timeframe bar.
- **Transfer notes:** Portable.
- **Evidence/status:** Breakout/retest teaching describes a level break, return, and subsequent assessment: https://tradefundrr.com/breakout-retest-confirmation.
- **Uncertainty/variants:** Some methods allow a near-miss zone retest; others require exact contact.

## flip-of-role — Support/resistance role flip

- **Family:** Price-level interaction.
- **Aliases:** S/R flip; polarity flip; resistance-becomes-support; support-becomes-resistance.
- **Definition:** A previously observed reference changes its interpreted side-dependent role after a break and subsequent interaction.
- **Boundaries:** This is not merely a breakout or retest; it requires both a role assumption and observed post-break behavior.
- **Observable inputs:** Reference, pre-break role label, break event, later test/rejection or acceptance.
- **Recognition semantics:** State the old role, detect the transition through it, then test whether later interactions conform to the opposite role according to a bound rule.
- **Parameters/profiles:** `prior_role`, `break_basis`, `post_break_test`, `role_confirmation`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context, invalidation.
- **Market/data constraints:** Role is interpretive and can differ across timeframes.
- **Transfer notes:** Portable price-action primitive.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** A later touch can fail without invalidating the historical role label.

## liquidity-sweep — Liquidity sweep

- **Family:** Liquidity/failure language.
- **Aliases:** liquidity grab; raid; run on liquidity; take liquidity.
- **Definition:** Price trades through a visible reference treated by a methodology as a likely order-clustering location; outcome is recorded separately unless a reclaim is specified.
- **Boundaries:** A sweep is observable traversal, not evidence of institutional intent, stop execution, or reversal. An SFP adds failure/reclaim requirements.
- **Observable inputs:** Prior high/low, equal extreme, range/session boundary, price path; actual resting orders only if venue data exposes them.
- **Recognition semantics:** Mark a candidate pool/reference and the first traversal beyond it; tag `reclaim`, `continuation`, or `unresolved` only after subsequent evidence.
- **Parameters/profiles:** `pool_reference`, `sweep_basis`, `minimum_penetration`, `outcome_window`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, context, confirmation prerequisite, target/exit observation.
- **Market/data constraints:** Stops are not visible in spot FX; chart-based “liquidity” is an inference. CEX order data is only venue-local.
- **Transfer notes:** Use price-defined candidate pools for Forex spot; do not claim order visibility. Use named exchange data for crypto spot.
- **Evidence/status:** SMC references commonly map equal highs/lows to candidate pools and distinguish pool from sweep: https://www.luxalgo.com/library/concept/equal-highs-lows-as-liquidity.
- **Uncertainty/variants:** Some authors require a reclaim for “sweep”; others use it for any run through a level.

## stop-run-label — Stop-run / stop-hunt label

- **Family:** Liquidity/failure language.
- **Aliases:** stop hunt; stops taken; stop-loss run.
- **Definition:** A narrative label applied to a move through a location where stops may plausibly cluster.
- **Boundaries:** It is not a directly observable causal event from chart data and must not be normalized into an assertion of manipulation or participant identity.
- **Observable inputs:** Price-defined reference and breach; optionally venue-specific stop/order information where actually available.
- **Recognition semantics:** Store the neutral observable event as `liquidity-sweep` or `prior-extreme breach`; retain “stop run/hunt” only as a source alias/narrative claim with evidence.
- **Parameters/profiles:** `source_term`, `candidate_stop_location`, `observable_proxy`; all `source-stated` when quoted, otherwise `unresolved`.
- **Eligible roles:** context label, trigger alias, evidence annotation.
- **Market/data constraints:** Stop locations are generally hidden; broker flow cannot establish whole-market causality.
- **Transfer notes:** Especially important in decentralized spot FX; do not infer global stops from one broker.
- **Evidence/status:** Public definitions frequently assert intention, e.g. https://www.investopedia.com/terms/s/stophunting.asp; that claim exceeds ordinary chart observability.
- **Uncertainty/variants:** “Liquidity sweep,” “grab,” and “stop hunt” are often treated as synonyms despite different implied causality.

## swing-failure-pattern — Swing failure pattern

- **Family:** Liquidity/failure language.
- **Aliases:** SFP; failure swing; 2B (related); failed raid.
- **Definition:** Price exceeds a designated prior swing high/low and then closes or otherwise returns to the original side, under a declared timing rule.
- **Boundaries:** It is a swing-specific false break; it is not every wick, every liquidity sweep, or Wilder’s oscillator failure swing.
- **Observable inputs:** Confirmed prior swing, breach, bar closes, return timing.
- **Recognition semantics:** Identify a prior swing using the bound swing detector; detect violation; require a close/reclaim back through the swing level on the same or later allowed bar.
- **Parameters/profiles:** `swing_detector`, `reclaim_basis`, `same_bar_or_next_bar`, `window`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation observation, exit prompt.
- **Market/data constraints:** Bar-close definition is feed/timeframe dependent; intrabar formation is provisional.
- **Transfer notes:** Portable; describe it as price behavior, not proof that stops executed.
- **Evidence/status:** Detailed boundary discussion: https://www.luxalgo.com/library/concept/swing-failure-pattern/.
- **Uncertainty/variants:** Some allow several bars for the reclaim; others require the sweep candle itself.

## liquidity-run — Liquidity run / continuation through pool

- **Family:** Liquidity/failure language.
- **Aliases:** low-resistance run; liquidity run; sweep-and-continue.
- **Definition:** Price traverses a candidate liquidity reference and then remains/continues on the new side rather than reclaiming it within the specified window.
- **Boundaries:** Not the same as a sweep–reclaim reversal. “Low resistance” is a methodology interpretation, not a measured cause.
- **Observable inputs:** Candidate pool, breach, close/acceptance/follow-through data.
- **Recognition semantics:** Link a pool traversal to a later acceptance-beyond-reference state; preserve whether the pool itself was only inferred from chart geometry.
- **Parameters/profiles:** `pool_reference`, `acceptance_basis`, `continuation_window`, `minimum_follow_through`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context transition, invalidation.
- **Market/data constraints:** Actual available liquidity cannot be inferred reliably from candles alone.
- **Transfer notes:** Use price proxy in spot FX; crypto CEX depth must identify exchange and snapshot timing.
- **Evidence/status:** ICT material explicitly contrasts a pool that reverses with one that continues: https://innercircletrader.net/tutorials/ict-liquidity-pool.
- **Uncertainty/variants:** “Sweep” itself may include continuation in some vocabularies, so labels should preserve source usage.

## wyckoff-spring-upthrust — Wyckoff spring / upthrust event

- **Family:** Liquidity/failure language.
- **Aliases:** spring; upthrust; UTAD (upthrust after distribution); shakeout.
- **Definition:** A downside range-boundary failure and reclaim (spring), or its upside mirror (upthrust), in Wyckoff terminology.
- **Boundaries:** This is a labelled failed range break, not proof of accumulation/distribution or operator activity; UTAD adds phase/context claims.
- **Observable inputs:** Defined range, support/resistance boundary, breach and return/hold.
- **Recognition semantics:** Detect a range-edge breach, then return inside according to the bound reclaim/hold rule; separately record any claimed Wyckoff phase as interpretation.
- **Parameters/profiles:** `range_definition`, `reclaim_window`, `hold_rule`, `phase_label`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context, invalidation.
- **Market/data constraints:** Classical Wyckoff volume readings arise from centralized markets; price-only event is less data-dependent.
- **Transfer notes:** Price event transfers to Forex/crypto spot; volume/phase inferences require venue-qualified evidence.
- **Evidence/status:** Basic spring/upthrust definitions: https://investinganswers.com/dictionary/s/springs-and-upthrusts.
- **Uncertainty/variants:** Some writers equate these to liquidity sweeps; others require specific Wyckoff schematics.

## failed-n-period-extreme — Failed N-period extreme

- **Family:** Liquidity/failure language.
- **Aliases:** Turtle Soup pattern (related); failed Donchian breakout; N-bar false break.
- **Definition:** A break of a prior rolling N-bar high/low that returns through the old extreme under a stated failure rule.
- **Boundaries:** It is a parameterized event primitive, not the complete Turtle Soup strategy, which also specifies timing, offsets, stops, and management.
- **Observable inputs:** OHLC/ticks, rolling-extreme calculation, timing of old extreme, reclaim.
- **Recognition semantics:** Calculate prior N-bar extreme without look-ahead; record new extreme; then test stated return/reclaim conditions.
- **Parameters/profiles:** `N`; `minimum_age_of_old_extreme`; `failure_window`; all `source-stated` when reproducing a source. The classic Turtle Soup references `N=20` and a four-session age condition (`source-stated`): https://blueberrymarkets.com/market-analysis/turtle-soup-trading-strategy-identifying-potential-false-breakouts/.
- **Eligible roles:** trigger, confirmation, research normalization.
- **Market/data constraints:** Session definition alters daily rolling windows; FX five-day versus seven-day bars must be explicit.
- **Transfer notes:** Portable after session/calendar convention is declared.
- **Evidence/status:** terminology/source-derived normalization.
- **Uncertainty/variants:** Do not silently carry source-specific entry offset or stop rules into this primitive.

## structure-break — Swing-structure break

- **Family:** Market structure.
- **Aliases:** structural break; swing break; break in sequence.
- **Definition:** Price breaches or closes through a selected structural swing reference generated by a declared swing model.
- **Boundaries:** It is the neutral superclass for BOS/CHoCH/MSS labels; not every horizontal breakout is structural.
- **Observable inputs:** Swing points, structural hierarchy, price event, close basis.
- **Recognition semantics:** Generate swings without forward-looking ambiguity where possible; classify the crossed swing and direction relative to prior sequence.
- **Parameters/profiles:** `swing_algorithm`, `hierarchy`, `break_basis`, `close_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context/regime transition, invalidation.
- **Market/data constraints:** Swing algorithms repaint or differ in delay and granularity.
- **Transfer notes:** Portable price-based concept.
- **Evidence/status:** SMC literature treats the swing definition and close condition as material: https://dailypriceaction.com/blog/smc-market-structure.
- **Uncertainty/variants:** “Structure” can mean local pivots, external pivots, fractals, or discretionary legs.

## bos — Break of structure (BOS)

- **Family:** Market structure.
- **Aliases:** BoS; continuation break; structural continuation.
- **Definition:** In a common SMC convention, a structure break in the direction of the designated prevailing swing trend.
- **Boundaries:** Not a universal synonym for any break; some authors use BOS for both continuation and reversal or require a close/displacement/inducement.
- **Observable inputs:** Trend/swing sequence, selected structural extreme, break event.
- **Recognition semantics:** Establish a trend direction from the bound swing model, then identify a same-direction break of its designated continuation extreme.
- **Parameters/profiles:** `trend_model`, `internal_or_external`, `break_basis`, `required_displacement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context transition.
- **Market/data constraints:** Hierarchy choice changes whether a move is BOS, CHoCH, or neither.
- **Transfer notes:** Portable as a price label; no institutional-flow claim transfers with it.
- **Evidence/status:** One prevalent BOS/CHoCH distinction is documented at https://innercircletrader.net/tutorials/break-of-structure-vs-change-of-character/.
- **Uncertainty/variants:** Definition disputed; preserve a source’s own swing and confirmation rule.

## choch — Change of character (CHoCH)

- **Family:** Market structure.
- **Aliases:** ChoCH; change in character; character change.
- **Definition:** In a common SMC convention, the first relevant structure break against the established swing trend.
- **Boundaries:** It is an early transition label, not confirmation that a full reversal occurred, and not automatically synonymous with MSS.
- **Observable inputs:** Existing swing trend, protected/selected countertrend extreme, break/close data.
- **Recognition semantics:** Bind a prior structure model and identify the first opposite-direction break of the required swing; record whether it is internal or external.
- **Parameters/profiles:** `prior_trend_requirement`, `protected_swing_rule`, `break_basis`, `hierarchy`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context/regime transition, invalidation.
- **Market/data constraints:** Lower-timeframe CHoCH may be a pullback within a higher-timeframe trend.
- **Transfer notes:** Portable price label; separate it from claims about “smart money.”
- **Evidence/status:** A representative definition calls it the first break against trend: https://tradingwyckoff.com/en/smart-money-concepts.
- **Uncertainty/variants:** Some communities use CHoCH and MSS interchangeably; others distinguish force or timeframe.

## mss — Market structure shift (MSS)

- **Family:** Market structure.
- **Aliases:** market-structure shift; market shift; MSS.
- **Definition:** A methodology-dependent label for a transition in structure, often an opposite-direction swing break and, in some ICT usage, one accompanied by displacement.
- **Boundaries:** Not universally identical to CHoCH; neither term provides a canonical swing-selection or strength threshold.
- **Observable inputs:** Swing sequence, structural break, optionally range/body/imbalance measures.
- **Recognition semantics:** Store the source’s MSS rule explicitly: neutral `structure-break` plus optional `opposite-direction`, `displacement`, and hierarchy predicates.
- **Parameters/profiles:** `swing_scope`, `opposite_break_required`, `displacement_required`, `close_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, regime transition.
- **Market/data constraints:** Displacement criteria are visual and feed/timeframe dependent.
- **Transfer notes:** Portable as a descriptive price transition, but do not assume its ICT causal story.
- **Evidence/status:** A published SMC guide distinguishes CHoCH/MSS by intensity/displacement: https://tradingwyckoff.com/en/smart-money-concepts.
- **Uncertainty/variants:** This disagreement is substantive and must remain visible in later bindings.

## internal-external-structure-transition — Internal/external structure transition

- **Family:** Market structure.
- **Aliases:** internal BOS; external BOS; minor/major structure break.
- **Definition:** A structural break classified by the hierarchy of the crossed swing rather than direction alone.
- **Boundaries:** “Internal” is not intrinsically lower timeframe; it depends on the bound swing nesting model.
- **Observable inputs:** Multi-scale swing model, parent/child swing relationships, breach/close event.
- **Recognition semantics:** Assign each swing to a hierarchy, then classify the crossed reference as internal or external relative to the active leg/range.
- **Parameters/profiles:** `hierarchy_method`, `parent_leg_rule`, `swing_detector`, `break_basis`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, context, filter.
- **Market/data constraints:** No shared industry hierarchy exists; indicators can relabel history.
- **Transfer notes:** Portable price construction.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Some SMC sources reserve external structure for protected highs/lows; others use timeframe labels.

## trend-sequence-failure — Trend-sequence failure

- **Family:** Market structure.
- **Aliases:** higher-low failure; lower-high failure; trend failure.
- **Definition:** Failure of a bound sequence condition, such as a higher low or lower high, through a specified structural event.
- **Boundaries:** It is more general than CHoCH and does not by itself establish a new opposite trend.
- **Observable inputs:** Trend-sequence model, pivots, break/close data.
- **Recognition semantics:** Establish the expected sequence, identify its protected element, and flag a violation using the declared breach or close basis.
- **Parameters/profiles:** `sequence_definition`, `protected_element`, `violation_basis`, `hierarchy`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation, management.
- **Market/data constraints:** Pivot confirmation delay can make the event known only later.
- **Transfer notes:** Portable.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** A failed higher low may be called CHoCH, MSS, or simply a pullback break depending on scope.

## displacement — Directional displacement

- **Family:** Momentum, range, and volatility.
- **Aliases:** impulse displacement; repricing burst; displacement candle.
- **Definition:** A rapid directional move materially larger/faster than its recent local behavior, often described in ICT/SMC as body-dominant and leaving an imbalance.
- **Boundaries:** Not every large candle is displacement; it is not an entry action or proof of institutional participation.
- **Observable inputs:** OHLC/ticks, recent range/body distribution, direction, overlap, optional gap/imbalance.
- **Recognition semantics:** Compare directional range, body share, velocity, and overlap against a stated local baseline; separately record any structure break or imbalance.
- **Parameters/profiles:** `baseline_window`, `range_or_body_comparator`, `body_ratio`, `imbalance_requirement`; all `unresolved` unless source-stated. Published ICT-style heuristics are conventions, not standards.
- **Eligible roles:** trigger, confirmation, momentum filter, transition descriptor.
- **Market/data constraints:** News and thin-liquidity spikes can resemble displacement; bar aggregation changes appearance.
- **Transfer notes:** Portable price event; central order-flow attribution does not transfer to spot FX.
- **Evidence/status:** ICT terminology overview: https://www.alphaexcapital.com/smart-money-concepts/displacement-in-ict-trading.
- **Uncertainty/variants:** Whether an FVG or structure break is mandatory is disputed.

## momentum-expansion — Momentum expansion transition

- **Family:** Momentum, range, and volatility.
- **Aliases:** acceleration; impulse expansion; thrust.
- **Definition:** A transition from comparatively muted directional movement to faster or larger directional movement measured by a chosen momentum/range proxy.
- **Boundaries:** Momentum expansion is not necessarily volatility expansion; the latter can be two-sided.
- **Observable inputs:** Price returns/ranges, directional efficiency, derived momentum series.
- **Recognition semantics:** Compute a declared directional magnitude/velocity measure and detect crossing from a lower to higher regime or baseline-relative expansion.
- **Parameters/profiles:** `metric`, `baseline_window`, `expansion_threshold`, `direction`, `evaluation_mode`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter, management transition.
- **Market/data constraints:** Metrics are derived and can be sensitive to session gaps and bar size.
- **Transfer notes:** Portable; clearly name data feed and session handling.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** A directional large bar may be displacement, volatility expansion, both, or neither under different definitions.

## volatility-expansion — Volatility expansion transition

- **Family:** Momentum, range, and volatility.
- **Aliases:** range expansion; volatility breakout; expansion phase.
- **Definition:** A move from lower to higher realized range/dispersion according to a selected measure, regardless of direction.
- **Boundaries:** It does not state directional bias or predict continuation; an outside bar is one possible local manifestation.
- **Observable inputs:** High-low/true ranges, returns, ATR-like or realized-volatility measure.
- **Recognition semantics:** Compare current range/volatility measure to a stated rolling/distributional baseline and flag an upward regime transition.
- **Parameters/profiles:** `volatility_measure`, `lookback`, `threshold`, `session_treatment`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, filter, context/regime transition, management modifier.
- **Market/data constraints:** Gaps and weekend closures distort range metrics.
- **Transfer notes:** Portable; crypto’s continuous session and FX weekend closure require separate profiles.
- **Evidence/status:** Inside/narrow-range sources frame contraction and later expansion as separate states: https://www.netpicks.com/nr7-inside-bar/.
- **Uncertainty/variants:** “Expansion” may refer to candle range, ATR, Bollinger width, or implied volatility.

## volatility-contraction — Volatility contraction transition

- **Family:** Momentum, range, and volatility.
- **Aliases:** compression; coiling; squeeze; range contraction.
- **Definition:** A move from higher to lower realized range/dispersion according to a selected measure.
- **Boundaries:** It is a condition/state transition, not the later directional breakout or a promise of one.
- **Observable inputs:** Bar ranges/returns; optional band-width or other derived-volatility series.
- **Recognition semantics:** Flag decreasing or below-baseline volatility under a bound measure and window; record whether price also remains geometrically bounded.
- **Parameters/profiles:** `measure`, `lookback`, `contraction_threshold`, `persistence_window`; all `unresolved` unless source-stated.
- **Eligible roles:** context, filter, arming condition, confirmation input.
- **Market/data constraints:** Low reported volume and low volatility are distinct observations.
- **Transfer notes:** Portable.
- **Evidence/status:** NR7/inside-bar material describes these as volatility contractions: https://www.netpicks.com/nr7-inside-bar/.
- **Uncertainty/variants:** A visual “coil” is discretionary unless geometry/metric is bound.

## contraction-resolution-break — Contraction resolution break

- **Family:** Momentum, range, and volatility.
- **Aliases:** squeeze release; compression breakout; coil break.
- **Definition:** A price boundary break occurring after a recognized contraction state.
- **Boundaries:** It is an ordered condition-plus-event primitive, not a strategy; it does not require a particular pattern object.
- **Observable inputs:** Contraction state, reference/range geometry, subsequent breakout and optional expansion.
- **Recognition semantics:** Require contraction first, then a break of its bound range/series threshold; retain waiting time and breakout direction.
- **Parameters/profiles:** `contraction_definition`, `range_definition`, `break_basis`, `maximum_delay`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequencing primitive.
- **Market/data constraints:** Exact state depends on bar timeframe and session continuity.
- **Transfer notes:** Portable.
- **Evidence/status:** Published NR7 convention defines the narrowest range in seven periods; see https://theforexgeek.com/nr7-inside-bar/.
- **Uncertainty/variants:** A contraction can resolve by continuation, reversal, or continued compression.

## range-expansion-bar — Range expansion bar

- **Family:** Momentum, range, and volatility.
- **Aliases:** wide-range bar; WRB; expansion candle.
- **Definition:** A completed bar whose high-low range exceeds a defined local comparator.
- **Boundaries:** It is a one-bar observable, not automatically displacement, outside bar, or directional confirmation.
- **Observable inputs:** OHLC and comparative range series.
- **Recognition semantics:** Compare current bar range to prior-N ranges, ATR, percentile, or source rule; record close location separately.
- **Parameters/profiles:** `comparator`, `lookback`, `threshold`, `include_gap`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, volatility filter, management observation.
- **Market/data constraints:** Synthetic broker candles and illiquid prints can create spurious wide ranges.
- **Transfer notes:** Portable with quote-source declaration.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** “Wide” is relative; no universal multiplier should be assumed.

## wick-rejection-bar — Wick-rejection bar

- **Family:** Candlestick and short bar sequences.
- **Aliases:** pin bar; hammer (downside-wick variant); shooting star (upside-wick variant); rejection candle.
- **Definition:** A completed single bar with a relatively prominent wick and a body/close positioned away from that wick’s extreme.
- **Boundaries:** It is a bar-shape object/event, not a level rejection unless location is separately bound; hammer/shooting-star labels carry context conventions.
- **Observable inputs:** OHLC, relative body/wick measures, optional prior movement/reference.
- **Recognition semantics:** Calculate body and upper/lower wick ratios; identify the dominant wick and closing position, then optionally associate with a level touch.
- **Parameters/profiles:** `minimum_wick_ratio`, `maximum_opposite_wick`, `body_ratio`, `context_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter, exit prompt.
- **Market/data constraints:** Bar shape changes with timeframe and feed construction.
- **Transfer notes:** Portable.
- **Evidence/status:** Hammer definition and its contextual caveat: https://www.investopedia.com/terms/h/hammer.asp.
- **Uncertainty/variants:** Colour and exact wick/body thresholds vary materially among scanners.

## engulfing-completion — Engulfing completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** bullish engulfing; bearish engulfing; outside-body engulf.
- **Definition:** Completion of a two-bar sequence where the second real body overlaps/encloses the prior real body under the selected convention.
- **Boundaries:** A body engulf is not necessarily a full-range outside bar, and a bullish/bearish label is not a guaranteed reversal.
- **Observable inputs:** Consecutive OHLC bars and bar-close order.
- **Recognition semantics:** At second-bar close, compare real-body intervals; bind whether strict containment, overlap, and prior candle direction are required.
- **Parameters/profiles:** `body_vs_full_range`, `prior_direction_required`, `containment_rule`, `context_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter, exit prompt.
- **Market/data constraints:** Requires completed second bar; gaps can affect visual classification.
- **Transfer notes:** Portable.
- **Evidence/status:** Investopedia defines bullish engulfing using real bodies rather than shadows: https://www.investopedia.com/terms/b/bullishengulfingpattern.asp.
- **Uncertainty/variants:** Some scanners require a larger second body or trend context; others do not.

## inside-bar — Inside bar completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** inside day; mother-bar containment; Harami range (not body harami).
- **Definition:** A completed bar whose high-low range lies within the preceding mother bar’s high-low range.
- **Boundaries:** This is a contraction pattern object/state, not the later break of the mother-bar range.
- **Observable inputs:** Two consecutive OHLC bars.
- **Recognition semantics:** At bar close, require current high no higher and current low no lower than the prior bar under stated equality handling.
- **Parameters/profiles:** `strict_or_inclusive_containment`, `mother_bar_selection`, `nested_handling`; all `unresolved` unless source-stated.
- **Eligible roles:** context, arming condition, filter, pattern reference.
- **Market/data constraints:** Different chart feeds may differ by one tick at a boundary.
- **Transfer notes:** Portable.
- **Evidence/status:** Definition: https://theforexgeek.com/nr7-inside-bar/.
- **Uncertainty/variants:** Nested inside bars may use the immediately prior bar or the original mother bar.

## mother-bar-break — Mother-bar range break

- **Family:** Candlestick and short bar sequences.
- **Aliases:** inside-bar breakout; mother-bar breakout; IB resolution.
- **Definition:** A break of a declared mother bar’s high or low after one or more inside bars.
- **Boundaries:** It requires a prior inside-bar object; it is not a generic breakout, nor does it prescribe an order type.
- **Observable inputs:** Mother bar, associated inside-bar sequence, later price event.
- **Recognition semantics:** Bind mother-bar selection and containment chain; then detect breach or close-through of its boundary after the sequence completes.
- **Parameters/profiles:** `containment_rule`, `mother_bar_rule`, `break_basis`, `maximum_wait`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, ordered event primitive.
- **Market/data constraints:** Intrabar double-sided breaks can be unknowable from OHLC alone.
- **Transfer notes:** Portable.
- **Evidence/status:** Inside bars are commonly treated as contraction; see https://www.netpicks.com/nr7-inside-bar/.
- **Uncertainty/variants:** Some use the inside bar’s own boundary rather than the mother-bar boundary.

## outside-bar — Outside bar completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** outside day; engulfing range; expansion bar.
- **Definition:** A completed bar with both a higher high and a lower low than the preceding bar.
- **Boundaries:** It is full-range expansion, not necessarily a real-body engulfing pattern or a directional reversal.
- **Observable inputs:** Two consecutive OHLC bars.
- **Recognition semantics:** At completion compare current high and low to the preceding range; separately retain close location/direction.
- **Parameters/profiles:** `strict_or_inclusive_extremes`, `direction_rule`, `context_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, volatility filter, management prompt.
- **Market/data constraints:** Needs completed bars; synthetic candles can alter range relations.
- **Transfer notes:** Portable.
- **Evidence/status:** Inside/outside distinction is summarized at https://www.stockgro.club/blogs/trading/inside-bar-candlestick-pattern.
- **Uncertainty/variants:** Some names require the close to favor one side; neutral definition does not.

## star-reversal-completion — Three-bar star reversal completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** morning star; evening star; abandoned-baby variant.
- **Definition:** Completion of a specified three-bar reversal configuration, normally including an impulse bar, an intervening small-body/star bar, and a third bar closing back into the first bar’s body.
- **Boundaries:** It is a family template; do not treat every three-bar reversal as a morning/evening star, and gaps may be unavailable in continuous markets.
- **Observable inputs:** Three completed OHLC bars, optional gaps, prior direction.
- **Recognition semantics:** Bind the exact pattern grammar and require the third completed bar to meet its specified close/depth condition.
- **Parameters/profiles:** `body_size_rule`, `gap_requirement`, `third_bar_penetration`, `prior_trend_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter.
- **Market/data constraints:** True gaps are uncommon intraday and in 24/7 crypto spot.
- **Transfer notes:** Use non-gap variants explicitly for Forex/crypto spot rather than silently importing equity rules.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Published definitions vary in whether gaps and colour are mandatory.

## three-bar-directional-completion — Three-bar directional sequence completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** three white soldiers; three black crows; three-bar momentum sequence.
- **Definition:** Completion of a declared run of three directionally aligned bars with a specified progression in opens/closes/ranges.
- **Boundaries:** Not a generic three-bar trend and not necessarily a reversal; it does not establish volume or order-flow cause.
- **Observable inputs:** Three sequential OHLC bars, optional prior trend/context.
- **Recognition semantics:** Apply a bound grammar for bar direction, body prominence, close progression, and overlap; classify at third-bar completion.
- **Parameters/profiles:** `direction_rule`, `body_ratio`, `open_overlap_rule`, `context_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, momentum filter.
- **Market/data constraints:** Classification differs under Heikin-Ashi or other transformed bars.
- **Transfer notes:** Portable on ordinary OHLC charts.
- **Evidence/status:** Candlestick taxonomies list these named variants: https://enrichmoney.in/knowledge-center-chapter/types-candlesticks-patterns.
- **Uncertainty/variants:** Requirements for progressive closes and wick sizes are not standardized.

## nrn-completion — Narrow-range N completion

- **Family:** Candlestick and short bar sequences.
- **Aliases:** NR4; NR7; narrowest-range bar.
- **Definition:** A completed bar whose range is the smallest among a declared trailing N-bar comparison set.
- **Boundaries:** It records contraction only; a later high/low break is a separate resolution event.
- **Observable inputs:** OHLC range series and a non-look-ahead N-bar window.
- **Recognition semantics:** At bar close, compare the bar’s high-low range with the preceding N-minus-one completed bars, declaring tie treatment.
- **Parameters/profiles:** `N`; `range_measure`; `tie_rule`; all `source-stated` when reproducing a named source. `N=7` for NR7 is a published convention: https://theforexgeek.com/nr7-inside-bar/.
- **Eligible roles:** arming condition, context, filter, pattern reference.
- **Market/data constraints:** Daily FX calendar/session construction changes the bar set.
- **Transfer notes:** Portable after time-boundary convention is stated.
- **Evidence/status:** published convention.
- **Uncertainty/variants:** Some require simultaneous inside-bar status; that is a compound condition, not inherent to NRN.

## nrn-resolution — Narrow-range N resolution break

- **Family:** Candlestick and short bar sequences.
- **Aliases:** NR7 break; narrow-range breakout.
- **Definition:** A break of the designated NRN bar’s high or low after its completion.
- **Boundaries:** Requires a prior NRN object; it is not the assertion that the resulting move will persist.
- **Observable inputs:** NRN reference bar and subsequent price path.
- **Recognition semantics:** Preserve the NRN completion timestamp, then detect stated breach/close of either boundary within a bound window.
- **Parameters/profiles:** `N`, `resolution_basis`, `window`, `one_or_both_sides_policy`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequence primitive.
- **Market/data constraints:** Both sides can trade within one bar; tick data is needed to order them.
- **Transfer notes:** Portable.
- **Evidence/status:** NR7 is described as a contraction precursor in https://www.netpicks.com/nr7-inside-bar/; no edge claim is adopted.
- **Uncertainty/variants:** Some use stop orders at boundaries; that is later entry semantics, excluded here.

## chart-pattern-object — Chart-pattern object

- **Family:** Chart-pattern objects and completion.
- **Aliases:** pattern candidate; developing pattern; chart formation.
- **Definition:** A recognized but not necessarily completed geometric price configuration with named landmarks and boundaries.
- **Boundaries:** It is an object/state, not its breakout, neckline break, target, or trade.
- **Observable inputs:** Pivot sequence, trendlines/curves, support/resistance landmarks, timeframe.
- **Recognition semantics:** Store pattern type, landmarks, geometry rule, development status, and invalidation boundary without labelling it complete prematurely.
- **Parameters/profiles:** `pattern_type`, `pivot_detector`, `geometric_tolerance`, `completion_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** context, location/reference, arming condition, filter.
- **Market/data constraints:** Pattern recognition is highly dependent on pivot model, scale, and chart transformation.
- **Transfer notes:** Portable price geometry.
- **Evidence/status:** Pattern sources distinguish formation from completed break; e.g. https://www.investopedia.com/terms/p/pennant.asp.
- **Uncertainty/variants:** Human-drawn and scanner-detected patterns need not agree.

## triangle-wedge-object — Triangle or wedge object

- **Family:** Chart-pattern objects and completion.
- **Aliases:** symmetrical/ascending/descending triangle; rising/falling wedge.
- **Definition:** A developing configuration of converging or channel-like boundary lines built from selected pivots.
- **Boundaries:** It is not a triangle/wedge breakout, and the same geometry can receive different names based on slope/context conventions.
- **Observable inputs:** At least two pivots per relevant boundary where the chosen construction requires them, trendline geometry, prior movement.
- **Recognition semantics:** Fit or draw bound upper/lower boundaries, record convergence/divergence, slope, landmarks, and unbroken status.
- **Parameters/profiles:** `pivot_rule`, `line_fit`, `minimum_touches`, `tolerance`, `classification_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** context, reference, arming condition, location.
- **Market/data constraints:** Line fitting can materially alter whether a break occurred.
- **Transfer notes:** Portable.
- **Evidence/status:** Pennant/triangle completion is commonly a boundary break: https://www.incrediblecharts.com/technical/flags_and_pennants.php.
- **Uncertainty/variants:** Whether a rising wedge is reversal versus continuation is context-dependent and not encoded here.

## flag-pennant-object — Flag or pennant object

- **Family:** Chart-pattern objects and completion.
- **Aliases:** flag; pennant; continuation congestion.
- **Definition:** A developing post-impulse consolidation object: parallel/sloping bounds for a flag or converging bounds for a pennant.
- **Boundaries:** It is not its later continuation break, and “continuation” is a traditional classification rather than a guaranteed outcome.
- **Observable inputs:** Prior impulse candidate, consolidation pivots/boundaries, optional volume.
- **Recognition semantics:** Bind impulse definition and subsequent geometry; record object boundaries and completion status independently.
- **Parameters/profiles:** `impulse_rule`, `geometry`, `minimum_bars`, `volume_profile`; all `unresolved` unless source-stated.
- **Eligible roles:** context, arming condition, reference, filter.
- **Market/data constraints:** Traditional volume conventions presume centralized reported volume.
- **Transfer notes:** Use price geometry in Forex spot; exchange volume may be separately bound for named crypto venue.
- **Evidence/status:** Pennant anatomy and breakout distinction: https://www.investopedia.com/terms/p/pennant.asp.
- **Uncertainty/variants:** Flag/pennant duration and required preceding move vary by source.

## reversal-pattern-object — Reversal pattern object

- **Family:** Chart-pattern objects and completion.
- **Aliases:** double top/bottom; triple top/bottom; head and shoulders; inverse H&S.
- **Definition:** A developing multi-swing configuration conventionally associated with possible reversal and defined by extrema plus an intervening neckline/reference.
- **Boundaries:** It is not complete before the stated neckline break; it does not predict reversal merely because the silhouette appears.
- **Observable inputs:** Prior trend, pivot sequence, similarity relationships, neckline construction.
- **Recognition semantics:** Store subtype, pivots, tolerance, neckline, and development state; require the later completion event separately.
- **Parameters/profiles:** `subtype`, `pivot_detector`, `similarity_tolerance`, `neckline_rule`, `prior_trend_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** context, arming condition, reference, filter.
- **Market/data constraints:** Similarity tolerance is discretionary and scanners encode their author’s rules.
- **Transfer notes:** Portable price geometry; volume confirmation from equities does not automatically transfer.
- **Evidence/status:** Double top/bottom sources explicitly separate potential object from neckline confirmation: https://stockeducation.com/technical-analysis-blogs/double-top-and-double-bottom-patterns.
- **Uncertainty/variants:** Head-and-shoulders shoulder symmetry and double-top equality have no universal threshold.

## cup-handle-object — Cup-with-handle object

- **Family:** Chart-pattern objects and completion.
- **Aliases:** cup and handle; C&H.
- **Definition:** A developing rounded base/recovery followed by a smaller handle-like pullback near a prior high, in the classic equity-charting vocabulary.
- **Boundaries:** It is not a confirmed breakout; equity-source duration/volume requirements are not universal Forex/crypto defaults.
- **Observable inputs:** OHLC pivots/curve, prior high, handle boundary, optional volume.
- **Recognition semantics:** Record cup landmarks, handle geometry, resistance boundary, and source-specific requirements without concluding completion until resistance is broken.
- **Parameters/profiles:** `rounding_rule`, `depth_limit`, `handle_rule`, `breakout_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** context, arming condition, reference, filter.
- **Market/data constraints:** Pattern is traditionally equity-derived and often volume-qualified.
- **Transfer notes:** Price geometry can be explored in Forex/crypto spot; retain the equity-origin and do not import volume claims.
- **Evidence/status:** Historical anatomy: https://aaii.com/journal/article/the-cup-with-handle-pattern.
- **Uncertainty/variants:** Curvature and handle classification are discretionary.

## pattern-boundary-break — Pattern boundary break

- **Family:** Chart-pattern objects and completion.
- **Aliases:** trendline break; geometric breakout; pattern breakout.
- **Definition:** A selected boundary of an already identified pattern object is breached or crossed under a declared confirmation basis.
- **Boundaries:** It is the generic completion candidate; a neckline break and a flag/pennant break are specialized instances with extra semantics.
- **Observable inputs:** Pattern object/boundary geometry, price path, close/acceptance data.
- **Recognition semantics:** Reference immutable pattern landmarks, then test price against the selected boundary using intrabar, close, or acceptance rule.
- **Parameters/profiles:** `pattern_id`, `boundary`, `break_basis`, `confirmation_window`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation.
- **Market/data constraints:** Diagonal boundary calculation must be reproducible and timestamp-aware.
- **Transfer notes:** Portable.
- **Evidence/status:** Flag/pennant sources describe completion through a boundary break: https://www.incrediblecharts.com/technical/flags_and_pennants.php.
- **Uncertainty/variants:** A line can be redrawn after the fact; preserve the contemporaneous geometry.

## neckline-completion — Neckline break / reversal-pattern completion

- **Family:** Chart-pattern objects and completion.
- **Aliases:** double-top confirmation; double-bottom confirmation; H&S completion.
- **Definition:** A selected neckline of a previously recorded reversal-pattern object is broken according to its completion rule.
- **Boundaries:** This event confirms the chart-pattern definition under that convention; it is not a completed order entry or guarantee of a trend reversal.
- **Observable inputs:** Pattern object, neckline geometry, price close/path.
- **Recognition semantics:** Require a prior qualified object and then a directional neckline breach/close; retain close versus intrabar basis and any later retest separately.
- **Parameters/profiles:** `pattern_subtype`, `neckline_rule`, `break_basis`, `confirmation_window`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, invalidation transition.
- **Market/data constraints:** Diagonal necklines require time-indexed values; volume confirmation is venue-specific.
- **Transfer notes:** Portable price event; central volume is optional and source-dependent.
- **Evidence/status:** Double-pattern confirmation by neckline close is described at https://stockeducation.com/technical-analysis-blogs/double-top-and-double-bottom-patterns; H&S reference: https://www.investopedia.com/terms/h/head-shoulders.asp.
- **Uncertainty/variants:** Some accept wick penetration, others require one or more closes.

## continuation-pattern-completion — Flag/pennant/triangle completion break

- **Family:** Chart-pattern objects and completion.
- **Aliases:** flag break; pennant break; triangle breakout.
- **Definition:** A boundary break of a recorded continuation-style object, with direction assessed relative to its bound prior impulse rather than presumed.
- **Boundaries:** It is not generic breakout because it references a named object; it is not a claim that the pre-pattern trend will continue.
- **Observable inputs:** Flag/pennant/triangle object, prior impulse direction, boundary, price event.
- **Recognition semantics:** Detect a specified object first, then its boundary break and optionally classify alignment/misalignment with the prior impulse.
- **Parameters/profiles:** `object_type`, `prior_impulse_rule`, `break_basis`, `alignment_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter.
- **Market/data constraints:** Volume confirmation is only reliable where volume is representative of the traded venue.
- **Transfer notes:** Price event portable; avoid treating FX tick volume as centralized volume.
- **Evidence/status:** Pennants are conventionally a consolidation followed by breakout: https://www.investopedia.com/terms/p/pennant.asp.
- **Uncertainty/variants:** Triangle type and intended direction are often classified differently across sources.

## pattern-failure — Pattern failure / invalidated completion

- **Family:** Chart-pattern objects and completion.
- **Aliases:** failed H&S; failed triangle; failed flag; pattern trap.
- **Definition:** A pattern object or completed pattern violates the binding’s defining/invalidation condition, such as returning through a completion boundary or exceeding a prohibited landmark.
- **Boundaries:** It is not merely a weak follow-through; failure criteria must be explicit. It does not prove trapped positions.
- **Observable inputs:** Pattern object, completion state, boundaries/landmarks, subsequent path.
- **Recognition semantics:** Link the later violation to the exact prior object and rule, differentiating pre-completion invalidation from post-completion failure.
- **Parameters/profiles:** `pattern_id`, `failure_rule`, `evaluation_window`, `close_or_intrabar`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, veto, invalidation, management prompt.
- **Market/data constraints:** Pattern ambiguity propagates into its failure classification.
- **Transfer notes:** Portable.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** “Failure” may mean a return inside, a full opposite break, or timeout.

## series-crossover — Derived-series crossover

- **Family:** Derived-series operations.
- **Aliases:** cross; signal-line cross; moving-average cross; golden/death cross (specific MA aliases).
- **Definition:** One ordered numeric series crosses another from one side to the other.
- **Boundaries:** It is an abstract operation, not a claim about any named indicator or trend regime, and it is not an order action.
- **Observable inputs:** Two time-aligned derived series, sampling schedule, prior relation.
- **Recognition semantics:** Detect a sign change in `series_A - series_B`; bind equality and confirmation handling to avoid repeated zero-line events.
- **Parameters/profiles:** `series_A`, `series_B`, `sampling`, `cross_rule`, `close_confirmation`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter, exit/management prompt.
- **Market/data constraints:** Derived values can differ by feed, smoothing method, price input, and intrabar updating.
- **Transfer notes:** Portable if source data and calculation are explicit.
- **Evidence/status:** The familiar MA instance is described at https://www.britannica.com/money/golden-cross-vs-death-cross.
- **Uncertainty/variants:** Equality, cross-back, and intrabar versus completed-bar rules differ among platforms.

## threshold-cross — Derived-series threshold crossing

- **Family:** Derived-series operations.
- **Aliases:** level cross; overbought/oversold crossing (indicator-specific); band breach.
- **Definition:** A numeric series moves from one side of a fixed or dynamic threshold to the other.
- **Boundaries:** A threshold is not necessarily a price level; threshold cross does not imply mean reversion or continuation.
- **Observable inputs:** Series values, threshold definition, prior relation.
- **Recognition semantics:** Detect transition in the sign of `series - threshold`, recording upward/downward direction and bar-completion status.
- **Parameters/profiles:** `series`, `threshold`, `static_or_dynamic`, `cross_rule`, `evaluation_mode`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, filter, management prompt.
- **Market/data constraints:** Dynamic bands/thresholds can repaint with later data if not snapshot.
- **Transfer notes:** Portable with calculation provenance.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** “Touch,” “cross,” “close beyond,” and “remain beyond” are distinct operations.

## threshold-reclaim — Derived-series threshold reclaim

- **Family:** Derived-series operations.
- **Aliases:** oscillator reclaim; band re-entry; signal recovery.
- **Definition:** A series returns across a threshold after first being on the opposite side.
- **Boundaries:** It is a two-stage ordered series event, distinct from the first threshold cross and from price-level reclaim.
- **Observable inputs:** Series, threshold, prior loss/cross state.
- **Recognition semantics:** Require recorded threshold loss then an opposite-direction cross/re-entry using a bound timing/close rule.
- **Parameters/profiles:** `series`, `threshold`, `loss_definition`, `reclaim_rule`, `window`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequencing primitive, management.
- **Market/data constraints:** The series’ sampling and update timing must be consistent across both stages.
- **Transfer notes:** Portable with explicit indicator computation.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Some practitioners call any threshold cross a reclaim without requiring the earlier loss.

## regular-divergence-completion — Regular price-series divergence completion

- **Family:** Derived-series operations.
- **Aliases:** bullish divergence; bearish divergence; momentum divergence.
- **Definition:** Price and a paired derived series form opposed relationships between matched pivot pairs, such as lower price low with higher series low.
- **Boundaries:** It is a shape relation, not a prediction or a trigger until the final compared pivot is confirmed; hidden divergence is separate.
- **Observable inputs:** Price pivots, series pivots, time matching/alignment rule.
- **Recognition semantics:** Confirm two relevant price pivots and corresponding series pivots, then test their signed directional relationships; retain pivot confirmation lag.
- **Parameters/profiles:** `series`, `price_pivot_detector`, `series_pivot_detector`, `matching_rule`, `minimum_separation`; all `unresolved` unless source-stated.
- **Eligible roles:** context, trigger, confirmation, filter, exit prompt.
- **Market/data constraints:** Different pivot anchoring and oscillator calculation produce different signals.
- **Transfer notes:** Portable; data/source provenance applies to the input series.
- **Evidence/status:** General definition and the matching-pivot issue: https://www.luxalgo.com/library/concept/regular-bullish-bearish-divergence.
- **Uncertainty/variants:** Some labels use “convergence” for the bullish case; preserve source wording.

## hidden-divergence-completion — Hidden divergence completion

- **Family:** Derived-series operations.
- **Aliases:** continuation divergence; hidden bullish/bearish divergence.
- **Definition:** A price/derived-series pivot relation conventionally described as trend-continuation oriented, such as price higher low paired with lower series low in the bullish variant.
- **Boundaries:** It is not regular divergence and does not prove trend continuation.
- **Observable inputs:** Existing trend model, matched price/series pivots.
- **Recognition semantics:** Establish the required prior trend, then evaluate the source-defined opposite pivot relationship with declared matching rules.
- **Parameters/profiles:** `trend_definition`, `series`, `pivot_rules`, `matching_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** context, confirmation, filter, trigger.
- **Market/data constraints:** Pivot and trend definitions dominate classification.
- **Transfer notes:** Portable with transparent derived-series provenance.
- **Evidence/status:** Example regular/hidden distinction: https://j2t.com/solutions/blogview/divergance.
- **Uncertainty/variants:** Some sources use hidden divergence only for oscillators, others generalize it.

## volume-expansion — Venue-qualified volume expansion

- **Family:** Volume, order flow, and order book.
- **Aliases:** volume surge; relative-volume expansion; participation spike.
- **Definition:** Reported traded volume at a named venue/feed rises above a stated local comparator.
- **Boundaries:** It is not order flow, net buying/selling, nor all-market volume. It does not establish cause or edge.
- **Observable inputs:** Time-bucketed reported volume, venue/feed identity, baseline series.
- **Recognition semantics:** Compare current reported volume to a rolling average, percentile, session profile, or source-defined baseline; store the venue and instrument.
- **Parameters/profiles:** `venue`, `volume_definition`, `baseline`, `threshold`, `session_profile`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, filter, trigger, context transition.
- **Market/data constraints:** CEX volume is exchange-local; spot-FX “volume” is usually broker tick volume, not consolidated traded volume.
- **Transfer notes:** Use exchange-specific crypto spot volume; do not silently substitute FX tick volume for centralized volume.
- **Evidence/status:** Pennant literature commonly mentions volume change but is not evidence of transferability: https://www.investopedia.com/terms/p/pennant.asp.
- **Uncertainty/variants:** Reported volume, tick count, quote volume, and base/quote volume are different measures.

## volume-climax — Venue-qualified volume climax/exhaustion candidate

- **Family:** Volume, order flow, and order book.
- **Aliases:** climactic volume; exhaustion volume; blow-off volume.
- **Definition:** An unusually high reported-volume print near or after an extended directional move, labelled a candidate exhaustion event only under stated follow-through criteria.
- **Boundaries:** High volume alone is not exhaustion, reversal, or a causal participant diagnosis.
- **Observable inputs:** Venue volume, price direction/location, extension model, later path.
- **Recognition semantics:** Detect volume outlier plus bound directional/location context; optionally require subsequent failure, opposite response, or range normalization before using “exhaustion.”
- **Parameters/profiles:** `venue`, `outlier_measure`, `extension_definition`, `confirmation_window`, `exhaustion_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, exit/management prompt, context transition.
- **Market/data constraints:** Requires representative venue volume; not valid as market-wide evidence in spot FX.
- **Transfer notes:** Crypto spot must name CEX/DEX provenance; FX may only support broker-tick-volume proxy claims.
- **Evidence/status:** Gap analysis discusses exhaustion as a high-volume contextual category: https://school.stockcharts.com/doku.php?id=chart_analysis:gaps_and_gap_analysis.
- **Uncertainty/variants:** “Climax” can be continuation absorption rather than exhaustion.

## order-flow-delta-shift — Aggressor volume-delta shift

- **Family:** Volume, order flow, and order book.
- **Aliases:** delta flip; buy/sell delta shift; CVD slope shift (related).
- **Definition:** A change in signed aggressor-initiated buy versus sell volume at a named matching venue/data feed.
- **Boundaries:** It is not total volume, resting-book imbalance, or a claim about all exchanges. It cannot be inferred from ordinary FX candles.
- **Observable inputs:** Trade prints with aggressor-side classification, aggregation intervals, venue/instrument.
- **Recognition semantics:** Calculate per-bucket delta using venue-provided aggressor flags where available; detect sign, slope, or threshold transition under a bound rule.
- **Parameters/profiles:** `venue`, `aggressor_classification`, `bucket`, `delta_measure`, `shift_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, trigger, filter, management transition.
- **Market/data constraints:** Classification is venue-specific; aggregating venues can double count or mask dislocation.
- **Transfer notes:** Applicable to centralized crypto spot only with qualified trade data. Not a native spot-FX primitive absent a specific venue/feed.
- **Evidence/status:** CVD/delta construction and per-venue caveats: https://markettrace.ai/blog/cumulative-volume-delta.
- **Uncertainty/variants:** Tick-rule inferred aggression is not equivalent to exchange side flags.

## order-flow-divergence — Price versus order-flow divergence

- **Family:** Volume, order flow, and order book.
- **Aliases:** CVD divergence; delta divergence; footprint divergence.
- **Definition:** A divergence relation between price pivots and a venue-qualified order-flow series, such as CVD or cumulative delta.
- **Boundaries:** It is not generic indicator divergence because its input requires aggressor classification; it is not evidence of institutional intent.
- **Observable inputs:** Named-venue price, trade-side data, CVD/delta series, matched pivots.
- **Recognition semantics:** Generate the venue-qualified flow series, match its confirmed pivots to price pivots, then apply a stated divergence grammar.
- **Parameters/profiles:** `venue`, `flow_series`, `reset_rule`, `pivot_rules`, `matching_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, trigger, filter, management prompt.
- **Market/data constraints:** CVD reset point and side classification are material; cross-venue aggregation should not be assumed.
- **Transfer notes:** Suitable for named crypto CEX spot venues; not transferable to decentralized Forex spot as a global order-flow fact.
- **Evidence/status:** CVD is a running net of aggressive buys minus sells; caveats at https://markettrace.ai/blog/cumulative-volume-delta.
- **Uncertainty/variants:** A divergence may reflect venue fragmentation rather than broad-market behavior.

## absorption-event — Venue-qualified absorption candidate

- **Family:** Volume, order flow, and order book.
- **Aliases:** passive absorption; iceberg absorption (only with evidence); stalled aggression.
- **Definition:** At a named venue, aggressive flow persists at or near a price while price makes limited progress, consistent with passive opposing liquidity absorbing it.
- **Boundaries:** It is an inference from flow/price behavior, not proof of a particular hidden participant, iceberg order, or future reversal.
- **Observable inputs:** Trade-side data, price response, optional order-book updates, venue identity.
- **Recognition semantics:** Detect sustained signed aggression or high traded volume at a level with limited directional displacement under a stated tolerance; record the evidence rather than causal story.
- **Parameters/profiles:** `venue`, `flow_measure`, `price_progress_tolerance`, `window`, `book_data_requirement`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, trigger, context, management prompt.
- **Market/data constraints:** Requires high-quality venue trade/order-book data; candles and FX tick volume cannot prove absorption.
- **Transfer notes:** Use only for a named crypto CEX spot feed where data supports it; no direct whole-market Forex-spot transfer.
- **Evidence/status:** A neutral absorption/exhaustion distinction is described at https://anomiq.io/blog/absorption-exhaustion/.
- **Uncertainty/variants:** “Absorption” may be diagnosed differently by footprint, DOM, or price-only practitioners.

## order-book-liquidity-change — Venue-qualified displayed-book liquidity change

- **Family:** Volume, order flow, and order book.
- **Aliases:** liquidity pull; book thinning; replenishment; depth imbalance shift.
- **Definition:** A measurable change in displayed resting depth near selected price levels on a named order-book venue.
- **Boundaries:** Displayed depth is not total executable liquidity and does not establish spoofing, intent, or off-book interest.
- **Observable inputs:** Timestamped L2/L3 snapshots or updates, venue, depth bands, price.
- **Recognition semantics:** Compare displayed depth/imbalance across snapshots at declared levels/bands; label withdrawal, addition, or imbalance transition without causal attribution.
- **Parameters/profiles:** `venue`, `book_depth`, `price_band`, `snapshot_interval`, `change_threshold`; all `unresolved` unless source-stated.
- **Eligible roles:** confirmation, filter, trigger, microstructure context.
- **Market/data constraints:** Highly latency-sensitive and venue-specific; cancels and hidden orders limit interpretation.
- **Transfer notes:** Relevant to a named crypto CEX spot book only. Retail spot-FX platforms generally do not expose a consolidated interbank order book.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** “Liquidity” can mean displayed depth, executed volume, or inferred stop clusters; these must not be conflated.

## sweep-reclaim — Sweep–reclaim ordered event

- **Family:** Ordered compound events.
- **Aliases:** raid-and-reclaim; sweep and return; liquidity-sweep reversal sequence.
- **Definition:** An ordered pair in which price first traverses a designated prior extreme/boundary and later reclaims the designated original side.
- **Boundaries:** It is a sequence primitive, not a full strategy, order instruction, or assertion that stops were deliberately targeted.
- **Observable inputs:** Reference/pool proxy, sweep event, reclaim event, timestamps and price path.
- **Recognition semantics:** Require `sweep` before `reclaim`; bind maximum elapsed time and reclaim basis. Preserve whether the sweep reference was a chart-inferred pool.
- **Parameters/profiles:** `reference`, `sweep_basis`, `reclaim_basis`, `maximum_delay`, `same_bar_allowed`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequencing primitive, invalidation transition.
- **Market/data constraints:** OHLC alone cannot order intrabar sweep and reclaim when both occur in a bar.
- **Transfer notes:** Portable as price sequence; no invisible-stop claim is needed for Forex spot.
- **Evidence/status:** SFP guidance explicitly distinguishes a sweep from a sweep that reclaims: https://www.luxalgo.com/library/concept/swing-failure-pattern/.
- **Uncertainty/variants:** Some sources require same-bar close; others permit one to several later bars.

## break-retest — Break–retest ordered event

- **Family:** Ordered compound events.
- **Aliases:** breakout-pullback; break and hold test; breakout retest.
- **Definition:** A specified boundary break followed, after separation, by return to that boundary for a retest.
- **Boundaries:** It does not require the retest to hold or specify subsequent entry; `break–retest–hold` would be a more specific sequence.
- **Observable inputs:** Reference, breakout event, separation, retest event, timestamps.
- **Recognition semantics:** Require a declared break first, then a return interaction after minimum separation; store later hold/rejection/failure separately.
- **Parameters/profiles:** `break_basis`, `minimum_separation`, `retest_basis`, `maximum_delay`, `same_bar_allowed`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequencing primitive.
- **Market/data constraints:** Both the reference and bar/tick source must remain stable over the sequence.
- **Transfer notes:** Portable.
- **Evidence/status:** Breakout/retest sequence description: https://tradefundrr.com/breakout-retest-confirmation.
- **Uncertainty/variants:** “Retest” can mean exact touch, zone revisit, or close back at the level.

## break-retest-hold — Break–retest–hold ordered event

- **Family:** Ordered compound events.
- **Aliases:** confirmed flip; breakout retest confirmation; break-pullback continuation sequence.
- **Definition:** A boundary break followed by retest and then stated evidence that price holds/rejects in the post-break direction.
- **Boundaries:** It is a compound confirmation event, not an entry rule; it remains distinct from a generic S/R flip because it preserves the required order.
- **Observable inputs:** Break event, retest event, post-retest close/path/acceptance measure.
- **Recognition semantics:** Enforce temporal order `break → retest → hold`; bind the final hold definition and timeout, and record failure if price instead reclaims the old side.
- **Parameters/profiles:** `break_basis`, `retest_basis`, `hold_definition`, `sequence_window`, `failure_rule`; all `unresolved` unless source-stated.
- **Eligible roles:** trigger, confirmation, sequencing primitive, management transition.
- **Market/data constraints:** Needs tick data if a single bar contains multiple sequence stages; otherwise mark ordering unresolved.
- **Transfer notes:** Portable; venue-qualified volume/order-flow additions are optional, not implied.
- **Evidence/status:** General breakout/retest confirmation discussion: https://tradefundrr.com/breakout-retest-confirmation.
- **Uncertainty/variants:** Many sources call the retest itself “confirmation”; this candidate reserves confirmation for the explicitly bound final hold.

## Deduplication notes

- `breach`, `close-through`, and `acceptance-beyond-reference` are deliberately separate raw-to-later transitions. `breakout` binds one or more of them to a reference object; it is not a duplicate of any one.
- `liquidity-sweep` is a neutral price traversal of a candidate pool. `stop-run-label` preserves intent-laden vocabulary as a source claim. `swing-failure-pattern` and `sweep-reclaim` add explicit return/reclaim semantics.
- `structure-break` is the neutral superclass. `BOS`, `CHoCH`, and `MSS` remain distinct aliases/profiles because their swing hierarchy, direction, close, and displacement requirements are contested.
- Candlestick objects (`inside-bar`, `NRN`) are not their resolution events (`mother-bar-break`, `NRN-resolution`). Likewise chart-pattern objects are not their boundary/neckline completion events.
- Generic indicator divergence and venue-qualified order-flow divergence are separate because the latter has strict trade-side/venue provenance requirements.

## Unresolved taxonomy questions

1. Should `acceptance` require time-at-price, closes, or both for each data class?
2. What canonical swing model(s), if any, can support reproducible BOS/CHoCH/MSS bindings without pretending their definitions are settled?
3. Should `liquidity-sweep` require a reclaim in STRATS-neutral usage, or should that remain a source-profile choice?
4. How should intrabar event ordering be represented when only OHLC data is available?
5. Which visible-status vocabulary should distinguish `source-stated`, chart-observable inference, venue-measured flow, and unobservable intent claims?
6. Which spot-FX broker tick-volume measures, if any, may be retained as explicitly broker-local confirmation inputs rather than treated as market volume?
