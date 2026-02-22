import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MOTHERDUCK_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing MOTHERDUCK_TOKEN in .env")

DB_NAME = "ghostmarket"

# --- Connection ---
def get_connection() -> duckdb.DuckDBPyConnection:
    """Create and return a MotherDuck connection."""
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
    con.execute(f"USE {DB_NAME}")
    return con


# --- Schema Setup ---
def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """
    Create tables if they don't exist.
    Safe to call on every startup.
    """

    # Raw price snapshots from CoinGecko
    con.execute("""
        CREATE TABLE IF NOT EXISTS price_snapshots (
            ticker      TEXT,
            price_usd   DOUBLE,
            timestamp   DOUBLE,
            ingested_at TIMESTAMP DEFAULT now()
        )
    """)

    # Raw social signals from Telegram (post-FinBERT)
    con.execute("""
        CREATE TABLE IF NOT EXISTS social_signals (
            ticker      TEXT,
            vibe_score  DOUBLE,
            text        TEXT,
            author      TEXT,
            source      TEXT,
            timestamp   DOUBLE,
            ingested_at TIMESTAMP DEFAULT now()
        )
    """)

    # Computed decoupling signals (output of stream_processor.py)
    con.execute("""
        CREATE TABLE IF NOT EXISTS decoupling_signals (
            ticker          TEXT,
            timestamp       DOUBLE,
            price_current   DOUBLE,
            price_avg       DOUBLE,
            vibe_current    DOUBLE,
            vibe_avg        DOUBLE,
            delta_price     DOUBLE,
            delta_vibe      DOUBLE,
            hype_momentum   DOUBLE,
            alert           TEXT,       -- NULL or "IMMINENT_HYPE_PUMP"
            recorded_at     TIMESTAMP DEFAULT now()
        )
    """)

    print("[DB] Schema ready.")


# --- Write Helpers ---
def insert_price(con: duckdb.DuckDBPyConnection, ticker: str, price_usd: float, timestamp: float) -> None:
    con.execute(
        "INSERT INTO price_snapshots (ticker, price_usd, timestamp) VALUES (?, ?, ?)",
        [ticker, price_usd, timestamp]
    )


def insert_social(
    con: duckdb.DuckDBPyConnection,
    ticker: str,
    vibe_score: float,
    text: str,
    author: str,
    source: str,
    timestamp: float,
) -> None:
    con.execute(
        """INSERT INTO social_signals
           (ticker, vibe_score, text, author, source, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [ticker, vibe_score, text, author, source, timestamp]
    )


def insert_signal(con: duckdb.DuckDBPyConnection, signal: dict) -> None:
    con.execute(
        """INSERT INTO decoupling_signals
           (ticker, timestamp, price_current, price_avg,
            vibe_current, vibe_avg, delta_price,
            delta_vibe, hype_momentum, alert)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            signal["ticker"],
            signal["timestamp"],
            signal["price_current"],
            signal["price_avg"],
            signal["vibe_current"],
            signal["vibe_avg"],
            signal["delta_price"],
            signal["delta_vibe"],
            signal["hype_momentum"],
            signal["alert"],
        ]
    )


# --- Run standalone to verify connection & schema ---
if __name__ == "__main__":
    con = get_connection()
    init_schema(con)

    # Quick sanity check
    tables = con.execute("SHOW TABLES").fetchall()
    print("Tables in ghostmarket DB:")
    for t in tables:
        print(f"  - {t[0]}")

    con.close()