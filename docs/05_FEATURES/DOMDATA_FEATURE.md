---
doc_type: feature
system: Dominion
ragd_priority: 7
audience:
  - developer
  - maintainer
status: operational
last_reviewed: 2026-05-19
tags:
  - feature
  - data-pipeline
  - mt5
  - real-time
---

# MT5 Real-Time Bridge (domdata)

**One-line summary:** Real-time tick ingestion from MetaTrader 5 via domdata CLI.

---

## Overview

**Purpose:**
Bridge between MetaTrader 5 (MT5) platform and Dominion V2 data pipeline for real-time tick data.

**Status:**
- Operational (Phase 2)
- 4/4 tests passing
- Latency: <100ms (tick → database)

**Related Features:**
- [[MULTI_SOURCE_FUSION]] — Fuses MT5 with other sources (Yahoo, FRED, AV, COT)
- [[TRUST_SCORING_SYSTEM]] — Assigns dynamic trust score to MT5 feed
- [[FEATURE_GENERATION_PIPELINE]] — Consumes MT5 ticks for feature computation

---

## Architecture

**Components:**
1. **MT5 Platform** — Futures broker platform (desktop app)
2. **domdata CLI** — Python CLI tool, bridges MT5 ↔ Dominion
3. **MQL5 Expert Advisor (EA)** — Script running in MT5, exports ticks
4. **CSV Export** — domdata exports MT5 ticks to CSV
5. **Pipeline Ingestion** — Dominion reads CSV, ingests into DuckDB

**Data Flow:**
```
MT5 (tick stream)
  → Expert Advisor (MQL5 script)
    → domdata CLI (Python)
      → CSV file (ticks/SYMBOL_YYYYMMDD.csv)
        → Dominion data_pipeline.cli ingest
          → DuckDB (gold_master table)
            → Feature generation (400+ features)
```

---

## API / CLI

**Installation:**
```bash
pip install git+https://github.com/USERNAME/domdata.git
```

**Configuration:**
```bash
# Copy example config
cp secrets/mt5.env.example secrets/mt5.env

# Edit secrets/mt5.env (never commit!)
MT5_LOGIN=12345678
MT5_PASSWORD=secret
MT5_SERVER=BrokerName-Live
MT5_PATH=/path/to/MT5/terminal64.exe
```

**CLI Commands:**
```bash
# Start real-time tick capture
domdata capture GC=F --duration 1h --output ticks/

# Export historical ticks
domdata export GC=F --start 2026-01-01 --end 2026-01-31 --output ticks/

# Check connection status
domdata status

# List available symbols
domdata symbols
```

**Python API:**
```python
from domdata import MT5Client

# Connect to MT5
client = MT5Client(
    login=12345678,
    password="secret",
    server="BrokerName-Live"
)

# Subscribe to ticks
for tick in client.stream_ticks("GC=F"):
    print(f"{tick.time}: {tick.bid}/{tick.ask}, vol={tick.volume}")

# Get historical ticks
ticks = client.get_ticks("GC=F", start="2026-01-01", end="2026-01-31")
```

---

## Data Format

**CSV Output (ticks/GC_20260519.csv):**
```csv
timestamp,symbol,bid,ask,last,volume,flags
2026-05-19 09:30:00.123,GC=F,2345.60,2345.62,2345.61,100,2
2026-05-19 09:30:00.456,GC=F,2345.61,2345.63,2345.62,50,2
...
```

**Fields:**
- `timestamp` — UTC timestamp (microsecond precision)
- `symbol` — Futures symbol (GC=F, SI=F, etc.)
- `bid` — Bid price
- `ask` — Ask price
- `last` — Last trade price
- `volume` — Tick volume (number of ticks, not contracts)
- `flags` — MT5 flags (2=bid/ask update, 4=last trade)

**DuckDB Schema (gold_master table):**
```sql
CREATE TABLE gold_master (
    timestamp TIMESTAMP PRIMARY KEY,
    symbol VARCHAR,
    source VARCHAR,  -- 'mt5'
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE,      -- Computed: (bid + ask) / 2
    last DOUBLE,
    volume DOUBLE,
    trust_score DOUBLE  -- From trust scoring system
);
```

---

## Algorithms

### 1. Tick Capture (Real-Time)

**MQL5 Expert Advisor (`domdata_export.mq5`):**
```mql5
void OnTick() {
    MqlTick tick;
    SymbolInfoTick(_Symbol, tick);
    
    // Write to CSV (buffered, flush every 100 ticks)
    string line = StringFormat("%d,%s,%.5f,%.5f,%.5f,%d,%d",
        tick.time_msc,
        _Symbol,
        tick.bid,
        tick.ask,
        tick.last,
        tick.volume,
        tick.flags
    );
    
    FileWrite(file_handle, line);
}
```

