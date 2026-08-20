# Spotware GitHub org inventory (2026-08-20)

Research agent report against https://github.com/spotware (37 repos, both pages read). Feeds GAP-0035 (secrets) and GAP-0038 (adapter contract). Research protocol: findings presented, NOT adopted — the venue sitting ratifies. Claims graded [primary] (read from the repo/file) vs [inferred].

## Headline verdict

**The official Python SDK (OpenApiPy / PyPI `ctrader-open-api`) imposes Twisted's reactor as a hard, pinned runtime dependency** — verbatim from `pyproject.toml` [primary, https://raw.githubusercontent.com/spotware/OpenApiPy/main/pyproject.toml]:

```
python = "^3.8"
Twisted = "24.3.0"
pyOpenSSL = "24.1.0"
protobuf = "3.20.1"
requests = "2.32.3"
inputimeout = "1.0.4"
```

Its README drives the process with `reactor.run()` and returns Twisted Deferreds [primary]. Not asyncio; it owns the process's concurrency model. Under AD-6's ban on dependencies imposing their own event loop, **the vendor SDK is not legal as a runtime dependency**. License (MIT) is fine; the reactor is the blocker. Usable path: consume the protobuf `.proto` source directly and write the transport in-house (consistent with build-our-own, DEC-0013).

## openapi-proto-messages — the protocol source of truth

- https://github.com/spotware/openapi-proto-messages — **MIT** [primary], not archived, 12 open issues.
- Four proto files at root: `OpenApiCommonMessages.proto`, `OpenApiCommonModelMessages.proto`, `OpenApiMessages.proto`, `OpenApiModelMessages.proto` [primary].
- **Versioning: sequential integer release tags** (…86, 88, 89, 90, 91; underscore patch suffixes like `86_2`) — not SemVer, not dated; per-release changelogs live on the GitHub Releases page, no in-tree CHANGELOG [primary]. Latest observed tag 91 (new PnL-change subscribe requests; year [inferred] 2025).
- Consequence for QMF: protocol version pinning/fingerprinting must carry the integer tag scheme; the Releases feed is the diff-able change record — the Help Centre HTML is not.

## OpenApiPy / PyPI `ctrader-open-api` — official Python SDK (reference only)

- https://github.com/spotware/OpenApiPy — MIT [primary]; author Spotware (connect@spotware.com) on PyPI [primary].
- Concurrency: Twisted reactor + Deferreds, NOT asyncio [primary] — the disqualifying fact.
- Staleness [primary]: GitHub tags 0.9.1 (May 2022) → 2-year gap → 0.9.2 (Jun 2024) → 0.9.3 (Aug 2024); **PyPI 0.9.3 is YANKED**, installable release is 0.9.2 (Jun 2024) — ~2 years stale at this sitting. Not archived; treat as maintenance-mode.
- Bundles compiled protobuf messages inside the package; pins `protobuf 3.20.1` (an old pin — a compatibility hint only; we compile the .proto against a current runtime ourselves).
- **No standalone pip-installable pure-messages Python package exists** from Spotware [inferred from PyPI + repo listing]; a Go package exists (tag 86 note), not Python.

## OAuth / token lifecycle in official examples

**Essentially nothing to inherit** [primary, OpenApiPy README]: samples show application-level auth (`ProtoOAApplicationAuthReq`) with client id/secret inline as literals; no access-token, refresh-token, storage, or rotation code anywhere. The OAuth authorization-code + refresh flow is documented on the Help Centre but has no reference implementation in the org. **GAP-0035 owns storage and rotation entirely — nothing to borrow.**

## Other findings

- FIX API repos exist (`cTraderFixPy` Python MIT; C#/.NET samples) — noted only, out of scope.
- Legacy `connect-*` JS/TS family (older Open API generation): wrong language, near-zero relevance; reads as superseded [inferred].
- `OpenAPI.Net` (C#, MIT) and Java examples (Apache-2.0): reference implementations only.
- `ctrader-skills` (Python, "agent skills for the cTrader platform", no license badge) — worth a later look; license unconfirmed.
- License posture org-wide: everything badged is MIT or Apache-2.0; **no GPL/AGPL/LGPL observed** [primary]. Repos with no license badge (`connect-js-codec`, `connection-adapter`, etc.) = all-rights-reserved, do not vendor, until confirmed.
- No org repo generates help.ctrader.com (proprietary CMS [inferred]); SDK doc sites are GitHub Pages from the SDK repos. Interactive reference at openapi.ctrader.com; `m-ahmadi.github.io/ctoa/` is community, not Spotware.
- No repo carries GitHub's `archived` flag [primary]; staleness is de-facto, not declared.

## Bottom line for the adapter design (candidate rulings for GAP-0038)

1. Integrate against `openapi-proto-messages` (MIT, four proto files), compiled in-house against a current protobuf runtime.
2. OpenApiPy: reference implementation only, never a runtime dependency (AD-6 event-loop rule).
3. Pin/track protocol version by integer release tag (e.g. "91"); watch the Releases feed for change tracking.
4. GAP-0035 designs token storage/rotation from scratch — no vendor pattern exists.
