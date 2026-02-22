# 🗺️ GhostMarket: Detailed Implementation Plan

Based on the README, here is a comprehensive, step-by-step breakdown of the entire system.

---

## 📦 Phase 0 — Project Setup & Environment

**Purpose:** Establish the foundation before writing any pipeline code.

### Steps:
1. **Clone the repo** and create a Python virtual environment
2. **Install dependencies** via `requirements.txt`, which will include:
   - `confluent-kafka` (Aiven Kafka client)
   - `telethon` (Telegram client)
   - `transformers` + `torch` (FinBERT)
   - `duckdb` (MotherDuck)
   - `python-dotenv` (secrets management)
   - `requests` (CoinGecko)
   - `streamlit` + `plotly` (dashboard)
3. **Configure `.env`** with all secrets:
   ```env
   BOOTSTRAP_SERVERS=
   KAFKA_SSL_CA=certs_for_aiven_kafka_online/ca.pem
   KAFKA_SSL_CERT=certs_for_aiven_kafka_online/service.cert
   KAFKA_SSL_KEY=certs_for_aiven_kafka_online/service.key
   TELEGRAM_API_ID=
   TELEGRAM_API_HASH=
   MOTHERDUCK_TOKEN=
   COINGECKO_API_KEY=
   ```
4. **Create Kafka topics** on Aiven console:
   - `bitcoin`
   - `dogecoin`
   - `live-social`

---

## 🔁 Phase 1 — Data Ingestion Layer (Producers)

### 1A. `producers/price_fetcher.py` + `producers/price_producer.py`

**Purpose:** Split into two files for clarity and independent testability:
- `price_fetcher.py` — handles only the CoinGecko API call (testable without Kafka)
- `price_producer.py` — handles only the Kafka producing loop (imports from `price_fetcher.py`)

#### Work — `price_fetcher.py`:
1. Load `COINGECKO_API_KEY` from `.env`
2. Configure the API call targeting multiple assets in **one request**:
   ```
   GET https://api.coingecko.com/api/v3/simple/price
       ?ids=bitcoin,dogecoin
       &vs_currencies=usd
   Headers:
       x-cg-demo-api-key: <your_key>
       accept: application/json
   ```
3. Implement a `fetch_prices()` function:
   - Wraps the `requests.get()` call
   - Calls `response.raise_for_status()` to catch HTTP errors (4xx / 5xx)
   - Returns parsed JSON or `None` on failure
4. Expose `TARGET_TICKERS` as a module-level constant for reuse
5. Run standalone (`if __name__ == "__main__"`) to test fetching without Kafka

#### Work — `price_producer.py`:
1. Import `fetch_prices` and `TARGET_TICKERS` from `price_fetcher`
2. For each asset in the response, build a structured Kafka message:
   ```json
   {
     "ticker": "bitcoin",
     "price_usd": 62450.00,
     "timestamp": "2026-02-21T10:05:00Z"
   }
   ```
3. **Produce** each message to Kafka topic `live-prices`
4. Run in a `while True` loop with **`time.sleep(60)`**:

   > ⚠️ **Rate Limit Note:** The CoinGecko **Demo API key** enforces strict rate limits.
   > The poll interval is set to **60 seconds** (not 5 seconds as originally planned)
   > to avoid hitting `429 Too Many Requests`. This is a hard constraint of the free tier.

   ```python
   while True:
       data = fetch_prices()
       if data:
           for ticker, values in data.items():
               message = {
                   "ticker": ticker,
                   "price_usd": values["usd"],
                   "timestamp": datetime.utcnow().isoformat()
               }
               producer.produce("live-prices", json.dumps(message))
       time.sleep(60)
   ```

---

### 1B. `producers/social_producer.py`

**Purpose:** Continuously ingest raw social text mentioning target assets and push to Kafka.

