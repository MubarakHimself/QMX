# Stage A investigation inputs

Investigators were read-only explore agents (could not write). Their full findings were returned to the lead and distilled into the spine. Condensed notes:

| File | Source |
|---|---|
| `../RECON-RETURN.md` | Freshness vs 8510c03 / 270e992 |
| `opportunities-journeys.md` | CIS clustering + OP-NEW-01..18 |
| Lead-written companions in parent folder | contracts, journeys, copilot, stack, conflicts |

Key evidence paths at `270e992`:

- `qmb/src/qmb/config/compiler.py` — Book+BMS required on sanctioned compile
- `qmn/src/qmn/venue/port.py` — three VenueClientKind
- `qml/src/qml/research/` + `qml/src/qml/host/research_store.py` — mill present
- `qma/daemon/discovery/federated.py` — two-rail concatenate
- `qma/daemon/taskgraph/execution.py:172` — pairwise back-edge only
- `qma/daemon/taskgraph/dispatcher.py:118` — TaskGraphStore in-memory, no edges
- `qma/core/ontology/records.py:169` — Session is execution container
- `qma/core/ontology/desks.py` — Role “Product Manager”
