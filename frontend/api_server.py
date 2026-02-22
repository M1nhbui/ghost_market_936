import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import duckdb
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MOTHERDUCK_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing MOTHERDUCK_TOKEN in .env")

DB_NAME = os.getenv("GHOSTMARKET_DB", "ghostmarket")

app = Flask(__name__)
CORS(app)

def get_con():
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
    con.execute(f"USE {DB_NAME}")
    return con

def sentiment_label(v: float) -> str:
    if v >= 0.35: return "Bullish"
    if v >= 0.10: return "Slight +"
    if v >= -0.10: return "Neutral"
    return "Bearish"

def fmt_time(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%I:%M %p")
    except Exception:
        return ""

@app.get("/api/state")
def api_state():
    ticker = request.args.get("ticker", "dogecoin").lower()
    limit_price = int(request.args.get("price_limit", "60"))
    limit_vibe = int(request.args.get("vibe_limit", "50"))
    window_s = 9999999 # int(request.args.get("window_s", "300"))

    con = get_con()
    now = time.time()
    cutoff = now - window_s

    # --- price series ---
    price_rows = con.execute(
        """
        SELECT timestamp, price_usd
        FROM price_snapshots
        WHERE ticker = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        [ticker, limit_price],
    ).fetchall()

    price_rows = list(reversed(price_rows))
    price_series = [{"t": fmt_time(ts), "p": float(p)} for ts, p in price_rows]
    last_price = price_series[-1]["p"] if price_series else None

    # --- vibe feed (latest messages) ---
    vibe_rows = con.execute(
        """
        SELECT text, vibe_score, timestamp, source
        FROM social_signals
        WHERE ticker = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        [ticker, limit_vibe],
    ).fetchall()

    vibe_feed = []
    for text, score, ts, source in vibe_rows:
        score = float(score) if score is not None else 0.0
        vibe_feed.append(
            {
                "message": text,
                "sentimentValue": score,
                "sentimentLabel": sentiment_label(score),
                "timeLabel": fmt_time(ts),
                "source": source or "unknown",
            }
        )

    # --- stats over last window ---
    stats_row = con.execute(
        """
        SELECT
            AVG(vibe_score) AS avg_sent,
            COUNT(*) AS n_events,
            COUNT(DISTINCT source) AS n_sources
        FROM social_signals
        WHERE ticker = ?
          AND timestamp >= ?
        """,
        [ticker, cutoff],
    ).fetchone()

    avg_sent = float(stats_row[0]) if stats_row and stats_row[0] is not None else 0.0
    n_events = int(stats_row[1]) if stats_row and stats_row[1] is not None else 0
    n_sources = int(stats_row[2]) if stats_row and stats_row[2] is not None else 0

    # --- latest decoupling signal ---
    sig = con.execute(
        """
        SELECT
            timestamp, delta_price, delta_vibe, hype_momentum, alert
        FROM decoupling_signals
        WHERE ticker = ?
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        [ticker],
    ).fetchone()

    if sig:
        _, delta_price, delta_vibe, hype_momentum, alert = sig
        delta_price = float(delta_price) if delta_price is not None else 0.0
        delta_vibe = float(delta_vibe) if delta_vibe is not None else 0.0
        hype_momentum = float(hype_momentum) if hype_momentum is not None else 0.0
        alert = alert  # can be None or "IMMINENT_HYPE_PUMP"
    else:
        delta_price = 0.0
        delta_vibe = 0.0
        hype_momentum = 0.0
        alert = None

    signal_up = (hype_momentum > 1.0)  # matches check_alert intent

    state = {
        "ticker": {
            "key": ticker,
            "label": ticker.capitalize(),
            "symbol": ticker[:4].upper(),
        },
        "stats": {
            "avgSentiment": round(avg_sent, 2),
            "signalUp": bool(signal_up),
            "sources": n_sources,
            "eventsCount": n_events,
            "eventsLabel": "imminent" if alert else "demo",
        },
        "price": {
            "last": last_price if last_price is not None else 0.0,
            "changePct": 0.0,  # optional; compute later if you want
            "series": price_series,
        },
        "vibeFeed": vibe_feed,
        "signal": {
            "alert": alert,
            "deltaPrice": round(delta_price, 4),
            "deltaVibe": round(delta_vibe, 4),
            "hypeMomentum": round(hype_momentum, 1),
            "n": n_events,
        },
    }

    return jsonify(state)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
