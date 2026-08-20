---
review: currency
target: ARCHITECTURE-SPINE.md — the venue increment (AD-26, AD-27, AD-28, the AD-8/AD-9
  amendments, and the new Stack row for Spotware openapi-proto-messages), plus the
  companion ctrader-venue-facts.md (QMF V1 Foundation, architecture-QMX-2026-08-19)
reviewer-method: GitHub REST API (gh api, authoritative, non-summarized) for release
  tags and raw file contents; direct curl + Python JSON parse for PyPI; WebFetch
  against help.ctrader.com primary docs and raw.githubusercontent.com proto source
  for live-doc spot-checks
reviewed: 2026-08-20
---

# Currency & Reality-Check Review — Venue Increment (AD-26/27/28) — ARCHITECTURE-SPINE.md

## Scope

Follow-up to `review-currency.md`, `review-currency-2.md`, `review-currency-3.md`. This
pass targets tonight's venue increment only: AD-26 (secret lifecycle), AD-27 (commands
and the uncertainty law), AD-28 (adapter contract and capability discovery), the AD-8/
AD-9 amendments that lean on cTrader venue facts, and the new Stack row for Spotware
`openapi-proto-messages`. Six specific claims were checked against the live web /
authoritative APIs, not training data:

1. Spotware `openapi-proto-messages` latest release tag (spine: integer tags, latest
   observed 91, verified 2026-08-20).
2. TA-Lib 0.7.1 (C + Python wrapper) and duckdb 1.5.5 Stack rows — spot-check only
   (full check already on record in `review-currency-3.md`).
3. cTrader venue facts the ADs lean on: 50/5 req/s per connection; demo/live separate
   hosts requiring two connections; refresh-token-never-expires; heartbeat 10s.
4. AD-28's claim that vendor SDK OpenApiPy is Twisted-bound and reference-only.
5. Whether the corpus's own grading (primary-doc / primary-proto / staff-forum /
   community-inference) holds up where the spine leans on it, and whether any
   increment claim was asserted without that discipline.

## Verdict

**Every claim checked in the venue increment holds up as written — the Spotware tag
(91), the TA-Lib/duckdb rows, all four spot-checked cTrader venue facts, and the
OpenApiPy/Twisted claim are all confirmed current and accurate against live primary
sources as of 2026-08-20.** No claim found false or stale. This increment's sourcing
discipline is the best of the four currency passes to date: `ctrader-venue-facts.md`
and its four upstream research files grade every claim by evidence tier, and the spine
correctly refuses to promote staff-only/inference-grade claims (17:00 NY daily
boundary; BID-basis of trendbars) to invariant status — it treats them as
broker-scoped, empirically-verified-at-connection facts instead. One methodology gap
found (M1, MEDIUM): the corpus's own rate-limit research file records the 50/5 req/s
figures as "NOT re-tested this pass" in one document while a sibling document
confirms them with a primary citation — both exist in the folder, the spine leans on
the correct (confirmed) one, but a reader hitting the first file alone would be
misled. No LOW/informational notes rise to spine-text corrections.

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