**domdata CLI (Python):**
```python
def capture_ticks(symbol, duration):
    # Launch MT5 EA (via subprocess)
    launch_mt5_ea(symbol)
    
    # Monitor CSV file (tail -f style)
    csv_path = f"ticks/{symbol}_{date.today()}.csv"
    for tick in tail_csv(csv_path, duration):
        yield tick
```

### 2. Tick Ingestion (Batch)

**Dominion Pipeline:**
```python
def ingest_mt5_ticks(csv_path):
    # Read CSV
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    
    # Compute mid
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # Add metadata
    df['source'] = 'mt5'
    df['trust_score'] = 1.0  # Initial trust (updated by trust scorer)
    
    # Insert into DuckDB
    con.execute("""
        INSERT INTO gold_master
        SELECT * FROM df
        ON CONFLICT (timestamp) DO UPDATE SET
            bid = EXCLUDED.bid,
            ask = EXCLUDED.ask,
            mid = EXCLUDED.mid,
            last = EXCLUDED.last,
            volume = EXCLUDED.volume,
            trust_score = EXCLUDED.trust_score
    """)
```

---

## Configuration

**MT5 Connection Parameters:**
```python
MT5_LOGIN = int(os.getenv('MT5_LOGIN'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = os.getenv('MT5_SERVER')
MT5_PATH = os.getenv('MT5_PATH')  # Path to terminal64.exe
```

**Capture Settings:**
```python
TICK_BUFFER_SIZE = 100        # Flush CSV every 100 ticks
RECONNECT_INTERVAL = 5        # Retry connection every 5s
MAX_RECONNECT_ATTEMPTS = 10   # Give up after 10 failures
```

**Tuning:**
- Increase `TICK_BUFFER_SIZE` for high-frequency symbols (reduce I/O)
- Decrease for low-frequency (faster flush)
- Typical: 100-1000 ticks

---

## Testing

**Test Coverage:**
- 4/4 tests passing
- Coverage: 85%

**Test Files:**
- `tests/test_mt5_client.py` — Connection, tick streaming, historical
- `tests/test_domdata_cli.py` — CLI commands (capture, export, status)

**Key Tests:**

**1. Connection Test**
```python
def test_mt5_connection():
    client = MT5Client(login=TEST_LOGIN, password=TEST_PASSWORD, server=TEST_SERVER)
    assert client.is_connected()
    client.disconnect()
```

**2. Tick Streaming Test**
```python
def test_tick_streaming():
    client = MT5Client(...)
    ticks = list(itertools.islice(client.stream_ticks("GC=F"), 10))
    assert len(ticks) == 10
    assert all(tick.bid < tick.ask for tick in ticks)
```

**3. Historical Ticks Test**
```python
def test_historical_ticks():
    client = MT5Client(...)
    ticks = client.get_ticks("GC=F", start="2026-01-01", end="2026-01-02")
    assert len(ticks) > 1000  # At least 1000 ticks per day
```

**4. CSV Ingestion Test**
```python
def test_csv_ingestion():
    # Create test CSV
    df = pd.DataFrame({
        'timestamp': [datetime.now()],
        'symbol': ['GC=F'],
        'bid': [2345.60],
        'ask': [2345.62],
        'last': [2345.61],
        'volume': [100],
        'flags': [2]
    })
    df.to_csv('test_ticks.csv', index=False)
    
    # Ingest
    ingest_mt5_ticks('test_ticks.csv')
    
    # Verify
    result = con.execute("SELECT COUNT(*) FROM gold_master WHERE source='mt5'").fetchone()
    assert result[0] == 1
```

---

## Performance

**Metrics:**
- Throughput: 1000 ticks/second (capture + write CSV)
- Latency: <100ms (tick → database)
- Memory: ~50MB (MT5 client + buffer)

**Benchmarks:**
- GC=F (gold): ~200 ticks/minute (typical)
- ES=F (S&P 500): ~2000 ticks/minute (high-frequency)
- CSV file size: ~10MB/day (GC=F)

**Bottlenecks:**
- MT5 → CSV: MQL5 file I/O (50ms per 100 ticks)
- CSV → DuckDB: pandas read_csv (20ms per 1000 ticks)
- Total: ~70ms per 100 ticks

**Optimization:**
- Batching (100-1000 ticks per flush)
- CSV compression (gzip, ~3× smaller)
- Direct TCP socket (future: bypass CSV)

---

## Dependencies

**Internal:**
- [[MULTI_SOURCE_FUSION]] — Fuses MT5 with other sources
- [[TRUST_SCORING_SYSTEM]] — Assigns trust score to MT5