#### Work:
1. Initialize a **Telethon Telegram client** (async event-driven mode)
2. Subscribe to target public Telegram groups: `binanceexchange`, `CryptoComOfficial`, `dogecoin_official`
3. Listen for new messages in real time via `@client.on(events.NewMessage)`
4. Apply **Alias-aware Keyword Filter** (cheap gate):
   - Maintain a `TICKER_ALIASES` dict mapping typos and short forms to canonical tickers (e.g., `"btc"` → `"bitcoin"`, `"doge"` → `"dogecoin"`)
   - Use `detect_tickers()` to split text into words, strip punctuation, and match against aliases
   - Discard if no match → reduces volume significantly
5. For matching messages, build a structured message:
   ```json
   {
     "source": "telegram",
     "timestamp": 1740134400.0,
     "text": "btc to the moon!",
     "tickers": ["bitcoin"],
     "author": "123456789"
   }
   ```
6. **Produce** to Kafka topic `live-social`

---

## 🛣️ Phase 2 — Message Broker (Aiven Kafka)

**Purpose:** Act as the durable, time-ordered buffer between producers and consumers. Decouples ingestion speed from processing speed.

#### Work:
1. **Partition topics** by ticker (e.g., all `"bitcoin"` messages go to the same partition) → guarantees ordering per asset
2. Kafka retains messages, so if the processor crashes/restarts, it can **resume from offset** without data loss
3. Both producers write concurrently with **no coordination needed** — Kafka handles the fan-in
4. SSL certificate authentication is handled by `import_me_to_use_kafka_stuff.py` — producers simply call `send_string_to_kafka_topic(topic, payload)`

> ⚠️ **Timing Implication:** Because price data now arrives every **60 seconds** instead of 5,
> the sliding window math in Phase 3 will have sparser price data points.
> The `SlidingWindow` for prices effectively holds ~5 samples per 5-minute window
> instead of ~60. This is still valid but reduces price-side resolution.

---

## 🧠 Phase 3 — Stream Processing & Threshold Engine

### 3A. `processor/math_utils.py`

**Purpose:** Provide memory-efficient sliding window calculations.

#### Work:
1. Implement a **`SlidingWindow`** class using Python's `collections.deque` with `maxlen`:
   - Automatically evicts data older than 5 minutes → **O(1) memory**
2. Expose methods:
   - `add(value, timestamp)` — append new data point
   - `average()` — compute rolling mean
   - `count()` — message velocity (N)
3. Implement the **three decoupling metrics**:

   | Metric | Formula | Purpose |
   |--------|---------|---------|
   | `delta_price` (ΔP) | `(P_current - P_avg) / P_avg` | Has market reacted? |
   | `delta_vibe` (ΔV) | `V_current - V_avg` | Emotional spike magnitude |
   | `hype_momentum` (M) | `ΔV × N` | Volume-gated hype signal |

4. Implement **alert trigger logic**:
   ```python
   def check_alert(M_hype, delta_P):
       if M_hype > 100 and delta_P < 0.02:
           return "IMMINENT_HYPE_PUMP"
       return None
   ```

---

### 3B. `processor/stream_processor.py`

**Purpose:** The core brain — consumes from Kafka, scores sentiment, computes metrics, writes to DB, triggers alerts.

#### Work:
1. **Initialize Quix Streams consumer** subscribed to both `live-prices` and `live-social`
2. **Load FinBERT model** from HuggingFace on startup:
   ```python
   # ProsusAI/finbert — trained on financial text
   model = pipeline("sentiment-analysis", model="ProsusAI/finbert")
   ```
3. **Maintain per-ticker state** (one sliding window per asset):
   ```python
   state = {
     "bitcoin": { "price_window": deque(), "vibe_window": deque() },
     "dogecoin": { ... }
   }
   ```
4. **Route incoming Kafka messages**:
   - If from `live-prices` → update `price_window` for that ticker
   - If from `live-social` → run FinBERT, get a score in `[-1.0, +1.0]`, update `vibe_window`
5. **FinBERT scoring**:
   - Input: raw comment text
   - Output: `{ label: "positive", score: 0.92 }` → map to `+0.92`
   - Labels: `positive → +score`, `negative → -score`, `neutral → 0`
