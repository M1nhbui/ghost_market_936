import os
from dotenv import load_dotenv
import duckdb

load_dotenv()
TOKEN = os.getenv("MOTHERDUCK_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing MOTHERDUCK_TOKEN in .env")

DB = "tiny_demo"

con = duckdb.connect(f"md:?motherduck_token={TOKEN}")

con.execute(f"USE {DB}")

con.execute("""
CREATE TABLE IF NOT EXISTS people (
  id INTEGER,
  name TEXT,
  created_at TIMESTAMP DEFAULT now()
)
""")

con.execute("DELETE FROM people")  # makes reruns clean
con.execute("INSERT INTO people (id, name) VALUES (1, 'Minh'), (2, 'DuckDB'), (3, 'MotherDuck')")

rows = con.execute("SELECT id, name, created_at FROM people ORDER BY id").fetchall()
print("Rows in people:")
for r in rows:
    print(r)
