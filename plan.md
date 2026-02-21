# 🗺️ GhostMarket: Detailed Implementation Plan

Based on the README, here is a comprehensive, step-by-step breakdown of the entire system.

---

## 📦 Phase 0 — Project Setup & Environment

**Purpose:** Establish the foundation before writing any pipeline code.

### Steps:
1. **Clone the repo** and create a Python virtual environment
2. **Install dependencies** via `requirements.txt`, which will include:
   - `confluent-kafka` or `kafka-python` (Upstash Kafka client)
   - `quixstreams` (stream processor)
   - `transformers`, `torch` (FinBERT/HuggingFace)
   - `praw` (Reddit API)
   - `duckdb`, `motherduck` (lakehouse)
   - `streamlit`, `plotly` (dashboard)
   - `requests` (CoinGecko polling)
   - `python-dotenv` (secrets management)
3. **Configure `.env`** with all secrets:
   ```env
   UPSTASH_KAFKA_BROKER=
   UPSTASH_KAFKA_USERNAME=
   UPSTASH_KAFKA_PASSWORD=
   REDDIT_CLIENT_ID=
   REDDIT_CLIENT_SECRET=
   REDDIT_USER_AGENT=
   MOTHERDUCK_TOKEN=
   ```
4. **Create Kafka topics** on Upstash console:
   - `live-prices`
   - `live-social`

---

## 🔁 Phase 1 — Data Ingestion Layer (Producers)

### 1A. `producers/price_producer.py`

**Purpose:** Continuously poll live asset prices and push them into Kafka.

#### Work:
1. Load target tickers from config: `["bitcoin", "dogecoin", "gamestop"]`
2. Every **5 seconds**, call the **CoinGecko API**:
   ```
   GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,dogecoin&vs_currencies=usd
   ```
3. For each asset, build a structured message:
   ```json
   {
     "ticker": "bitcoin",
     "price_usd": 62450.00,
     "timestamp": "2026-02-21T10:05:00Z"
   }
   ```
4. **Serialize** to JSON and **produce** to Kafka topic `live-prices`
5. Handle API rate limits and network errors gracefully

---

### 1B. `producers/social_producer.py`

**Purpose:** Continuously ingest raw social text mentioning target assets and push to Kafka.

#### Work:
1. Initialize a **PRAW Reddit client** (async streaming mode)
2. Subscribe to target subreddits: `r/wallstreetbets`, `r/CryptoCurrency`, etc.
3. Stream all new comments/posts in real time
4. Apply **Keyword Filter** (cheap gate):
   - Check if comment text mentions any target ticker or keyword (e.g., `"bitcoin"`, `"BTC"`, `"DOGE"`)
   - Discard if no match → reduces volume significantly
5. For matching comments, build a structured message:
   ```json
   {
     "ticker": "bitcoin",
     "text": "BTC is going to moon, I'm buying more!",
     "source": "reddit",
     "subreddit": "wallstreetbets",
     "timestamp": "2026-02-21T10:05:02Z"
   }
   ```
6. **Produce** to Kafka topic `live-social`

---

## 🛣️ Phase 2 — Message Broker (Upstash Kafka)

**Purpose:** Act as the durable, time-ordered buffer between producers and consumers. Decouples ingestion speed from processing speed.

#### Work:
1. **Partition topics** by ticker (e.g., all `"bitcoin"` messages go to the same partition) → guarantees ordering per asset
2. Kafka retains messages, so if the processor crashes/restarts, it can **resume from offset** without data loss
3. Both producers write concurrently with **no coordination needed** — Kafka handles the fan-in

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
1. **Create table schema** on MotherDuck:
   ```sql
   CREATE TABLE market_signals (
     timestamp     TIMESTAMPTZ,
     ticker        VARCHAR,
     price_usd     DOUBLE,
     vibe_score    DOUBLE,
     msg_velocity  INTEGER,
     delta_price   DOUBLE,
     delta_vibe    DOUBLE,
     hype_momentum DOUBLE,
     alert_status  VARCHAR   -- NULL or 'IMMINENT_HYPE_PUMP'
   );
   ```
2. Stream processor uses DuckDB Python client to **`INSERT`** a row after each processed event
3. Dashboard queries this table using **DuckDB SQL** directly from Python

---

## 📊 Phase 5 — Real-Time Dashboard (`frontend/app.py`)

**Purpose:** Visualize decoupling events and alert users in real time.

#### Work:
1. **Connect to MotherDuck** using token from `.env`
2. Use `st.experimental_rerun()` or `time.sleep()` loop to **auto-refresh** every few seconds
3. **Query recent data**:
   ```sql
   SELECT * FROM market_signals
   WHERE timestamp > NOW() - INTERVAL '10 minutes'
   ORDER BY timestamp DESC
   ```
4. **Render components**:

   | Component | Data Used | Purpose |
   |-----------|-----------|---------|
   | **Dual-axis line chart** | `price_usd` + `vibe_score` vs `timestamp` | Visualize decoupling visually |
   | **Vibe Meter** | Latest `vibe_score` | Instant emotional gauge |
   | **Alert banner** | `alert_status == 'IMMINENT_HYPE_PUMP'` | Flashing warning when triggered |
   | **Ticker selector** | All active tickers | Filter per asset |

5. Use **Plotly** for dual-axis charts (price on left Y-axis, vibe on right Y-axis)

---

## 🔄 Full Data Flow Summary

```
Reddit/CoinGecko
      ↓
  [Producers] — keyword filter, polling
      ↓
  [Upstash Kafka] — partitioned, time-ordered
      ↓
  [Quix Streams Consumer]
      ├── FinBERT: text → vibe score [-1, +1]
      ├── SlidingWindow: rolling 5-min memory (deque)
      ├── Math: ΔP, ΔV, M_hype
      └── Alert: M_hype > 100 AND ΔP < 0.02?
            ↓
      [MotherDuck] — all signals persisted
            ↓
      [Streamlit] — live charts, vibe meter, alerts
```

---

## 🗂️ File Creation Checklist

| File | Status | Key Dependencies |
|------|--------|-----------------|
| `.env` | Configure first | All external services |
| `requirements.txt` | Create early | Everything |
| `producers/price_producer.py` | Phase 1A | `requests`, `kafka` |
| `producers/social_producer.py` | Phase 1B | `praw`, `kafka` |
| `processor/math_utils.py` | Phase 3A | `collections.deque` |
| `processor/stream_processor.py` | Phase 3B | `quixstreams`, `transformers`, `duckdb` |
| `frontend/app.py` | Phase 5 | `streamlit`, `plotly`, `duckdb` |

---

## ⚠️ Key Engineering Decisions to Make

1. **FinBERT is CPU-heavy** — consider batching social messages or using a GPU if throughput is high
2. **Window size is fixed at 5 min** — make it configurable per ticker via config file
3. **Alert deduplication** — add a cooldown timer so one event doesn't fire 100 alerts
4. **Kafka consumer group ID** — set explicitly so restarts resume from last committed offset