6. **After each update**, compute ΔP, ΔV, M_hype and run alert check
7. **Write every processed record to MotherDuck**

---

## 🗄️ Phase 4 — Data Lakehouse (MotherDuck / DuckDB)

**Purpose:** Persist every processed event for querying by the dashboard.

#### Work:
1. **Connection** via `processor/db.py`:
   ```python
   con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
   con.execute("USE ghostmarket")
   ```

2. **Create three tables** on MotherDuck (all created by `init_schema()` on startup):

   **Table 1: `price_snapshots`** — raw price ticks from CoinGecko
   ```sql
   CREATE TABLE IF NOT EXISTS price_snapshots (
       ticker      TEXT,
       price_usd   DOUBLE,
       timestamp   DOUBLE,
       ingested_at TIMESTAMP DEFAULT now()
   )
   ```

   **Table 2: `social_signals`** — raw Telegram messages post-FinBERT scoring
   ```sql
   CREATE TABLE IF NOT EXISTS social_signals (
       ticker      TEXT,
       vibe_score  DOUBLE,
       text        TEXT,
       author      TEXT,
       source      TEXT,
       timestamp   DOUBLE,
       ingested_at TIMESTAMP DEFAULT now()
   )
   ```

   **Table 3: `decoupling_signals`** — computed metrics output from stream processor
   ```sql
   CREATE TABLE IF NOT EXISTS decoupling_signals (
       ticker          TEXT,
       timestamp       DOUBLE,
       price_current   DOUBLE,
       price_avg       DOUBLE,
       vibe_current    DOUBLE,
       vibe_avg        DOUBLE,
       delta_price     DOUBLE,
       delta_vibe      DOUBLE,
       hype_momentum   DOUBLE,
       alert           TEXT,       -- NULL or 'IMMINENT_HYPE_PUMP'
       recorded_at     TIMESTAMP DEFAULT now()
   )
   ```

3. **How the three tables link together:**

   All three tables share `ticker` and `timestamp` as the join keys.

   ```
   price_snapshots                    social_signals
        |                                   |
        | ticker + timestamp                | ticker + timestamp
        └──────────────┬────────────────────┘
                       ↓
              decoupling_signals
          (derived from both above via
           sliding window math in
           stream_processor.py)
   ```

   - `price_snapshots` and `social_signals` are **raw input tables** — written directly by `stream_processor.py` as messages arrive from Kafka
   - `decoupling_signals` is the **computed output table** — written after every poll cycle using values from the in-memory `SlidingWindow` (not by joining the raw tables directly)
   - The dashboard (`frontend/app.py`) primarily reads from `decoupling_signals` for charts and alerts, and can optionally query `social_signals` to show raw message text

4. **Write helpers** in `processor/db.py`:
   - `insert_price(con, ticker, price_usd, timestamp)` → writes to `price_snapshots`
   - `insert_social(con, ticker, vibe_score, text, author, source, timestamp)` → writes to `social_signals`
   - `insert_signal(con, signal)` → writes to `decoupling_signals`

5. **Dashboard query** (reads from `decoupling_signals`):
   ```sql
   SELECT * FROM decoupling_signals
   WHERE timestamp > epoch(NOW()) - 600
   ORDER BY timestamp DESC
   ```

---

## 📊 Phase 5 — Real-Time Dashboard (`frontend/`)

**Purpose:** Visualize decoupling events and alert users in real time.

#### Work:
1. **Start `api_server.py`** first — this exposes MotherDuck data as REST endpoints for the React app to consume
2. **Install frontend dependencies** (first time only):
   ```bash
   cd frontend
   npm install
   ```
3. **Start the dev server**:
   ```bash
   npm run dev
   ```
4. **Real-time updates** — the dashboard does NOT poll on a fixed interval. Instead:
   - Every Kafka message processed → immediately written to MotherDuck via `db.py`
   - Frontend listens for updates and re-renders as soon as new data arrives
