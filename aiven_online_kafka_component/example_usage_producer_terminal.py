import time
from import_me_to_use_kafka_stuff import send_string_to_kafka_topic

TOPIC = "bitcoin"

payload = f"hello kafka @ {time.strftime('%Y-%m-%d %H:%M:%S')}"
print(f"[producer] sending to {TOPIC!r}: {payload!r}")
send_string_to_kafka_topic(TOPIC, payload)
print("[producer] done")
