"""Extract key gold-mine / recovery messages to markdown."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\AppData\Local\hermes\state.db")
OUT = Path(
    r"C:\Users\Mubarak\Desktop\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-09-16\research"
)

KEYS = [
    ("20260825_115530_94412f", 4070, "goldmine-4070-assistant.md"),
    ("20260825_115530_94412f", 4071, "goldmine-4071-user.md"),
    ("20260826_180446_36307b", 5678, "recovery-5678-assistant.md"),
]


def main() -> None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    for sid, mid, name in KEYS:
        row = cur.execute(
            "SELECT role, compacted, content FROM messages WHERE session_id=? AND id=?",
            (sid, mid),
        ).fetchone()
        if not row:
            print("missing", sid, mid)
            continue
        role, compacted, content = row
        (OUT / name).write_text(
            f"# {sid} msg {mid} role={role} compacted={compacted}\n\n{content or ''}",
            encoding="utf-8",
        )
        print("wrote", name, "len", len(content or ""), "role", role)


if __name__ == "__main__":
    main()
