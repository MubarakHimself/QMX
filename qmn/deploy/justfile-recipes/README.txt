Operations toolkit recipe bodies for the root justfile's `just node-…` recipes.
DevOps only: never a trading control, never a product CLI, never a console script.
Recipes must not import qmn.host or qmn.doors.api and must never place, cancel,
amend, flatten, promote, or activate (AR-79; DEC-0202; DEC-0211).

`node.just` is imported by the root justfile. `just node-install` runs the
check-mode planner in qmn/deploy/install.py (fixtures under
qmn/deploy/fixtures/). Live --apply is refused off-VPS; this story never SSHes
to Contabo.
