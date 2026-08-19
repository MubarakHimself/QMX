---
id: 006
title: Spotware app + broker selection
label: wayfinder:task
status: open
assignee:
blocked-by: []
---

## Operator input (2026-08-17 evening)

Broker choice: **IC Markets**, most likely on their **swap-free (Islamic) account**. Implications to verify during setup: swap-free accounts usually replace overnight swap with an administration fee after N days — get the exact fee schedule in writing, because the ledger's `financing` column must model IT rather than swap; confirm IC Markets cTrader demo + live both expose Open API; measure their real tick-history retention.

## Question

Unblock the trader hat's longest external pole: submit the Spotware Open API application registration (review time unknown — submit ASAP, D11); pick two candidate cTrader brokers and verify Open API access on demo AND live accounts; measure each broker's real tick-history retention (research file 02 says per-request limits are documented but retention is broker-specific); establish whether cTrader trendbars are BID-derived or mid-derived (UNVERIFIED across files 02/05 — affects every backtest-to-live comparison). Mubarak performs the sign-ups; Claude prepares exact steps and verification scripts when he starts.
