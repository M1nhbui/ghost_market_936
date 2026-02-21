"""
Tiny Kafka helper for GhostMarket (Aiven SSL).

Goal:
- Friend can import this file and call:
    send_string_to_kafka_topic("bitcoin", "hello")
    receive_one_content_from_kafka_topic("bitcoin")

Notes:
- Topic partition count is configured on the Kafka cluster (not enforced here).
- This module uses SSL certs stored next to this file (robust to working directory).
- Consumer polls up to `timeout_s` seconds; it does NOT hang forever.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from confluent_kafka import Producer, Consumer, KafkaException

# Load .env from current working directory (typical usage)
load_dotenv()

BOOTSTRAP = os.getenv("BOOTSTRAP_SERVERS")
if not BOOTSTRAP:
    raise RuntimeError("Missing BOOTSTRAP_SERVERS. Set it in .env or your environment.")

# Resolve cert paths relative to THIS file, not the caller's working directory.
_THIS_DIR = Path(__file__).resolve().parent
_CERT_DIR = _THIS_DIR / "certs_for_aiven_kafka_online"

_CA = _CERT_DIR / "ca.pem"
_CERT = _CERT_DIR / "service.cert"
_KEY = _CERT_DIR / "service.key"

for p in (_CA, _CERT, _KEY):
    if not p.exists():
        raise RuntimeError(f"Missing Kafka SSL file: {p}")

EXPECTED_TOPIC_NAMES = {"bitcoin", "dogecoin"}

_BASE_CONFIG = {
    "bootstrap.servers": BOOTSTRAP,
    "security.protocol": "SSL",
    "ssl.ca.location": str(_CA),
    "ssl.certificate.location": str(_CERT),
    "ssl.key.location": str(_KEY),
}

# Producer can be reused; keep it module-level for simplicity.
_PRODUCER = Producer(_BASE_CONFIG)


def _validate_topic(topic_name: str) -> None:
    if topic_name not in EXPECTED_TOPIC_NAMES:
        raise ValueError(
            f"Unsupported topic {topic_name!r}. Supported: {sorted(EXPECTED_TOPIC_NAMES)} (ask nghia about this)"
        )


def send_string_to_kafka_topic(topic_name: str, content: str, flush_timeout_s: float = 5.0) -> None:
    """
    Sends one UTF-8 string message to `topic_name`.

    flush_timeout_s:
      how long to wait for delivery (default 5s). If delivery doesn't complete in time,
      we raise an error so the caller knows it didn't go through reliably.
    """
    _validate_topic(topic_name)

    delivery_err = {"err": None}

    def delivery_report(err, msg):
        # Callback is invoked from producer.poll()/flush()
        if err is not None:
            delivery_err["err"] = err
        else:
            # Keep prints minimal; comment out if you want it silent.
            print(f"Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

    _PRODUCER.produce(topic_name, value=content.encode("utf-8"), callback=delivery_report)

    # Serve callbacks + ensure delivery
    remaining = _PRODUCER.flush(flush_timeout_s)
    if remaining != 0:
        raise TimeoutError(f"Kafka delivery not confirmed after {flush_timeout_s}s (remaining={remaining}).")
    if delivery_err["err"] is not None:
        raise KafkaException(delivery_err["err"])


def receive_one_content_from_kafka_topic(
    topic_name: str,
    timeout_s: float = 3.0,
) -> str | None:
    """
    Polls up to `timeout_s` seconds and returns ONE message (decoded as UTF-8).
    Returns None if no message arrives before timeout.

    group_id:
      consumer group to use (required by confluent_kafka Consumer).
    """
    _validate_topic(topic_name)

    group_id = topic_name + "_1"

    consumer_config = dict(_BASE_CONFIG)
    consumer_config.update(
        {
            "group.id": group_id,
            "enable.auto.commit": True,
            "auto.offset.reset": "earliest",
        }
    )

    c = Consumer(consumer_config)
    try:
        c.subscribe([topic_name])

        msg = c.poll(timeout_s)

        if msg is None:
            return None

        if msg.error():
            # This covers partition EOF and real errors; treat as an exception for simplicity.
            raise KafkaException(msg.error())

        value_bytes = msg.value()
        if value_bytes is None:
            return None

        result = value_bytes.decode("utf-8", errors="replace")
        print(f"[DEBUG] {msg.topic()}[{msg.partition()}]@{msg.offset()}: {result}")
        return result
    finally:
        c.close()
