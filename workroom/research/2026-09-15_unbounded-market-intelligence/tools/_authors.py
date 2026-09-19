import re
from pathlib import Path

MD = Path(r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md")
ids = [
    2930, 22484, 23488, 22754, 21142, 22553, 15222, 6834, 21299, 22438,
    22476, 22519, 22539, 22638, 23171, 21743, 21742, 22220, 22756, 23077,
    23351, 23451, 11487, 6351, 17273, 3886, 23112, 23444, 23149, 16085,
    18453, 23565, 23657, 16747, 23013, 20173, 5451, 12129, 2118,
]
for aid in ids:
    text = (MD / f"{aid}.md").read_text(encoding="utf-8", errors="replace")[:3000]
    m = re.search(r'author:\s*"([^"]*)"', text)
    m2 = re.search(r"\[([^\]]+)\]\(https://www\.mql5\.com/en/users/", text)
    author = (m.group(1) if m and m.group(1) else "") or (m2.group(1) if m2 else "")
    print(aid, author[:50])
