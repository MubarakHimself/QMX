# QMN operations toolkit recipe bodies (TN-16 / AR-79 / DEC-0202).
# DevOps only — never a trading control. No recipe places, cancels, amends,
# flattens, promotes, activates, settings-edits, resurrects, attests, or
# countersigns. Recipes needing live node state use the ops principal over
# the powers channel; node-install / node-switch / node-rollback are
# privileged host acts that touch no door.
#
# Paths are rooted at the importing justfile (repo root).

qmn_deploy := justfile_directory() / "qmn" / "deploy"
qmn_values := qmn_deploy / "fixtures" / "render-values.json"

# Idempotent Ubuntu install planner (check mode by default).
# Live --apply is refused off-VPS; never SSHes to Contabo from this recipe.
node-install *ARGS:
    uv run python "{{qmn_deploy}}/install.py" --check-mode --values "{{qmn_values}}" {{ARGS}}

# Release switch / rollback (Story 25.18). Check mode by default; live --apply
# is refused off-VPS. Fixture-root apply is for CI/tests only.
node-switch *ARGS:
    uv run python "{{qmn_deploy}}/switch.py" node-switch --check-mode {{ARGS}}

node-rollback *ARGS:
    uv run python "{{qmn_deploy}}/switch.py" node-rollback --check-mode {{ARGS}}

# First-deployment demo shape (Story 28.2 / TN-9/16). Check mode by default.
# Live --apply is refused off-VPS; never procures a VPS or opens live
# credentials. Book routing PAPER for the whole first-deployment window.
node-demo-deploy *ARGS:
    uv run python "{{qmn_deploy}}/demo.py" --check-mode {{ARGS}}

# Pinned ubuntu-24.04 lane contract suite (NFR-18/21 compensators).
node-ci-lane *ARGS:
    uv run python "{{qmn_deploy}}/ci_lane.py" {{ARGS}}

# Restricted secrets wizard (Story 27.1 / TN-12). Check-mode by default.
# Never SSHes to a live VPS; --apply without --fixture-root is refused.
# Streams stdin into systemd-creds encrypt --with-key=host; never argv/file/echo.
node-secrets-provision *ARGS:
    uv run python "{{qmn_deploy}}/secrets_provision.py" --check-mode {{ARGS}}

# History bootstrap (Story 27.2 / TN-13). Check-mode by default.
# Never downloads from the live Dukascopy datafeed; --apply without
# --fixture-root is refused. Fixture apply writes injected hour payloads.
node-data-bootstrap *ARGS:
    uv run python "{{qmn_deploy}}/data_bootstrap.py" --check-mode {{ARGS}}

# Credential-free recorded-day decision diff (Story 27.7 / TN-21).
# Check-mode by default. Spawns python -m qmn.replay outside the node.
# Never resolves a secret, never opens a live sink, never trades.
node-replay *ARGS:
    uv run python "{{qmn_deploy}}/replay.py" --check-mode {{ARGS}}

node-config-init *ARGS:
    @echo "node-config-init: reserved"

node-config-validate *ARGS:
    @echo "node-config-validate: reserved"

node-config-explain *ARGS:
    @echo "node-config-explain: reserved"

node-notify-test *ARGS:
    @echo "node-notify-test: reserved (ops principal notify_test power)"

node-hub-publish *ARGS:
    @echo "node-hub-publish: reserved (ops principal hub_publish power)"

node-host-loss-restore *ARGS:
    @echo "node-host-loss-restore: reserved (restore_drill_run power)"

# Lifecycle campaign planner (Story 28.4 / TN-4/14/19/23). Check mode by
# default. Never applies a live VPS firewall or a live bucket restore.
# Campaign proofs run as qmn.host tests; this recipe never trades.
node-lifecycle-campaign *ARGS:
    uv run python "{{qmn_deploy}}/lifecycle.py" --check-mode {{ARGS}}

# Powers/secret probes plus fixture unit/network/upgrade inspection
# (Story 28.4 / QMX-F045/F064). Check mode by default. Never applies a
# live VPS firewall. DevOps recipes remain unable to trade.
node-security-probes *ARGS:
    uv run python "{{qmn_deploy}}/security_probes.py" --check-mode {{ARGS}}
