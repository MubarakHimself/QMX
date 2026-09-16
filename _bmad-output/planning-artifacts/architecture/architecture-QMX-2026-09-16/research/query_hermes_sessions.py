"""Read-only probe of Hermes state.db for STRATS session IDs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\Mubarak\AppData\Local\hermes\state.db")
IDS = (
    "20260824_121737_86f88c",
    "20260825_115530_94412f",
    "20260826_115355_ae94f7",
    "20260826_180446_36307b",
)


def main() -> None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    print("TABLES")
    for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"):
        print(" ", r[0])
    print("\nSCHEMA snippets")
    for name in [
        "sessions",
        "session",
        "messages",
        "message",
        "conversation_messages",
    ]:
        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        if row:
            print(row[0][:800])
            print("---")
    # Try common session id columns
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
        joined = " ".join(cols).lower()
        if "session" in joined or "id" in joined:
            if any(c.lower() in {"id", "session_id", "sessionid"} for c in cols):
                idcol = next(
                    c
                    for c in cols
                    if c.lower() in {"session_id", "sessionid", "id"}
                )
                try:
                    q = f"SELECT {idcol} FROM {table} WHERE {idcol} LIKE '%94412f%' OR {idcol} LIKE '%36307b%' OR {idcol} LIKE '%86f88c%' OR {idcol} LIKE '%ae94f7%' LIMIT 20"
                    hits = list(cur.execute(q))
                    if hits:
                        print(f"HITS in {table}.{idcol}: {hits}")
                except sqlite3.Error as exc:
                    print(f"skip {table}: {exc}")


if __name__ == "__main__":
    main()
