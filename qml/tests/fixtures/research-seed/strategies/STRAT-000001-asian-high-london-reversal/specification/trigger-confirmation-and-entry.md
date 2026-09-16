# Trigger, confirmation, and entry (human trigger / entry lenses)

**LAYOUT-DEMO.** **Trigger ≠ order.** Sweep + engulfing-completion are trigger events. Confluence is graph composition (`ALL`), not a primitive class.

## Trigger

1. `liquidity-sweep` (pre-trigger in the sketch)
2. bullish `engulfing-completion` (synchronous)

## Confirmation / confluence

The four operands are composed with `ALL` in `logic/graph.yaml`. There is no separate "confluence" primitive.

## Entry semantics

| Topic | Value |
|---|---|
| action | `enter` (long) — not an order type |
| order type | `unresolved` |
| price basis | `unresolved` |
| delay / expiry | `unresolved` |