5. **Query recent data**:
   ```sql
   SELECT * FROM decoupling_signals
   WHERE timestamp > epoch(NOW()) - 600
   ORDER BY timestamp DESC
   ```
6. **Render components**:

   | Component | Data Used | Purpose |
   |-----------|-----------|---------|
   | **Dual-axis line chart** | `price_usd` + `vibe_score` vs `timestamp` | Visualize decoupling visually |
   | **Vibe Meter** | Latest `vibe_score` | Instant emotional gauge |
   | **Alert banner** | `alert == 'IMMINENT_HYPE_PUMP'` | Flashing warning when triggered |
   | **Ticker selector** | All active tickers | Filter per asset |

7. Built with **React + Vite** for fast development and hot reload
8. Styled with **Tailwind CSS** for utility-first rapid UI building
9. Use a charting library (e.g., **Recharts** or **Chart.js**) for dual-axis charts

---

## 🔄 Full Data Flow Summary

```
Telegram Groups                 CoinGecko (Demo API)
   |                                    |
   | real-time messages           GET /simple/price
   | (event-driven)               every 60s (rate limit)
   ↓                                    ↓
[social_producer.py]          [price_fetcher.py]
  alias-aware keyword filter   fetch_prices()
  detect_tickers()             raise_for_status()
  build JSON payload                   |
                              [price_producer.py]
                               Kafka produce loop
       |                             |
       ↓                             ↓
   [Aiven Kafka]  ←————————————————┘
   live-social topic           bitcoin / dogecoin topics
   (partitioned by ticker)     (partitioned by ticker)
            |
            ↓
   [stream_processor.py]
      ├── FinBERT: text → vibe score [-1, +1]
      ├── SlidingWindow: rolling 5-min memory (deque)
      │     price window: ~5 samples per 5 min (60s cadence)
      │     vibe window:  high-frequency (per message)
      ├── Math: ΔP, ΔV, M_hype
      └── Alert: M_hype > 100 AND ΔP < 0.02?
            ↓
      [MotherDuck] — all signals persisted immediately
            ↓
      [api_server.py] — REST API over MotherDuck
            ↓
      [React + Vite + Tailwind CSS]
         updates in real time as data arrives
         live charts, vibe meter, alerts
```

---

## 🗂️ File Creation Checklist

| File | Status | Key Dependencies |
|------|--------|-----------------|
| `.env` | Configure first | All external services + `COINGECKO_API_KEY` |
| `requirements.txt` | Create early | Everything |
| `producers/price_fetcher.py` | Phase 1A | `requests`, `python-dotenv` |
| `producers/price_producer.py` | Phase 1A | `confluent-kafka`, `price_fetcher`, `import_me_to_use_kafka_stuff` |
| `producers/social_producer.py` | Phase 1B | `telethon`, `import_me_to_use_kafka_stuff` |
| `processor/math_utils.py` | Phase 3A | `collections.deque` |
| `processor/stream_processor.py` | Phase 3B | `quixstreams`, `transformers`, `duckdb` |
| `frontend/app.py` | Phase 5 | `streamlit`, `plotly`, `duckdb` |

---

## ⚠️ Key Engineering Decisions to Make

1. **CoinGecko Demo rate limit** — poll interval is locked at **60s minimum**; upgrade to a paid plan if lower latency price data is needed
2. **FinBERT is CPU-heavy** — consider batching social messages or using a GPU if throughput is high
3. **Window size is fixed at 5 min** — with 60s price cadence this gives ~5 price points; make window size configurable if needed
4. **Alert deduplication** — add a cooldown timer so one event doesn't fire 100 alerts
5. **Kafka consumer group ID** — set explicitly so restarts resume from last committed offset
6. **Error handling in `fetch_prices()`** — `raise_for_status()` catches HTTP errors; wrap in try/except to log and continue the loop without crashing
7. **Test fetching independently** — run `python producers/price_fetcher.py` directly to verify CoinGecko responses without needing Kafka running