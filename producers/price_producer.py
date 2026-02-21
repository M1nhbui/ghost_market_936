import json
import time
import os
from dotenv import load_dotenv
from kafka import KafkaProducer
from price_fetcher import fetch_prices, TARGET_TICKERS

load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "placeholder")
KAFKA_TOPIC = "live-prices"
POLL_INTERVAL = 60  # seconds

# --- Kafka Producer ---
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    # TODO: Uncomment when teammate provides Aiven credentials
    # ssl_cafile=os.getenv("KAFKA_SSL_CA"),
    # ssl_certfile=os.getenv("KAFKA_SSL_CERT"),
    # ssl_keyfile=os.getenv("KAFKA_SSL_KEY"),
    # security_protocol="SSL",
)


def produce_prices():
    """Main loop: fetch prices and push each ticker as a Kafka message."""
    print("[INFO] Price producer started...")

    while True:
        data = fetch_prices()

        if data:
            for ticker, values in data.items():
                message = {
                    "ticker": ticker,
                    "price_usd": values["usd"],
                    "timestamp": time.time(),
                }
                producer.send(KAFKA_TOPIC, value=message)
                print(f"[PRODUCED] {message}")

            producer.flush()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    produce_prices()