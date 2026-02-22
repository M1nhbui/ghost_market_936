import os
import json
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from telethon import TelegramClient, events
from import_me_to_use_kafka_stuff import send_string_to_kafka_topic

load_dotenv()

# --- Config ---
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
KAFKA_TOPIC = "live-social"

# --- Alias Map: maps any variant → canonical ticker name ---
TICKER_ALIASES = {
    "bitcoin": "bitcoin",
    "bitconi": "bitcoin",   # typo
    "bitcon": "bitcoin",    # typo
    "bitocin": "bitcoin",   # typo
    "btc": "bitcoin",       # short form
    "dogecoin": "dogecoin",
    "dodcoin": "dogecoin",  # typo
    "dogcoin": "dogecoin",  # typo
    "doge": "dogecoin",     # short form
}

TARGET_GROUPS = [
    # "binanceexchange",      # Binance Global English
    # "CryptoComOfficial",    # Crypto.com English
    # "dogecoin_official",    # Dogecoin Community
    "groupcrypto100win"
]

# --- Telethon Client ---
client = TelegramClient("ghostmarket_session", API_ID, API_HASH)


def detect_tickers(text: str) -> list[str]:
    """
    Returns list of canonical ticker names found in text.
    Matches exact aliases and typos defined in TICKER_ALIASES.
    Example: "btc to the moon, doge!" -> ["bitcoin", "dogecoin"]
    """
    words = text.lower().split()
    found = set()
    for word in words:
        # Strip punctuation from word edges e.g. "btc!" -> "btc"
        clean_word = word.strip("!?,.()")
        if clean_word in TICKER_ALIASES:
            found.add(TICKER_ALIASES[clean_word])
    return list(found)


@client.on(events.NewMessage(chats=TARGET_GROUPS))
async def handler(event):
    """Fires on every new message in TARGET_GROUPS."""
    text = event.raw_text.lower()

    # Layer 1 — Alias-aware keyword filter
    matched_tickers = detect_tickers(text)
    if not matched_tickers:
        return

    payload = json.dumps({
        "source": "telegram",
        "timestamp": event.date.timestamp(),
        "text": text,
        "tickers": matched_tickers,       # e.g. ["bitcoin", "dogecoin"]
        "author": str(event.sender_id),
    })

    send_string_to_kafka_topic(KAFKA_TOPIC, payload)
    print(f"[PRODUCED] tickers={matched_tickers} | {text[:60]}...")


async def main():
    print("[INFO] Social producer starting...")
    await client.start()
    print(f"[INFO] Listening to {len(TARGET_GROUPS)} groups...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())