**M1 — Internal corpus inconsistency on the 50/5 req/s citation status (not a spine
error, but worth closing).**
`ctrader-primary-verification.md` (the seven-question re-verification pass), finding
6, states explicitly: *"The 50 req/s and 5 req/s figures were not re-tested in this
pass and carry no citation here — treat them as carried-forward, unverified."* A
separate, later document, `ctrader-rate-limits-research.md` ("re-research,
2026-08-20"), *does* carry a primary citation for the same figures, verbatim from
`help.ctrader.com/open-api/` ("Rate limiting" box). `ctrader-venue-facts.md` (the
consolidation sheet the spine cites) correctly draws on the confirmed document and
grades A4 as primary-doc. **The spine's claim is sound** — I independently re-fetched
`help.ctrader.com/open-api/` today and got the identical verbatim text (50
non-historical / 5 historical, both "per connection"). The only issue is that the
corpus itself contains one stale "unverified, no citation" note sitting alongside a
confirmed one on the same fact, which could mislead a future reader who opens
`ctrader-primary-verification.md` without also checking the later rate-limits pass.
Recommend a one-line addendum in `ctrader-primary-verification.md` finding 6 pointing
to `ctrader-rate-limits-research.md` as the superseding confirmation, or folding the
note into `ctrader-venue-facts.md`'s own provenance trail.

### LOW / informational (no spine correction needed)

**L1 — Genuine primary-source contradiction on heartbeat interval, correctly resolved
by the spine (not a currency defect).**
Independently re-verified both sides today:
- FAQ (`https://help.ctrader.com/open-api/faq/`): *"make sure that you send a
  heartbeat to the server at least once every 10 seconds."*
- Proto comment (`OpenApiCommonMessages.proto`, fetched raw from
  `raw.githubusercontent.com/spotware/openapi-proto-messages/main/`):
  *"Open API client can send this message when he needs to keep the connection open
  for a period without other messages longer than 30 seconds."*
These are two live primary sources stating different numbers. AD-8/A8 in
`ctrader-venue-facts.md` already flags this as a contradiction and adopts the
stricter 10s bound as the safe figure — the correct call, not a currency gap.

**L2 — Spotware protocol repo has had no new release in over two years relative to
story-date.**
Confirmed via `gh api repos/spotware/openapi-proto-messages/releases`: Release 91,
tagged 2024-07-15, remains the newest entry (no pagination cutoff — full history back
to v7.4/2021 enumerated). The spine's "latest observed 91, verified 2026-08-20" is
accurate today. Flagging only as a watch item: AD-28's re-verification gate fires on
"a tag change," and with the upstream repo now over two years quiet, that gate may
simply never fire again before V1 ships — not a defect, just worth knowing the trigger
condition may be dormant rather than exercised.

**L3 — "Refresh token never expires" carries a load-bearing caveat that the spine
correctly preserves, not a simplification.**
Live FAQ quote confirmed verbatim today: *"The refresh token is valid forever until
you use it to refresh an access token or if you re-authorise your cTrader ID and
trading accounts."* AD-26's compromise-recovery clause ("cTID re-authorization
invalidates all outstanding refresh tokens") is drawn from this same sentence, not a
separate unsourced claim — the two halves of one primary quote are correctly split
across "never expires" (Stack/AD-9 territory) and "invalidated by re-auth" (AD-26
compromise drill). No gap.

## Verification detail

**F1 — Spotware `openapi-proto-messages` latest release tag = 91. Confirmed via
GitHub API directly (not a summarized page fetch).**
```
gh api repos/spotware/openapi-proto-messages/releases --paginate
91   Release 91    2024-07-15T05:42:52Z   <- latest
90   Release 90    2024-04-08T08:29:52Z
89   Version 89    2024-01-29T07:53:43Z
88   Release 88    2023-09-26T05:19:48Z
...  (down to v7.4, 2021)
```
Matches the Stack row exactly: "integer release tags (latest observed 91, verified
2026-08-20)." A first WebFetch pass against the HTML releases page independently
agreed (same tag, same date), but the GitHub API call is the authoritative check here
since it isn't subject to a summarizing model's read of a JS-rendered page.
Source: `gh api repos/spotware/openapi-proto-messages/releases`

**F2 — TA-Lib 0.7.1 (C + Python wrapper) and duckdb 1.5.5 — spot-check confirms both
still current; full analysis already on record.**
- PyPI JSON (`pypi.org/pypi/ta-lib/json`): `info.version` = `0.7.1`, latest in the
  release list (0.6.3 → 0.7.1).
- GitHub (`gh api repos/TA-Lib/ta-lib/releases`): `v0.7.1`, 2026-07-03, is the latest
  tag.
- PyPI JSON (`pypi.org/pypi/duckdb/json`): `info.version` = `1.5.5`; pre-release
  `1.6.0.dev*` builds exist but nothing stable past 1.5.5.
- GitHub (`gh api repos/duckdb/duckdb/releases`): `v1.5.5`, 2026-07-22, is the latest
  stable tag; no `v2.0` tag exists.
Both rows remain accurate. `review-currency-3.md` already carries the full licence /
streaming-semantics / DuckDB-v2.0-preview analysis for these two rows — not repeated
here, only reconfirmed current.
Sources: `pypi.org/pypi/ta-lib/json`, `pypi.org/pypi/duckdb/json`,
`gh api repos/TA-Lib/ta-lib/releases`, `gh api repos/duckdb/duckdb/releases`

