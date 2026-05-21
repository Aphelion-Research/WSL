#!/bin/bash
# Fetch additional data sources overnight

LOG="/tmp/extra_data.log"
echo "[$(date +%H:%M:%S)] Starting extra data fetches..." | tee -a $LOG

# 1. CBOE options data (VIX term structure, SKEW, put/call ratios)
python3 << 'PYEOF' 2>&1 | tee -a $LOG
import pandas as pd
import requests
from pathlib import Path
import time

OUTPUT_DIR = Path("data/cboe_options")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# VIX term structure (approximate via VIX futures tickers)
VIX_FUTURES = ['VX1', 'VX2', 'VX3', 'VX4', 'VX5', 'VX6', 'VX7', 'VX8']

print("Fetching VIX futures for term structure...")
import yfinance as yf
for ticker in VIX_FUTURES:
    try:
        symbol = f"^{ticker}"
        df = yf.download(symbol, start='2015-01-01', progress=False)
        if len(df) > 0:
            df.to_parquet(OUTPUT_DIR / f"{ticker}.parquet")
            print(f"  {ticker}: {len(df)} rows")
    except:
        pass

# Combine
dfs = []
for f in OUTPUT_DIR.glob("VX*.parquet"):
    df = pd.read_parquet(f)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    dfs.append(df[['Close']].rename(columns={'Close': f.stem}))

if dfs:
    combined = pd.concat(dfs, axis=1)
    combined = combined.ffill()
    combined.to_parquet(OUTPUT_DIR / "vix_term_structure.parquet")
    print(f"VIX term structure: {len(combined)} rows × {len(combined.columns)} cols")
PYEOF

# 2. More commodities (metals, energy, agriculture)
python3 << 'PYEOF' 2>&1 | tee -a $LOG
import yfinance as yf
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path("data/commodities_extended")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = {
    'zinc': 'ZI=F', 'nickel': 'NI=F', 'lead': 'PL=F',
    'tin': 'TN=F', 'iron_ore': 'SCIF', 'steel': 'MT',
    'uranium': 'URA', 'lithium': 'LIT', 'rare_earth': 'REMX',
    'coal': 'KOL', 'propane': 'UGA', 'ethanol': 'CORN',
    'rice': 'RR=F', 'cocoa': 'CC=F', 'orange_juice': 'OJ=F',
    'lean_hogs': 'HE=F', 'live_cattle': 'LE=F', 'feeder_cattle': 'GF=F',
}

print("Fetching extended commodities...")
for name, ticker in TICKERS.items():
    try:
        df = yf.download(ticker, start='2015-01-01', progress=False)
        if len(df) > 100:
            df.to_parquet(OUTPUT_DIR / f"{name}.parquet")
            print(f"  {name}: {len(df)} rows")
    except:
        pass

# Combine
combined = pd.DataFrame(index=pd.date_range('2015-01-01', '2026-05-20', freq='D'))
for f in OUTPUT_DIR.glob("*.parquet"):
    df = pd.read_parquet(f)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    combined[f.stem] = df['Close']
combined = combined.ffill()
combined.to_parquet(OUTPUT_DIR / "commodities_extended.parquet")
print(f"Extended commodities: {len(combined)} rows × {len(combined.columns)} cols")
PYEOF

# 3. Currency futures (more FX pairs)
python3 << 'PYEOF' 2>&1 | tee -a $LOG
import yfinance as yf
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path("data/currency_futures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CURRENCIES = {
    'usdinr': 'INR=X', 'usdbrl': 'BRL=X', 'usdmxn': 'MXN=X',
    'usdzar': 'ZAR=X', 'usdtry': 'TRY=X', 'usdrub': 'RUB=X',
    'usdkrw': 'KRW=X', 'usdsgd': 'SGD=X', 'usdhkd': 'HKD=X',
    'eurchf': 'EURCHF=X', 'euraud': 'EURAUD=X', 'eurcad': 'EURCAD=X',
}

print("Fetching currency futures...")
for name, ticker in CURRENCIES.items():
    try:
        df = yf.download(ticker, start='2015-01-01', progress=False)
        if len(df) > 100:
            df.to_parquet(OUTPUT_DIR / f"{name}.parquet")
            print(f"  {name}: {len(df)} rows")
    except:
        pass

combined = pd.DataFrame(index=pd.date_range('2015-01-01', '2026-05-20', freq='D'))
for f in OUTPUT_DIR.glob("*.parquet"):
    df = pd.read_parquet(f)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    combined[f.stem] = df['Close']
combined = combined.ffill()
combined.to_parquet(OUTPUT_DIR / "currency_futures.parquet")
print(f"Currency futures: {len(combined)} rows × {len(combined.columns)} cols")
PYEOF

# 4. More crypto pairs from Binance
python3 << 'PYEOF' 2>&1 | tee -a $LOG
import requests
import pandas as pd
from pathlib import Path
import time

OUTPUT_DIR = Path("data/crypto_extended")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Top 50 more pairs
PAIRS = [
    'GMTUSDT', 'RUNEUSDT', 'WAVESUSDT', 'KSMUSDT', 'CHZUSDT',
    'SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'THETAUSDT', 'ENJUSDT',
    'AAVEUSDT', 'COMPUSDT', 'SNXUSDT', 'MKRUSDT', 'YFIUSDT',
    'CRVUSDT', '1INCHUSDT', 'BALUSDT', 'SUSHIUSDT', 'ZILUSDT',
    'BATUSDT', 'ZRXUSDT', 'RENUSDT', 'LRCUSDT', 'OMGUSDT',
    'XTZUSDT', 'DASHUSDT', 'ZECUSDT', 'QTUMUSDT', 'ONTUSDT',
]

def fetch_binance_daily(symbol):
    all_data = []
    end_ms = int(pd.Timestamp('2026-05-20').timestamp() * 1000)
    start_ms = int(pd.Timestamp('2020-01-01').timestamp() * 1000)
    current = start_ms

    while current < end_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&startTime={current}&limit=1000"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            all_data.extend(data)
            current = data[-1][0] + 1
            time.sleep(0.15)
        except:
            break
    return all_data

print("Fetching extended crypto pairs...")
for pair in PAIRS:
    data = fetch_binance_daily(pair)
    if len(data) > 10:
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df['date'] = pd.to_datetime(df['open_time'], unit='ms')
        df = df.set_index('date')
        for col in ['close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.to_parquet(OUTPUT_DIR / f"{pair}.parquet")
        print(f"  {pair}: {len(df)} rows")

combined = pd.DataFrame(index=pd.date_range('2020-01-01', '2026-05-20', freq='D'))
for f in OUTPUT_DIR.glob("*.parquet"):
    df = pd.read_parquet(f)
    combined[f.stem.replace('USDT', '').lower()] = df['close']
combined = combined.ffill()
combined.to_parquet(OUTPUT_DIR / "crypto_extended.parquet")
print(f"Extended crypto: {len(combined)} rows × {len(combined.columns)} cols")
PYEOF

echo "[$(date +%H:%M:%S)] Extra data fetches complete" | tee -a $LOG
