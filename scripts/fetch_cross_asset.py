"""Fetch cross-asset daily data from Yahoo Finance."""
import yfinance as yf
import pandas as pd
import requests
from pathlib import Path
import time
import warnings
warnings.filterwarnings('ignore')

CROSS_DIR = Path("data/cross_asset")
CROSS_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = {
    'dxy': 'DX-Y.NYB',
    'eurusd': 'EURUSD=X',
    'usdjpy': 'USDJPY=X',
    'gbpusd': 'GBPUSD=X',
    'audusd': 'AUDUSD=X',
    'usdchf': 'USDCHF=X',
    'usdcad': 'USDCAD=X',
    'usdcnh': 'USDCNH=X',
    'silver': 'SI=F',
    'copper': 'HG=F',
    'platinum': 'PL=F',
    'palladium': 'PA=F',
    'spx': '^GSPC',
    'nasdaq': '^IXIC',
    'russell': '^RUT',
    'vix': '^VIX',
    'gvz': '^GVZ',
    'tlt': 'TLT',
    'hyg': 'HYG',
    'lqd': 'LQD',
    'ief': 'IEF',
    'wti': 'CL=F',
    'brent': 'BZ=F',
    'natgas': 'NG=F',
    'btc': 'BTC-USD',
    'eth': 'ETH-USD',
    'gld': 'GLD',
}

ALTERNATIVES = {
    'dxy': ['^DXY', 'UUP'],
    'silver': ['XAGUSD=X', 'SLV'],
    'gvz': ['^GVZ'],
}


def fetch_ticker(name, symbol):
    cache_file = CROSS_DIR / f"{name}.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if len(df) > 100:
            return df

    try:
        df = yf.download(symbol, start='2015-01-01', end='2026-05-21',
                         auto_adjust=True, progress=False)
        if df is not None and len(df) > 100:
            df.to_parquet(cache_file)
            return df
    except Exception:
        pass

    # Try alternatives
    if name in ALTERNATIVES:
        for alt in ALTERNATIVES[name]:
            try:
                df = yf.download(alt, start='2015-01-01', end='2026-05-21',
                                 auto_adjust=True, progress=False)
                if df is not None and len(df) > 100:
                    df.to_parquet(cache_file)
                    return df
            except Exception:
                continue

    return None


def fetch_binance_daily(symbol, name):
    """Fetch daily klines from Binance."""
    cache_file = CROSS_DIR / f"{name}_binance.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)

    all_data = []
    end_time = int(pd.Timestamp('2026-05-20').timestamp() * 1000)
    start_time = int(pd.Timestamp('2017-01-01').timestamp() * 1000)

    current = start_time
    while current < end_time:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&startTime={current}&limit=1000"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if not data:
                    break
                all_data.extend(data)
                current = data[-1][0] + 1
                time.sleep(0.2)
            else:
                break
        except Exception:
            break

    if all_data:
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
        df.columns = [c.capitalize() for c in df.columns]
        df.to_parquet(cache_file)
        return df
    return None


def main():
    results = {}
    failed = []

    for name, symbol in TICKERS.items():
        df = fetch_ticker(name, symbol)
        if df is not None and len(df) > 100:
            results[name] = df
            print(f"  {name}: {len(df)} rows ({df.index.min().date()} to {df.index.max().date()})")
        else:
            failed.append(name)
            print(f"  {name}: FAILED")
        time.sleep(0.2)

    # Binance fallback for crypto
    for sym, name in [('BTCUSDT', 'btc'), ('ETHUSDT', 'eth')]:
        if name in failed or (name in results and len(results[name]) < 500):
            df = fetch_binance_daily(sym, name)
            if df is not None and len(df) > 100:
                results[name] = df
                if name in failed:
                    failed.remove(name)
                print(f"  {name} (binance): {len(df)} rows")

    # Build combined daily close prices
    print("\nBuilding combined cross-asset dataset...")
    date_range = pd.date_range('2015-01-01', '2026-05-20', freq='D')
    combined = pd.DataFrame(index=date_range)
    combined.index.name = 'date'

    for name, df in results.items():
        df.index = pd.to_datetime(df.index).tz_localize(None)
        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if 'Close' in df.columns:
            series = df['Close'].rename(name)
        elif 'close' in df.columns:
            series = df['close'].rename(name)
        else:
            continue
        combined[name] = series

    combined = combined.ffill()
    combined.to_parquet(CROSS_DIR / "cross_asset_daily.parquet")

    real_cols = [c for c in combined.columns if combined[c].notna().sum() > 100]
    print(f"Cross-asset daily: {len(combined)} rows, {len(real_cols)} real columns")
    if failed:
        print(f"Failed tickers: {failed}")


if __name__ == "__main__":
    main()