**F3 — cTrader venue fact: 50 req/s non-historical / 5 req/s historical, per
connection. Confirmed live, independent of the corpus's own citation.**
Direct fetch of `https://help.ctrader.com/open-api/` today returned the identical
verbatim text the corpus cites: *"You can perform a maximum of 50 requests per second
per connection for any non-historical data requests... 5 requests per second per
connection for any historical data requests."* Matches spine AD-27/AD-28 and
`ctrader-venue-facts.md` A4 exactly. (See M1 for the one corpus-hygiene note.)

**F4 — cTrader venue fact: demo and live environments require two separate
connections. Confirmed live.**
Direct fetch of `https://help.ctrader.com/open-api/proxies-endpoints/` today: *"Demo
and live environments are fully separated. If you connect to a live endpoint, you
cannot use demo accounts in your application, and vice versa... you would need to
establish and maintain two separate connections."* Matches AD-28's "Sessions and
paired demo: simultaneous environments follow the venue's declared topology (cTrader:
demo + live require two connections)" exactly.

**F5 — cTrader venue fact: refresh token has no expiration period. Confirmed live.**
Direct fetch of `https://help.ctrader.com/open-api/faq/` today: *"The refresh token
is valid forever until you use it to refresh an access token or if you re-authorise
your cTrader ID and trading accounts."* Matches the Stack-adjacent AD-26 token
lifecycle framing and the compromise-recovery clause (see L3).

**F6 — cTrader venue fact: heartbeat interval. Confirmed live, contradiction verified
on both sides (see L1).**
FAQ: 10s minimum. Proto comment (`OpenApiCommonMessages.proto`, raw GitHub fetch):
30s tolerance stated by the server side. The spine/`ctrader-venue-facts.md` A8
correctly documents this as a primary-vs-primary contradiction and adopts 10s as the
safe bound — verified as the right call, not an unverified assertion.

**F7 — AD-28's claim that vendor SDK OpenApiPy is Twisted-bound, reference-only.
Confirmed via direct pyproject.toml fetch.**
`gh api repos/spotware/OpenApiPy/contents/pyproject.toml` (base64-decoded, raw
file content, not a summarized fetch):
```toml
[tool.poetry.dependencies]
python = "^3.8"
Twisted = "24.3.0"
pyOpenSSL = "24.1.0"
protobuf = "3.20.1"
requests = "2.32.3"
inputimeout = "1.0.4"
```
`Twisted` is a direct, pinned, non-optional dependency of `ctrader_open_api` (the
package name in the same file). This confirms AD-6's event-loop-imposing-dependency
prohibition is correctly the reason OpenApiPy is excluded as a runtime dependency, and
AD-28's characterization ("OpenApiPy is Twisted-bound, reference-only") is accurate,
not asserted from memory. Also independently corroborated by
`spotware-org-inventory.md`'s own finding that OpenApiPy's README samples show
inline application-credential literals with no token-storage/rotation code worth
borrowing — consistent with "reference-only."
Source: `gh api repos/spotware/OpenApiPy/contents/pyproject.toml`

## Summary Table

| Claim (spine/companion text) | Verified value | Status |
| --- | --- | --- |
| Spotware `openapi-proto-messages` latest tag = 91 | Release 91, tagged 2024-07-15, still latest | Confirmed |
| TA-Lib 0.7.1 (C + wrapper), current | 0.7.1 latest on PyPI + GitHub | Confirmed |
| duckdb 1.5.5, current stable | 1.5.5 latest on PyPI + GitHub; 1.6.0 only in dev pre-release | Confirmed |
| cTrader 50/5 req/s per connection | Verbatim match, help.ctrader.com/open-api/ | Confirmed |
| cTrader demo/live require two connections | Verbatim match, proxies-endpoints page | Confirmed |
| cTrader refresh token never expires (until used/re-authed) | Verbatim match, FAQ | Confirmed |
| cTrader heartbeat 10s (adopted safe bound) | FAQ says 10s, proto says 30s — genuine contradiction, spine correctly picks stricter figure | Confirmed as correctly resolved |
| OpenApiPy is Twisted-bound, reference-only | pyproject.toml pins `Twisted = "24.3.0"` as a direct dependency | Confirmed |
| Corpus citation hygiene on 50/5 figures | One doc says "unverified, no citation," a sibling doc supplies the citation the spine actually relies on | MEDIUM note (M1), no spine correction needed |
