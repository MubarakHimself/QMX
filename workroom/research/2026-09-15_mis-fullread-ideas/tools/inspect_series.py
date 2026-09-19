import sqlite3
from collections import Counter

p = r"C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\index.sqlite"
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
rows = list(con.execute("SELECT series_title, series_part, title FROM articles WHERE fetch_status='ok'"))
empty = sum(1 for r in rows if not (r["series_title"] or "").strip())
print("ok", len(rows), "empty series_title", empty, "filled", len(rows) - empty)
print("series_part set", sum(1 for r in rows if r["series_part"] not in (None, "")))
n = 0
for r in rows:
    st = (r["series_title"] or "").strip()
    if st:
        print(repr(st[:90]), r["series_part"], "|", (r["title"] or "")[:70])
        n += 1
        if n >= 12:
            break
print("--- title Part N count ---")
import re
pat = re.compile(r"\bPart\s+(\d+)\b", re.I)
print("titles with Part N", sum(1 for r in rows if pat.search(r["title"] or "")))
