"""Dump gold-mine messages around 4065-4071 even if compacted."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\AppData\Local\hermes\state.db")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-09-16\research"
)


def main() -> None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    sid = "20260825_115530_94412f"
    rows = cur.execute(
        "SELECT id, role, compacted, active, length(content) n, content "
        "FROM messages WHERE session_id=? AND id BETWEEN 4050 AND 4080 "
        "ORDER BY id",
        (sid,),
    ).fetchall()
    print("range 4050-4080 count", len(rows))
    parts = [f"# goldmine messages 4050-4080 n={len(rows)}\n"]
    for r in rows:
        body = r["content"] or ""
        parts.append(
            f"\n## msg {r['id']} role={r['role']} compacted={r['compacted']} "
            f"active={r['active']} chars={r['n']}\n\n{body}\n"
        )
        print(r["id"], r["role"], "c", r["compacted"], "n", r["n"])
    (OUT / "goldmine-4065-range.md").write_text("".join(parts), encoding="utf-8")

    # All user messages including compacted
    users = cur.execute(
        "SELECT id, compacted, active, length(content) n, content "
        "FROM messages WHERE session_id=? AND role='user' ORDER BY id",
        (sid,),
    ).fetchall()
    uparts = [f"# goldmine ALL user messages n={len(users)}\n"]
    for r in users:
        uparts.append(
            f"\n## msg {r['id']} compacted={r['compacted']} active={r['active']} "
            f"chars={r['n']}\n\n{r['content'] or ''}\n"
        )
    (OUT / "goldmine-all-user.md").write_text("".join(uparts), encoding="utf-8")
    print("all users", len(users))

    rec_users = cur.execute(
        "SELECT id, compacted, active, length(content) n, content "
        "FROM messages WHERE session_id=? AND role='user' ORDER BY id",
        ("20260826_180446_36307b",),
    ).fetchall()
    rparts = [f"# recovery ALL user n={len(rec_users)}\n"]
    for r in rec_users:
        rparts.append(
            f"\n## msg {r['id']} compacted={r['compacted']} chars={r['n']}\n\n"
            f"{r['content'] or ''}\n"
        )
    (OUT / "recovery-all-user.md").write_text("".join(rparts), encoding="utf-8")
    print("recovery users", len(rec_users))


if __name__ == "__main__":
    main()
