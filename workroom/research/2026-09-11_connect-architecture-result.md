CONNECT architecture sitting — captain brief (2026-09-11)

Path: C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-CONNECT-2026-09-11/
Spine: ARCHITECTURE-SPINE.md  status: final  (lint 0). Memlog: .memlog.md
Brownfield: integration@1b451a8 via git show; checkout unchanged (main).
Paradigm: hexagonal port completion. Local AD-1..AD-5. Parents QMX AD-1..41 and NODE TN-1..25 inherited, not re-derived.
AD-1 fail-closed live selection: explicit roster VenueClientKind; unknown live VenueId refuses (today’s else→CTRADER is a connect bug).
AD-2 honest FX paper: demo + world=live + same live client + submit encode + read-back. Spot FX not skipped.
AD-3 encode in qmf-venue ConnectionManager; qmn.venue sole importer (DEC-0241); no third library; production must call connect_open_api.
AD-4 FTR-01 closed: CT-20 kinds position-read-back / balance-read-back journal as CT-13 data quality; no eighth type. [ASSUMPTION A3]
AD-5 crypto is plurality (same port, later CT-18 + impl); no fourth V1 kind and no exchange pick this sitting.
Conflicts surfaced, not overridden: PRD §7 node-runtime OOS vs DEC-0259; PRD §7 forex-only vs later crypto; DEC-0247 “observation” vs CT-13 seven (interpreted as CT-20 kind); TN-11 THREE vs L22 (scoped).
Out: Book/BMS/sizing/MIS redesign, UI, STRATS, documentation-factory, epics, Grok factory.
Next skill: /documentation-factory in a NEW session, then bmad-create-epics-and-stories, then factory lane. Do not run those here.
