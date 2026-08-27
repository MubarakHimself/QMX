#!/bin/bash
set -e
D="/mnt/c/Users/Mubarak/AppData/Local/Temp/claude/C--Users-Mubarak-Desktop-QMX/d0fe034d-001a-4a56-8823-d14f95739a7d/scratchpad/battery/mutmut"
cp /root/mutmut_results.txt "$D/mutmut_results_survived_only.txt"
cp /root/mutmut_results_all.txt "$D/mutmut_results_all.txt"
cp /root/survivors_diffs.txt "$D/survivors_diffs.txt"
sort /root/survivors_summary.txt > "$D/survivors_summary.tsv"
cp /root/mutmut_run.log "$D/mutmut_run.log"
cp /mnt/c/Users/Mubarak/Desktop/QMX-worktrees/qa-mutmut/packages/qmf-core/pyproject.toml "$D/qmf-core_pyproject_used.toml"
echo COPY_OK
ls -la "$D"
