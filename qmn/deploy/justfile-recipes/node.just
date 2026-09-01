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

# Placeholder surfaces for later stories (25.18 switch/rollback, secrets, …).
# Bodies stay check-mode / no-op until those stories land; names are reserved
# on the allow-list in qmn/deploy/boundary.py.

node-switch *ARGS:
    @echo "node-switch: reserved (Story 25.18); refusing host mutation from this worktree"

node-rollback *ARGS:
    @echo "node-rollback: reserved (Story 25.18); refusing host mutation from this worktree"

node-secrets-provision *ARGS:
    @echo "node-secrets-provision: reserved; seal with systemd-creds encrypt --with-key=host"

node-data-bootstrap *ARGS:
    @echo "node-data-bootstrap: reserved (history bootstrap)"

node-replay *ARGS:
    @echo "node-replay: reserved"

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