**External:**
- **MetaTrader 5** — Desktop platform (required)
- **MQL5** — Scripting language (Expert Advisor)
- **MetaTrader5 Python package** — `pip install MetaTrader5`
- **pandas** — CSV parsing
- **DuckDB** — Database storage

---

## Known Limitations

### 1. MT5 Desktop Required
- MT5 must be running on local machine or Windows VM
- No cloud deployment (MT5 is desktop-only)
- **Workaround:** Use Windows VM in cloud (AWS EC2 Windows, GCP Windows)

### 2. No Order Book Depth
- MT5 provides ticks (bid/ask/last) only, no L2 order book
- [[LOB_RECONSTRUCTION_FEATURE]] uses synthetic quotes (2 bps spread)
- **Workaround:** Accept limitation, focus on 1-min+ horizons

### 3. Tick Volume ≠ Contract Volume
- MT5 tick volume = number of price updates, not actual contracts traded
- Real volume unavailable for futures
- **Workaround:** Use tick volume as proxy for activity

### 4. Connection Instability
- MT5 connection can drop (broker maintenance, internet issues)
- domdata retries 10× before giving up
- **Mitigation:** Reconnect logic, fallback to Yahoo Finance

### 5. Historical Data Limits
- MT5 historical tick data: ~3 months (broker-dependent)
- Older data unavailable
- **Workaround:** Use Yahoo Finance for older data

---

## Operational Procedures

**Daily (Automated):**
- 8:00am: domdata captures ticks (GC=F) for 16 hours
- 12:00am: domdata stops, CSV flushed

**Weekly (Manual):**
- Monday 9am: Check MT5 connection status (`domdata status`)
- Verify CSV files exist (ticks/GC_*.csv)
- Spot-check tick counts (~200 ticks/min × 960 min = 192K ticks/day)

**Incident Response:**

**Scenario 1: MT5 Connection Lost**
1. Check internet connection
2. Restart MT5 platform
3. Rerun `domdata capture`
4. If still fails: Fallback to Yahoo Finance (15-minute delay acceptable)

**Scenario 2: CSV File Missing**
1. Check MT5 EA logs (MT5/MQL5/Logs/)
2. Verify file permissions (ticks/ directory writable)
3. Manually export: `domdata export GC=F --start yesterday --end today`

**Scenario 3: Tick Count Low**
1. Check market hours (no ticks outside trading hours)
2. Verify broker connection (MT5 "Connected" status)
3. Check for broker maintenance (announcements)

---

## Security

**Secrets Management:**
- MT5 credentials in `secrets/mt5.env` (never commit!)
- `.gitignore` includes `secrets/` directory
- File permissions: `chmod 600 secrets/mt5.env`

**Safety Rules:**
- domdata is **read-only** (no trading functions)
- Expert Advisor has no `OrderSend()` calls
- Code review required before deploying new EA

**Audit:**
- All domdata commands logged (logs/domdata.log)
- MT5 connection attempts logged
- CSV exports timestamped

---

## Future Enhancements

**Planned (Phase 9):**
1. Multi-asset support (12 symbols: GC, SI, HG, CL, NG, RB, 6E, 6J, ES, NQ, ZN, ZB)
2. Direct TCP socket (bypass CSV, reduce latency to <10ms)
3. Cloud deployment (AWS EC2 Windows + MT5)

**Research (Phase 6+):**
- Order book reconstruction (use CQG/Rithmic for real L2 data)
- Volume data (switch to futures exchange data feed)

---

## Related Documentation

- [[DATA_FLOW]] — Data pipeline architecture
- [[PHASE_2]] — Multi-source fusion (includes MT5 integration)
- [[ADR_0007_read_only_mt5_architecture]] (to be created) — Safety design
- [[MULTI_SOURCE_FUSION]] — Kalman filter + trust scoring

---

## Changelog

| Date | Change | Author |
|---|---|---|
| 2025-04-01 | Initial implementation (Phase 2) | Owner |
| 2025-06-15 | Added reconnect logic (10× retry) | Owner |
| 2026-01-20 | Tested with live MT5 account (demo) | Owner |
| 2026-05-19 | Documented for Phase 5 | Agent |

---

## Notes

**domdata GitHub:** https://github.com/USERNAME/domdata (private repo)

**MT5 Broker Compatibility:**
- Tested: OANDA, Interactive Brokers, Amp Futures
- Required: MT5 account (demo or live)
- Futures access required (GC=F symbol available)

**Platform Support:**
- Windows: Native (MT5 runs natively)
- Linux: Wine (MT5 via Wine, experimental)
- macOS: Parallels/VMware (Windows VM required)
