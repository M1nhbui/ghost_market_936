import json
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from import_me_to_use_kafka_stuff import send_string_to_kafka_topic
from price_fetcher import fetch_prices, TARGET_TICKERS

load_dotenv()

POLL_INTERVAL = 60  # seconds


def produce_prices():
    """Main loop: fetch prices and push each ticker as a Kafka message."""
    print("[INFO] Price producer started...")

    while True:
        data = fetch_prices()

        if data:
            for ticker, values in data.items():
                # Only produce if topic exists in Kafka
                if ticker not in ("bitcoin", "dogecoin"):
                    print(f"[SKIP] No Kafka topic for {ticker}, skipping.")
                    continue

                message = json.dumps({
                    "ticker": ticker,
                    "price_usd": values["usd"],
                    "timestamp": time.time(),
                })

                send_string_to_kafka_topic(ticker, message)
                print(f"[PRODUCED] {message}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    produce_prices()