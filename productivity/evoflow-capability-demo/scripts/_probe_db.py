import sqlite3
from pathlib import Path

p = Path(r"C:\Users\admin\.evoflow-dev\evoflow.db")
c = sqlite3.connect(str(p))
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1")]
print("TABLES:")
for t in tables:
    print(" ", t)

for hint in ("token", "auth", "api_key", "session", "credential"):
    hits = [t for t in tables if hint in t.lower()]
    if hits:
        print(f"HINT {hint}:", hits)

for t in tables:
    if any(x in t.lower() for x in ("token", "api_key", "credential", "auth")):
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
        print(f"\n{t} cols:", cols)
        try:
            rows = c.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
            for row in rows:
                # redact long secrets in print — show presence only
                safe = []
                for v, col in zip(row, cols):
                    s = str(v) if v is not None else ""
                    if any(k in col.lower() for k in ("token", "key", "secret", "hash")) and len(s) > 8:
                        safe.append(f"{col}={s[:6]}…len{len(s)}")
                    else:
                        safe.append(f"{col}={s[:80]}")
                print(" ", " | ".join(safe))
        except Exception as e:
            print("  err", e)
