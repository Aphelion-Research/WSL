#!/usr/bin/env python3
"""Fetch 100+ cross-asset tickers from Yahoo Finance."""
import yfinance as yf
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = Path("data/cross_asset_extended")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUTPUT_DIR / "cross_asset_extended_daily.parquet"

# Expanded ticker universe
TICKERS = {
    # FX (existing + more)
    'dxy': 'DX-Y.NYB', 'eurusd': 'EURUSD=X', 'usdjpy': 'USDJPY=X', 'gbpusd': 'GBPUSD=X',
    'audusd': 'AUDUSD=X', 'usdchf': 'USDCHF=X', 'usdcad': 'USDCAD=X', 'usdcnh': 'USDCNH=X',
    'nzdusd': 'NZDUSD=X', 'eurgbp': 'EURGBP=X', 'eurjpy': 'EURJPY=X', 'gbpjpy': 'GBPJPY=X',

    # Metals (existing + more)
    'silver': 'SI=F', 'copper': 'HG=F', 'platinum': 'PL=F', 'palladium': 'PA=F',
    'aluminum': 'ALI=F',

    # Equity indices (expanded)
    'spx': '^GSPC', 'nasdaq': '^IXIC', 'russell': '^RUT', 'dow': '^DJI',
    'sp400': '^SP400', 'sp600': '^SP600',
    'ftse': '^FTSE', 'dax': '^GDAXI', 'cac': '^FCHI', 'nikkei': '^N225',
    'hang_seng': '^HSI', 'shanghai': '000001.SS', 'asx': '^AXJO', 'tsx': '^GSPTSE',

    # Equity sectors
    'xlk': 'XLK', 'xlf': 'XLF', 'xle': 'XLE', 'xlv': 'XLV', 'xly': 'XLY',
    'xlp': 'XLP', 'xli': 'XLI', 'xlb': 'XLB', 'xlu': 'XLU', 'xlre': 'XLRE',

    # Volatility
    'vix': '^VIX', 'vix3m': '^VIX3M', 'vix6m': '^VIX6M', 'vix1y': '^VIX1Y',
    'gvz': '^GVZ', 'ovx': '^OVX', 'rvx': '^RVX',
    'vxn': '^VXN', 'vxd': '^VXD',

    # Bonds
    'tlt': 'TLT', 'ief': 'IEF', 'shy': 'SHY', 'hyg': 'HYG', 'lqd': 'LQD',
    'emb': 'EMB', 'jnk': 'JNK', 'bnd': 'BND', 'agg': 'AGG',

    # Commodities
    'wti': 'CL=F', 'brent': 'BZ=F', 'natgas': 'NG=F', 'heating_oil': 'HO=F',
    'gasoline': 'RB=F', 'corn': 'ZC=F', 'wheat': 'ZW=F', 'soybeans': 'ZS=F',
    'sugar': 'SB=F', 'coffee': 'KC=F', 'cotton': 'CT=F', 'lumber': 'LBS=F',

    # Crypto (expanded)
    'btc': 'BTC-USD', 'eth': 'ETH-USD', 'bnb': 'BNB-USD', 'xrp': 'XRP-USD',
    'ada': 'ADA-USD', 'sol': 'SOL-USD', 'dot': 'DOT-USD', 'doge': 'DOGE-USD',
    'avax': 'AVAX-USD', 'matic': 'MATIC-USD', 'link': 'LINK-USD', 'ltc': 'LTC-USD',

    # Precious metals ETFs
    'gld': 'GLD', 'iau': 'IAU', 'slv': 'SLV', 'gdx': 'GDX', 'gdxj': 'GDXJ',

    # Risk indicators
    'move': '^MOVE', 'skew': '^SKEW',
}


def fetch_ticker(name, symbol):
    cache = OUTPUT_DIR / f"{name}.parquet"
    if cache.exists():
        try:
            df = pd.read_parquet(cache)
            if len(df) > 100:
                return (name, len(df), 'cached')
        except:
            pass

    try:
        df = yf.download(symbol, start='2015-01-01', end='2026-05-21',
                         auto_adjust=True, progress=False)
        if df is not None and len(df) > 100:
            df.to_parquet(cache)
            return (name, len(df), 'fetched')
    except:
        pass
    return (name, 0, 'failed')


def main():
    print(f"Fetching {len(TICKERS)} tickers...")

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_ticker, name, sym): name for name, sym in TICKERS.items()}
        completed = 0
        for future in as_completed(futures):
            name, rows, status = future.result()
            results.append((name, rows, status))
            completed += 1
            if completed % 20 == 0:
                success = sum(1 for _, _, s in results if s != 'failed')
                print(f"  {completed}/{len(TICKERS)} | Success: {success}")

    # Combine
    print("\nCombining...")
    date_range = pd.date_range('2015-01-01', '2026-05-20', freq='D')
    combined = pd.DataFrame(index=date_range)
    combined.index.name = 'date'

    success_count = 0
    for name, rows, status in results:
        if status == 'failed':
            continue
        try:
            df = pd.read_parquet(OUTPUT_DIR / f"{name}.parquet")
            df.index = pd.to_datetime(df.index).tz_localize(None)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            col = 'Close' if 'Close' in df.columns else df.columns[0]
            combined[name] = df[col]
            success_count += 1
        except:
            pass

    combined = combined.ffill()
    combined.to_parquet(OUTPUT)

    real = [c for c in combined.columns if combined[c].notna().sum() > 100]
    print(f"\nSaved: {OUTPUT}")
    print(f"Rows: {len(combined)}")
    print(f"Real columns: {len(real)}")
    print(f"Failed: {len(TICKERS) - success_count}")


if __name__ == "__main__":
    main()
