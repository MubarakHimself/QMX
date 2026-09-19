import json
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX\workroom\research\2026-09-15_mis-fullread-ideas")
PACKS = ROOT / "packs"

def load(pid):
    return json.loads((PACKS / f"{pid}.json").read_text(encoding="utf-8"))

wave_a = [
    "machine_learning_000",
    "machine_learning_001",
    "statistics_and_analysis_000",
    "statistics_and_analysis_001",
    "statistics_and_analysis_002",
    "statistics_and_analysis_003",
    "statistics_and_analysis_004",
    "statistics_and_analysis_005",
]
wave_b = [f"indicators_{i:03d}" for i in range(11)]
wave_c = [f"expert_advisors_{i:03d}" for i in range(5)] + ["experts_000", "interviews_000"]
wave_nn = [f"trading_systems_047_p{i:02d}" for i in range(7)]
wave_wiz = [f"trading_systems_043_p{i:02d}" for i in range(6)]
wave_pa = [f"examples_088_p{i:02d}" for i in range(4)] + [
    "indicators_010",
    "trading_systems_049_p00",
    "trading_systems_049_p01",
]

def dump(name, ids):
    packs = [load(i) for i in ids]
    path = ROOT / "waves" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"packs": packs}, indent=2), encoding="utf-8")
    print(name, "packs", len(packs), "articles", sum(p["n"] for p in packs), "->", path)

dump("wave_ml_stats", wave_a)
dump("wave_indicators", wave_b)
dump("wave_ea", wave_c)
dump("wave_nn_made_easy", wave_nn)
dump("wave_wizard", wave_wiz)
dump("wave_price_action", wave_pa)
