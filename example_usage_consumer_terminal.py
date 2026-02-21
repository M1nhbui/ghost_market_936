from import_me_to_use_kafka_stuff import receive_one_content_from_kafka_topic

TOPIC = "bitcoin"

print(f"[consumer] waiting for ONE message on topic={TOPIC!r} ...")
msg = receive_one_content_from_kafka_topic(TOPIC, timeout_s=10)

if msg is None:
    print("[consumer] timeout (no message received)")
else:
    print(f"[consumer] got: {msg!r}")
