"""Dump STRATS Hermes session metadata and user-turn excerpts (read-only)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\AppData\Local\hermes\state.db")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-09-16\research"
)
IDS = (
    "20260824_121737_86f88c",
    "20260825_115530_94412f",
    "20260826_115355_ae94f7",
    "20260826_180446_36307b",
)


def preview(text: str | None, n: int = 400) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n")
    return t[:n] + ("…" if len(t) > n else "")


def main() -> None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    meta = []
    for sid in IDS:
        s = cur.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if s is None:
            print("MISSING", sid)
            continue
        counts = list(
            cur.execute(
                "SELECT role, COUNT(*), SUM(CASE WHEN compacted=1 THEN 1 ELSE 0 END) "
                "FROM messages WHERE session_id=? GROUP BY role",
                (sid,),
            )
        )
        total = cur.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id=?", (sid,)
        ).fetchone()[0]
        rec = {
            "id": sid,
            "display_name": s["display_name"],
            "model": s["model"],
            "cwd": s["cwd"],
            "message_count_col": s["message_count"],
            "messages_rows": total,
            "started_at": s["started_at"],
            "ended_at": s["ended_at"],
            "end_reason": s["end_reason"],
            "parent_session_id": s["parent_session_id"],
            "role_counts": [(r[0], r[1], r[2]) for r in counts],
        }
        meta.append(rec)
        print(json.dumps(rec, default=str))

    (OUT / "session-index.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # User turns for gold mine + recovery
    for sid, slug in (
        ("20260825_115530_94412f", "goldmine-user-turns"),
        ("20260826_180446_36307b", "recovery-user-turns"),
        ("20260826_115355_ae94f7", "ae94f7-user-turns"),
    ):
        rows = cur.execute(
            "SELECT id, role, timestamp, compacted, length(content) AS n, "
            "substr(content,1,2000) AS head FROM messages "
            "WHERE session_id=? AND role='user' AND active=1 ORDER BY id",
            (sid,),
        ).fetchall()
        lines = [f"# {sid} user turns ({len(rows)})\n"]
        for r in rows:
            lines.append(
                f"\n## msg {r['id']} compacted={r['compacted']} chars={r['n']}\n\n"
                f"{r['head'] or ''}\n"
            )
        (OUT / f"{slug}.md").write_text("".join(lines), encoding="utf-8")
        print("wrote", slug, "n=", len(rows))

    # Longest assistant messages in gold mine and recovery (design dumps)
    for sid, slug in (
        ("20260825_115530_94412f", "goldmine-long-assistant"),
        ("20260826_180446_36307b", "recovery-long-assistant"),
    ):
        rows = cur.execute(
            "SELECT id, compacted, length(content) AS n FROM messages "
            "WHERE session_id=? AND role='assistant' AND active=1 "
            "ORDER BY n DESC LIMIT 8",
            (sid,),
        ).fetchall()
        print(slug, [(r["id"], r["n"], r["compacted"]) for r in rows])

    # Dump the longest recovery assistant message (likely the 56k recovery)
    row = cur.execute(
        "SELECT id, content FROM messages WHERE session_id=? AND role='assistant' "
        "AND active=1 ORDER BY length(content) DESC LIMIT 1",
        ("20260826_180446_36307b",),
    ).fetchone()
    if row and row["content"]:
        path = OUT / "recovery-36307b-longest-assistant.md"
        path.write_text(
            f"# recovery session assistant msg {row['id']}\n\n{row['content']}",
            encoding="utf-8",
        )
        print("wrote recovery dump", row["id"], "len", len(row["content"]))

    row = cur.execute(
        "SELECT id, content FROM messages WHERE session_id=? AND role='assistant' "
        "AND active=1 ORDER BY length(content) DESC LIMIT 1",
        ("20260825_115530_94412f",),
    ).fetchone()
    if row and row["content"]:
        path = OUT / "goldmine-94412f-longest-assistant.md"
        path.write_text(
            f"# goldmine session assistant msg {row['id']}\n\n{row['content']}",
            encoding="utf-8",
        )
        print("wrote goldmine dump", row["id"], "len", len(row["content"]))


if __name__ == "__main__":
    main()
