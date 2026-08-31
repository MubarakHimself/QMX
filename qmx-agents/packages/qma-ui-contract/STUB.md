# qma-ui-contract — deferred stub (GAP-0081; AR-Q08)

This directory is an **explicit deferred exclusion**.

It ships **no** UI SDK, **no** UI contribution point, and **no** UI package
behavior. The daemon-to-UI wire contract binds now in `qma-wire` (CT-40);
presentation architecture, Rust extension technology, UI SDK surfaces, and UI
plugin packaging wait for their own session once the daemon API is live and
stable (DEC-0333).

Do not add `pyproject.toml`, `src/`, or workspace membership here in this
increment.
