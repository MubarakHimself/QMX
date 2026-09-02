Operations toolkit recipe bodies for the root justfile's `just node-…` recipes.
DevOps only: never a trading control, never a product CLI, never a console script.
Recipes must not import qmn.host or qmn.doors.api and must never place, cancel,
amend, flatten, promote, or activate (AR-79; DEC-0202; DEC-0211).

`node.just` is imported by the root justfile.
- `just node-install` — check-mode planner in qmn/deploy/install.py
- `just node-switch` / `just node-rollback` — release flip planner in
  qmn/deploy/switch.py (Story 25.18); check mode by default; --fixture-root
  for CI/tests; live --apply refused off-VPS
- `just node-ci-lane` — pinned ubuntu-24.04 compensator suite in
  qmn/deploy/ci_lane.py
- `just node-secrets-provision` — restricted wizard in
  qmn/deploy/secrets_provision.py (Story 27.1); check mode by default;
  --fixture-root for CI/tests; live --apply refused off-VPS; stdin into
  systemd-creds encrypt --with-key=host; never argv/file/echo/log

Fixtures live under qmn/deploy/fixtures/ (render values + upgrade-policy).
This story never SSHes to Contabo.
