import requests
import os
from dotenv import load_dotenv

load_dotenv()

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
TARGET_TICKERS = ["bitcoin", "dogecoin"]


def fetch_prices() -> dict | None:
    """Fetch current USD prices for all target tickers from CoinGecko."""
    try:
        response = requests.get(
            COINGECKO_URL,
            params={
                "ids": ",".join(TARGET_TICKERS),
                "vs_currencies": "usd",
            },
            headers={"x-cg-demo-api-key": COINGECKO_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch prices: {e}")
        return None


# --- Run this file directly to test fetching alone ---
if __name__ == "__main__":
    data = fetch_prices()
    if data:
        for ticker, values in data.items():
            print(f"{ticker}: ${values['usd']}")
    else:
        print("No data returned.")