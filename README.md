# 👻 GhostMarket: Real-Time Vibe & Price Decoupling Engine

GhostMarket is a real-time data engineering pipeline designed to detect **market decoupling events**—moments when social sentiment (the **Vibe**) diverges from live asset prices.

Traditional indicators are often **lagging** (they tell you what already happened). GhostMarket aims to act as a **leading indicator** by:

* Ingesting high-frequency sentiment signals from social platforms
* Overlaying them against live price feeds
* Triggering alerts when attention/emotion shifts **before** price reacts

This helps surface early signals of:

* **Hype Pumps** (sentiment spikes while price is flat)
* **Panic Crashes** (negative sentiment surges ahead of a selloff)

---

## 🧭 Table of Contents

* [System Architecture](#-system-architecture)
* [Tracking Strategy](#-tracking-strategy)
* [Decoupling Math (MVP)](#-decoupling-math-mvp)
* [Tech Stack](#-tech-stack)
* [Repository Structure](#-repository-structure)
* [Quickstart](#-quickstart)
* [Configuration](#-configuration)
* [Running the Pipeline](#-running-the-pipeline)
* [Roadmap](#-roadmap)

---

## 🏗️ System Architecture

GhostMarket uses an **in-flight streaming** architecture optimized for low latency.
<img width="8192" height="2238" alt="Social_Signal_Processing-2026-02-22-152017" src="https://github.com/user-attachments/assets/92cc682d-b36e-462d-a8fe-c4106b951eb5" />

### Phase 1 — The Listeners (Data Ingestion)

Two asynchronous Python scripts run in parallel:

* **Price Producer**: Polls CoinGecko every **5 seconds** for target asset prices
* **Social Producer**: Pulls live text mentions from:

  * Telegram (e.g., `binanceexchange`, `CryptoComOfficial`, `dogecoin_official`)
  

### Phase 2 — The Highway (Message Broker)

Raw, unstructured data is pushed immediately into **partitioned topics** in Aiven Kafka, creating a strict time-ordered stream.

### Phase 3 — The Brain (Stream Processing & Threshold Engine)

A consumer subscribes to Kafka. For **each message**:

1. **Sentiment Extraction**: Text is scored with **FinBERT** → a continuous **Vibe Score** in `[-1.0, +1.0]`
2. **Rolling Memory**: Maintain a sliding 5-minute window for sentiment and price using an **O(1)** `deque`
3. **Decoupling Logic**: Compare the current state to rolling averages using strict thresholds to detect a “rubber band snap”

### Phase 4 — The Memory (Data Lakehouse)

Processed records are written into **MotherDuck** (DuckDB cloud) across three tables:

| Table | Written By | Contents |
|-------|-----------|---------|
| `price_snapshots` | `stream_processor.py` | Raw price ticks from CoinGecko |
| `social_signals` | `stream_processor.py` | Raw Telegram messages + FinBERT vibe scores |
| `decoupling_signals` | `stream_processor.py` | Computed ΔP, ΔV, M_hype, alert status |

All three tables share `ticker` and `timestamp` as join keys. `decoupling_signals` is the primary table read by the dashboard — it is derived from the in-memory sliding windows, not by SQL-joining the raw tables.

### Phase 5 — The Face (Real-Time UI)

A **React + Vite + Tailwind CSS** dashboard queries MotherDuck continuously and renders:

* dual-axis live charts (price + vibe)
* a "Vibe Meter"
* flashing predictive alerts

---

## 🎯 Tracking Strategy

To reduce rate limits and avoid noisy data, GhostMarket tracks a predefined list of hype-driven targets:

```python
TARGET_TICKERS = ["bitcoin", "dogecoin"]
```

It ingests two signal types:

* **Live Financial Data**: current price for target assets
* **Live Social Data**: volume and sentiment of comments mentioning those targets

### How does it know what a comment is about?

A two-step funnel:

1. **Keyword Filtering (cheap)**: Only ingest text that explicitly mentions a target keyword/ticker
2. **Contextual NLP (smart)**: FinBERT scores the remaining text to infer bullish/bearish tone

---

## 🧮 Decoupling Math (MVP)

The MVP engine computes three streaming metrics in a **memory-efficient 5-minute window**:

### 1) Price Move ($\Delta P$)

Measures whether the market has reacted yet.

$$
\Delta P = \frac{P_{current} - P_{average}}{P_{average}}
$$

### 2) Vibe Move ($\Delta V$)

Measures the spike in human emotion.

$$
\Delta V = V_{current} - V_{average}
$$

### 3) Hype Momentum ($M_{hype}$)

A volume-aware gate to prevent low-signal false positives.

$$
M_{hype} = \Delta V \times N
$$

Where `N` is the message velocity (count) in the 5-minute window.

### 🚨 Predictive Trigger

Fire an **IMMINENT_HYPE_PUMP** alert if and only if:

* $M_{hype} > 100$  *(high volume + strong positive vibe)*
* $\Delta P < 0.02$ *(price hasn’t moved yet)*

---

## 🛠️ Tech Stack

| Technology             | Purpose           | Why it fits                             |
| ---------------------- | ----------------- | --------------------------------------- |
| Aiven Kafka            | Message broker    | Managed Kafka with SSL auth             |
| FinBERT (HuggingFace)  | NLP model         | Financial-text sentiment scoring        |
| MotherDuck             | Lakehouse / DB    | DuckDB analytics with zero ops          |
| React + Vite           | Frontend UI       | Fast modern frontend with hot reload    |
| Tailwind CSS           | Frontend styling  | Utility-first CSS for rapid UI building |

---

## 📂 Repository Structure

```text
ghostmarket/
│
├── producers/
│   ├── price_fetcher.py       # CoinGecko API fetch logic
│   ├── price_producer.py      # Kafka producer loop (uses price_fetcher.py)
│   └── social_producer.py     # Telegram -> Kafka "live-social"
│
├── processor/
│   ├── stream_processor.py    # FinBERT + thresholds + DB writes
│   ├── math_utils.py          # Sliding window + decoupling math
│   └── db.py                  # MotherDuck connection + schema + write helpers
│
├── frontend/                  # React + Vite + Tailwind CSS dashboard
│
├── requirements.txt
└── .env.example               # Template for API keys & connection strings
```

---

## ⚡ Quickstart

### 1) Clone and install

```bash
git clone https://github.com/your-team/ghostmarket.git
cd ghostmarket
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

> **Tip:** Never commit your `.env` file. Add it to `.gitignore`.

---

## 🔐 Configuration

GhostMarket expects secrets for (at minimum):

* Aiven Kafka (broker + SSL certificates)
* Telegram API (API ID + API Hash)
* MotherDuck token / connection string

If you enable X/Twitter ingestion, you'll also need X API credentials.

---

## ▶️ Running the Pipeline

Open **four terminals**:

```bash
# Terminal 1: Price ingestion
python producers/price_producer.py
```

```bash
# Terminal 2: Social ingestion
python producers/social_producer.py
```

```bash
# Terminal 3: Stream processor (FinBERT + thresholds)
python processor/stream_processor.py
```

```bash
# Terminal 4: API server (first)
python frontend/api_server.py
```

```bash
# Terminal 5: Dashboard (first time only: npm install)
cd frontend
npm install   # first time only
npm run dev
```

> The dashboard reflects data **in real time** — every time a Kafka message is processed and written to MotherDuck, the frontend updates immediately. There is no fixed refresh interval.

---

## 📊 Dashboard Preview
<img width="1920" height="1448" alt="ghostmarket_ui" src="https://github.com/user-attachments/assets/5d63ac85-832e-42e8-ad4b-319fdf6be9ee" />

---

## 🚀 Roadmap (Post-Hackathon)

### Concept drift-aware detection

Hardcoded thresholds (e.g., $M_{hype} > 100$) work for an MVP, but real markets drift:

* What counts as “big hype” varies by asset
* A threshold that’s huge for a small coin can be noise for BTC

**Next step:** replace fixed rules with **online ML** using `river`:

* Train continuously on the stream via `learn_one()`
* Use streaming anomaly detection (e.g., Half-Space Trees)
* Learn a unique baseline per asset without batch retraining

---

## 🔮 Future Improvements

### Data Sources
- Add X/Twitter feed alongside Telegram for broader sentiment coverage
- Add Reddit (r/CryptoCurrency, r/Bitcoin) as a third social source
- Expand to more tickers (Solana, Ethereum, etc.)

### Signal Quality
- Replace simple keyword/alias matching with NER (Named Entity Recognition) for more accurate ticker detection
- Fine-tune FinBERT on crypto-specific language ("gm", "wagmi", "rekt", etc.)
- Deduplicate repeated messages from same author within a time window to prevent artificial vibe inflation

### Architecture
- Replace manual poll loop with proper Quix Streams stateful processing for horizontal scaling
- Add a dead letter queue for malformed Kafka messages
- Add Prometheus + Grafana monitoring for pipeline health

### Alerting
- Push alerts to Telegram/Discord bot instead of just logging
- Add more alert types (e.g. `PANIC_CRASH`, `WHALE_ACTIVITY`)
- Tune `M_hype` and `ΔP` thresholds per ticker based on historical volatility
