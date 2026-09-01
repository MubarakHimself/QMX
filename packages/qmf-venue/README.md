# qmf-venue

The venue-neutral seam and cTrader translation. An edge module: it imports only
`qmf-core`, and nothing in the seven roster packages or in `qmb`/`qml` imports
it. The trading node's `qmn.venue` subpackage is the one sanctioned importer and
wirer (DEC-0241).

`qmf-venue` imports as `qmf.venue` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer
lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Public surface is the four venue contracts on qmf-core nouns, plus the
connection manager and first cTrader adapter:

| Contract | Module | Role |
|---|---|---|
| [CT-18](../../docs/contracts/ct-18-venue-capabilities.yaml) | `qmf.venue.capabilities`, `qmf.venue.observation`, `qmf.venue.probe` | Static capability declaration + per-`(VenueId, account)` venue-observation profile; first-connection verify-or-refuse |
| [CT-19](../../docs/contracts/ct-19-venue-command.yaml) | `qmf.venue.commands`, `qmf.venue.blocking` | Five command kinds (`place_order`, `cancel_order`, `close_position`, `close_all`, `amend_protection`); four-outcome law; UNKNOWN stream block + explicit `resolve_unknown` |
| [CT-20](../../docs/contracts/ct-20-venue-event.yaml) | `qmf.venue.events` | Record-before-interpret inbound events; read-time order-state fold; on-demand reconciliation (`reconciled \| drift \| unknown \| out-of-lookback`) |
| [CT-21](../../docs/contracts/ct-21-venue-secret-session.yaml) | `qmf.venue.connection` | Opaque `SecretRef` / session seam; account bindings; sole in-memory secret-value holder |

Canonical component spec: [`docs/components/qmf-venue.md`](../../docs/components/qmf-venue.md).
Reference usages: [`examples/account_binding_usage.py`](examples/account_binding_usage.py)
(CT-21) and [`examples/observation_events_usage.py`](examples/observation_events_usage.py)
(CT-20). Build, lint, type-check, and test through the workspace `poe` tasks —
never in isolation.

## ConnectionManager authority

`ConnectionManager` (`qmf.venue.connection`) is the sole owner of venue sessions
and the single named in-memory holder of secret *values* for a session's
lifetime (DEC-0136, DEC-0138, DEC-0196). It:

- holds the venue-path `WriterId` at `(machine, adapter role, VenueId, account)`
  granularity — the same unit as the command stream;
- receives a composition-root-injected `SecretStore` and calls the injected
  core sinks (`ObservationSink`, `JournalSink`, `RecordSink`) synchronously;
- never returns a plaintext secret or `SecretValue`; rotation is
  store-before-discard;
- blocks the command pipe on a command-path `storage failure` while the sensing
  pipe stays unaffected;
- owns the cTrader Open API TLS transport (port 5035, length-prefixed
  `ProtoMessage` framing over the pinned `registry:venue_protocol_artifact`
  tag) when the parent accepts the async exemption below — no Spotware SDK, no
  Twisted, no second event loop, no second connection manager.

No other component constructs a venue client. Duty scheduling stays
application-side: the adapter declares schedulable duties; the node runs them.

## Named async exemption — `qmf.venue.connection`

The roster async-conformance ban gains exactly one named exemption:
`ASYNC_CONFORMANCE_EXEMPTION = "qmf.venue.connection"` (DEC-0243 / L8). That
module's `ConnectionManager` may hold the asyncio socket, session, and single
in-memory venue secret value on the loop the trading node injects; it owns no
loop and schedules nothing itself — the one delegated impurity.

If the parent **refuses** that exemption, the same transport contract lands in
the node's `qmn.venue.ctrader` subpackage instead. This README records both
placements and does not choose the disposition; the formal parent disposition
and locus resolution live at the `qmn.venue` boundary (DEC-0243, DEC-0196).

## `qmn.venue` composition boundary

Default-deny stands inside the roster. Applications never import `qmf-venue`
except the trading node through `qmn.venue` (DEC-0241):

- `qmn.venue` is the writable import and wiring boundary — the composition root
  constructs the adapter there;
- every other `qmn` module receives only `VenueClientPort` and CT-19/CT-20
  shapes;
- `qmb` and `qml` keep their `qmf-venue` ban;
- nothing imports `qmn`.

The node-minted `VenueClientPort` sits over CT-19/CT-20 shapes with V1
implementations selected by `(world, VenueId)`. Realizing that port seam inside
`qmf-venue` remains a recorded-not-applied parent annotation (DEC-0242) — this
package is not amended to carry it.
