Separate zero-authority observability stack (TN-15 / DEC-0200 / DEC-0212 / AR-83).

This directory is the ONLY VPS surface allowed to use containers. The trading
node itself remains a plain systemd service under qmn/deploy/systemd/ and must
run and pass with this entire stack stopped — losing the stack loses visibility
and nothing else.

Layout
------
  compose.yml                 Pinned Prometheus/Grafana/Loki/Promtail compose
  stack.py                    Inventory, pins, and check-mode inspection
  prometheus/                 Scrape config + alert-rule seeds (no trading budgets)
  loki/                       Loki config (loopback listen)
  promtail/                   Read-only journal namespace shipper
  grafana/provisioning/       Datasource + dashboard providers
  grafana/dashboards/         Versioned dashboard-as-code seeds
  journald/qmn-namespace.conf Journal namespace notes / ACL contract
  quota.txt                   /var/lib/qmx-observability quota declaration

Zero-authority footprint
------------------------
  * Unit:        qmx-observability.service (NOT a node unit)
  * Account:     qmxobs (distinct non-qmx)
  * Storage:     /var/lib/qmx-observability (own quota)
  * Network:     network_mode: host; every listen address 127.0.0.1
  * Scrape:      http://127.0.0.1:8787/metrics (evidence channel) only
  * Logs:        LogNamespace=qmn via Promtail — never the system journal
  * Credentials: grafana-admin + optional log-shipper-token only
                 (declared fourth secret holder; holds NOTHING the node holds)
  * Authority:   none — no write path into the node, no powers, no doors

Pinned images (never floating tags)
-----------------------------------
  prom/prometheus:v3.5.5
  grafana/grafana:13.1.4
  grafana/loki:3.7.7
  grafana/promtail:3.6.11

Registered as external tools in DEPENDENCIES.md. Grafana/Loki/Promtail images
are AGPL process-isolated containers — never linked into qmn (operator-named
stack, DEC-0212).

Do not deploy to a live VPS from this worktree. `just node-install` plans the
host steps in check mode; live apply is an ops-principal act on the VPS.
