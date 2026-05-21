#!/usr/bin/env python3
"""Fetch 30+ crypto pairs from Binance API."""
import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

OUTPUT_DIR = Path("data/crypto_binance")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUTPUT_DIR / "crypto_daily.parquet"

# Top 30 crypto pairs
PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
    'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
    'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'ETCUSDT',
    'XLMUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT',
    'ICPUSDT', 'XMRUSDT', 'NEARUSDT', 'FTMUSDT', 'HBARUSDT',
    'APTUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'STXUSDT',
]


def fetch_binance_daily(symbol):
    cache = OUTPUT_DIR / f"{symbol}.parquet"
    if cache.exists():
        try:
            df = pd.read_parquet(cache)
            if len(df) > 100:
                return (symbol, len(df), 'cached')
        except:
            pass

    all_data = []
    end_ms = int(pd.Timestamp('2026-05-20').timestamp() * 1000)
    start_ms = int(pd.Timestamp('2017-01-01').timestamp() * 1000)
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
            time.sleep(0.1)
        except:
            break

    if not all_data or len(all_data) < 10:
        return (symbol, 0, 'failed')

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df['date'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df.set_index('date')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    df.to_parquet(cache)
    return (symbol, len(df), 'fetched')


def main():
    print(f"Fetching {len(PAIRS)} crypto pairs from Binance...")

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_binance_daily, sym): sym for sym in PAIRS}
        completed = 0
        for future in as_completed(futures):
            sym, rows, status = future.result()
            results.append((sym, rows, status))
            completed += 1
            if status == 'fetched':
                print(f"  {sym}: {rows} rows")
            if completed % 10 == 0:
                success = sum(1 for _, _, s in results if s != 'failed')
                print(f"    Progress: {completed}/{len(PAIRS)} | Success: {success}")

    # Combine
    print("\nCombining...")
    date_range = pd.date_range('2017-01-01', '2026-05-20', freq='D')
    combined = pd.DataFrame(index=date_range)
    combined.index.name = 'date'

    success_count = 0
    for sym, rows, status in results:
        if status == 'failed':
            continue
        try:
            df = pd.read_parquet(OUTPUT_DIR / f"{sym}.parquet")
            combined[sym.replace('USDT', '').lower()] = df['close']
            success_count += 1
        except:
            pass

    combined = combined.ffill()
    combined.to_parquet(OUTPUT)

    real = [c for c in combined.columns if combined[c].notna().sum() > 100]
    print(f"\nSaved: {OUTPUT}")
    print(f"Rows: {len(combined)}")
    print(f"Real columns: {len(real)}")
    print(f"Failed: {len(PAIRS) - success_count}")


if __name__ == "__main__":
    main()
