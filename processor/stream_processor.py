import os
import json
import time
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from transformers import pipeline
from import_me_to_use_kafka_stuff import receive_one_content_from_kafka_topic
from math_utils import SlidingWindow, delta_price, delta_vibe, hype_momentum, check_alert
from db import get_connection, init_schema, insert_price, insert_social, insert_signal

load_dotenv()

# --- Config ---
PRICE_TOPICS = ["dogecoin"]
SOCIAL_TOPIC = "live-social"
POLL_TIMEOUT = 5       # seconds to wait per Kafka poll
WINDOW_SECONDS = 300   # 5-minute sliding window

# --- FinBERT Sentiment Pipeline ---
print("[INFO] Loading FinBERT model...")
sentiment = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    tokenizer="ProsusAI/finbert",
)
print("[INFO] FinBERT ready.")


def finbert_score(text: str) -> float:
    """
    Run FinBERT on text. Returns a score in [-1, +1].
    positive  → +confidence
    negative  → -confidence
    neutral   → 0.0
    Truncates to 512 tokens automatically.
    """
    result = sentiment(text[:512])[0]
    label = result["label"]
    score = result["score"]

    if label == "positive":
        return score
    elif label == "negative":
        return -score
    else:
        return 0.0


# --- Per-ticker state ---
# Each ticker gets its own sliding windows
price_windows: dict[str, SlidingWindow] = {}
vibe_windows: dict[str, SlidingWindow] = {}

for ticker in PRICE_TOPICS:
    price_windows[ticker] = SlidingWindow(window_seconds=WINDOW_SECONDS)
    vibe_windows[ticker] = SlidingWindow(window_seconds=WINDOW_SECONDS)


def process_price_message(raw: str) -> None:
    """
    Parse and ingest a price message into the sliding window.
    Expected format:
    {"ticker": "bitcoin", "price_usd": 62500.0, "timestamp": 1740134400.0}
    """
    try:
        msg = json.loads(raw)
        ticker = msg["ticker"]
        price = float(msg["price_usd"])
        ts = float(msg["timestamp"])

        if ticker not in price_windows:
            print(f"[SKIP] Unknown ticker: {ticker}")
            return

        price_windows[ticker].add(price, timestamp=ts)
        print(f"[PRICE] {ticker} = ${price:,.2f} | window_avg = ${price_windows[ticker].average():,.2f}")

    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"[ERROR] Bad price message: {e} | raw={raw}")


def process_social_message(raw: str) -> None:
    """
    Parse a social message, run FinBERT, ingest vibe score into window.
    Expected format:
    {"source": "telegram", "timestamp": ..., "text": "...", "tickers": ["bitcoin"], "author": "..."}
    """
    try:
        msg = json.loads(raw)
        text = msg["text"]
        tickers = msg.get("tickers", [])
        ts = float(msg["timestamp"])

        if not tickers:
            return

        vibe = finbert_score(text)

        for ticker in tickers:
            if ticker not in vibe_windows:
                continue
            vibe_windows[ticker].add(vibe, timestamp=ts)
            print(f"[VIBE]  {ticker} | score={vibe:+.3f} | window_avg={vibe_windows[ticker].average():+.3f}")

    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"[ERROR] Bad social message: {e} | raw={raw}")


def compute_and_alert(ticker: str) -> dict | None:
    """
    Compute decoupling metrics for a ticker and fire alert if conditions met.
    Returns a signal dict always if there is any price data,
    or None only if the window is completely empty.
    """
    p_win = price_windows[ticker]
    v_win = vibe_windows[ticker]

    p_current = p_win.latest()
    p_avg = p_win.average()
    v_current = v_win.latest()
    v_avg = v_win.average()

    # No price data at all yet — too early to write anything
    if p_current is None or p_avg is None:
        return None

    # Vibe data might not exist yet — default to 0.0 (neutral)
    if v_current is None:
        v_current = 0.0
    if v_avg is None:
        v_avg = 0.0

    dp = delta_price(p_current, p_avg)
    dv = delta_vibe(v_current, v_avg)
    n = v_win.count()
    mh = hype_momentum(dv, n)
    alert = check_alert(mh, dp)

    signal = {
        "ticker": ticker,
        "timestamp": time.time(),
        "price_current": p_current,
        "price_avg": p_avg,
        "vibe_current": v_current,
        "vibe_avg": v_avg,
        "delta_price": dp,
        "delta_vibe": dv,
        "hype_momentum": mh,
        "alert": alert,   # NULL in DB when no alert — row still written
    }

    if alert:
        print(f"🚨 ALERT [{ticker}] {alert} | M_hype={mh:.1f} | ΔP={dp:.4f}")

    return signal


def run():
    """
    Main processor loop.
    Alternates polling between price topics and social topic.
    """
    print("[INFO] Stream processor started...")

    # Init DB connection once
    con = get_connection()
    init_schema(con)

    while True:
        # Poll price topics
        for topic in PRICE_TOPICS:
            raw = receive_one_content_from_kafka_topic(topic, timeout_s=POLL_TIMEOUT)
            print("DEBUG CHIM TO:", raw, topic)
            if raw:
                process_price_message(raw)
                msg = json.loads(raw)
                insert_price(con, msg["ticker"], msg["price_usd"], msg["timestamp"])

        # Poll social topic
        raw = receive_one_content_from_kafka_topic(SOCIAL_TOPIC, timeout_s=POLL_TIMEOUT)
        if raw:
            process_social_message(raw)
            msg = json.loads(raw)
            for ticker in msg.get("tickers", []):
                insert_social(
                    con,
                    ticker=ticker,
                    vibe_score=finbert_score(msg["text"]),
                    text=msg["text"],
                    author=msg["author"],
                    source=msg["source"],
                    timestamp=msg["timestamp"],
                )

        # Compute metrics and write signals
        for ticker in PRICE_TOPICS:
            signal = compute_and_alert(ticker)
            if signal:                          # only None if price window empty
                insert_signal(con, signal)


if __name__ == "__main__":
    run()