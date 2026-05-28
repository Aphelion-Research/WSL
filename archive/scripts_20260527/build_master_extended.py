"""Build hydra_xauusd_m5_master.parquet — complete feature matrix."""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

OUTPUT = Path("data/hydra_xauusd_m5_master.parquet")

def strip_tz(df):
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df

def to_naive(s):
    s = pd.to_datetime(s)
    if hasattr(s, 'dt'):
        if s.dt.tz is not None:
            s = s.dt.tz_localize(None)
        # Normalize to 'ns' resolution
        s = pd.to_datetime(s.values.astype('datetime64[ns]'))
    elif isinstance(s, pd.DatetimeIndex):
        if s.tz is not None:
            s = s.tz_localize(None)
        s = pd.DatetimeIndex(s.values.astype('datetime64[ns]'))
    return s

def safe_merge(df, right):
    left_r = df[['close']].reset_index()
    left_r.columns = ['time', 'close_m5']
    left_r['time'] = to_naive(left_r['time'])
    right_r = right.reset_index()
    right_r.columns = ['time'] + list(right.columns)
    right_r['time'] = to_naive(right_r['time'])
    left_r = left_r.sort_values('time')
    right_r = right_r.sort_values('time')
    merged = pd.merge_asof(left_r, right_r, on='time', direction='backward')
    merged = merged.set_index('time')
    return merged

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def compute_price_features(df):
    feats = pd.DataFrame(index=df.index)
    close = df['close']
    high  = df['high']
    low   = df['low']
    op    = df['open']
    vol   = df['tick_volume'].astype(float)

    print("  Returns...")
    for lag in [1,2,3,5,8,13,21,34,55,89,144,288]:
        feats[f'log_ret_{lag}b'] = np.log(close / close.shift(lag)).clip(-0.5, 0.5)
        feats[f'pct_ret_{lag}b'] = (close / close.shift(lag) - 1).clip(-0.5, 0.5)

    print("  Rolling stats...")
    for w in [5,10,14,20,34,55,72,144,288,576]:
        rm = close.rolling(w).mean()
        rs = close.rolling(w).std() + 1e-10
        feats[f'zscore_{w}b']   = ((close - rm) / rs).clip(-5, 5)
        feats[f'drawdown_{w}b'] = (close / close.rolling(w).max() - 1).clip(-1, 0)
        feats[f'drawup_{w}b']   = (close / close.rolling(w).min() - 1).clip(0, 1)

    print("  Volatility...")
    atr14 = atr(high, low, close, 14)
    lr    = np.log(close / close.shift(1))
    for w in [5,10,14,20,34,55,72,144,288,576]:
        feats[f'realized_vol_{w}b'] = lr.rolling(w).std() * np.sqrt(288*252)
        feats[f'atr_{w}b']          = (atr(high, low, close, w) / (close + 1e-10)).clip(0, 0.1)
        hl = np.log((high + 1e-10) / (low + 1e-10))
        feats[f'parkinson_{w}b']    = (hl**2 / (4*np.log(2))).rolling(w).mean().apply(np.sqrt)

    print("  EMAs & trend...")
    for p in [5,8,13,21,34,55,89,144,200,233,377]:
        e = ema(close, p)
        feats[f'ema_{p}_pct'] = ((close - e) / (close + 1e-10)).clip(-0.1, 0.1)
    for a_p, b_p in [(5,13),(8,21),(13,34),(21,55),(34,89),(55,144),(89,233),(50,200)]:
        feats[f'ema_cross_{a_p}_{b_p}'] = ((ema(close,a_p) - ema(close,b_p)) / (close+1e-10)).clip(-0.05,0.05)

    print("  Oscillators...")
    for p in [5,7,10,14,21,34,50,72]:
        feats[f'rsi_{p}b'] = rsi(close, p) / 100 - 0.5
    macd_l = ema(close,12) - ema(close,26)
    macd_s = ema(macd_l, 9)
    feats['macd_pct']      = (macd_l / (close+1e-10)).clip(-0.02, 0.02)
    feats['macd_sig_pct']  = (macd_s / (close+1e-10)).clip(-0.02, 0.02)
    feats['macd_hist_pct'] = ((macd_l - macd_s) / (close+1e-10)).clip(-0.02, 0.02)
    for w in [10,20,34,55,89]:
        sm = close.rolling(w).mean()
        ss = close.rolling(w).std() + 1e-10
        bb_u = sm + 2*ss; bb_l = sm - 2*ss
        feats[f'bb_pos_{w}b']   = ((close - bb_l) / (bb_u - bb_l + 1e-10)).clip(0,1)
        feats[f'bb_width_{w}b'] = ((bb_u - bb_l) / (sm + 1e-10)).clip(0, 0.1)
    for p in [7,14,20,34]:
        a_p = atr(high, low, close, p)
        dm_p = (high - high.shift()).clip(lower=0)
        dm_m = (low.shift() - low).clip(lower=0)
        sm   = a_p * p
        di_p = 100 * dm_p.rolling(p).sum() / (sm + 1e-10)
        di_m = 100 * dm_m.rolling(p).sum() / (sm + 1e-10)
        dx   = 100 * (di_p - di_m).abs() / (di_p + di_m + 1e-10)
        feats[f'adx_{p}b']      = (dx.rolling(p).mean() / 100).clip(0,1)
        feats[f'di_plus_{p}b']  = (di_p / 100).clip(0,1)
        feats[f'di_minus_{p}b'] = (di_m / 100).clip(0,1)
    for kp in [5,14]:
        ll = low.rolling(kp).min(); hh = high.rolling(kp).max()
        k  = ((close - ll) / (hh - ll + 1e-10)).clip(0,1)
        feats[f'stoch_k_{kp}'] = k - 0.5
        feats[f'stoch_d_{kp}'] = k.rolling(3).mean() - 0.5
    ll14 = low.rolling(14).min(); hh14 = high.rolling(14).max()
    feats['williams_r'] = (-(hh14 - close) / (hh14 - ll14 + 1e-10)).clip(-1,0)
    for w in [14,20]:
        tp  = (high + low + close) / 3
        stp = tp.rolling(w).mean()
        mad = tp.rolling(w).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        feats[f'cci_{w}b'] = ((tp - stp) / (0.015 * mad + 1e-10)).clip(-3,3) / 3

    print("  Volume...")
    for w in [5,20,60]:
        feats[f'vol_ratio_{w}b'] = (vol / (vol.rolling(w).mean() + 1e-10)).clip(0,10) / 10
    feats['vol_zscore_20b'] = ((vol - vol.rolling(20).mean()) / (vol.rolling(20).std() + 1e-10)).clip(-5,5)
    obv = (np.sign(close.diff()) * vol).cumsum()
    feats['obv_zscore']    = ((obv - obv.rolling(20).mean()) / (obv.rolling(20).std() + 1e-10)).clip(-5,5)
    feats['obv_slope_5b']  = obv.diff(5)
    feats['obv_slope_20b'] = obv.diff(20)
    mf = ((close - low) - (high - close)) / (high - low + 1e-10)
    feats['cmf_20b']    = (mf * vol).rolling(20).sum() / (vol.rolling(20).sum() + 1e-10)
    feats['vol_mom_5b'] = (vol / (vol.shift(5) + 1e-10) - 1).clip(-5,5)
    feats['abnormal_vol'] = (vol > vol.rolling(20).mean() + 3*vol.rolling(20).std()).astype(float)

    print("  Candle structure...")
    body   = (close - op).abs() / (atr14 + 1e-10)
    u_shad = (high - pd.concat([close,op],axis=1).max(axis=1)) / (atr14 + 1e-10)
    l_shad = (pd.concat([close,op],axis=1).min(axis=1) - low)  / (atr14 + 1e-10)
    bar_rng = high - low + 1e-10
    feats['body_pct']       = body.clip(0,5)
    feats['upper_shad_pct'] = u_shad.clip(0,5)
    feats['lower_shad_pct'] = l_shad.clip(0,5)
    feats['close_in_range'] = ((close - low) / bar_rng).clip(0,1) - 0.5
    feats['body_to_range']  = (body / (bar_rng/(atr14+1e-10)+1e-10)).clip(0,1)
    feats['pin_bar']        = (pd.concat([u_shad,l_shad],axis=1).max(axis=1) > 2*body).astype(float)
    feats['doji']           = ((close-op).abs() < 0.1*bar_rng).astype(float)
    feats['inside_bar']     = ((high < high.shift()) & (low > low.shift())).astype(float)
    feats['engulf_bull']    = ((close > high.shift()) & (op < low.shift())).astype(float)
    feats['engulf_bear']    = ((close < low.shift()) & (op > high.shift())).astype(float)
    bull_s = pd.Series(0.0, index=df.index)
    bear_s = pd.Series(0.0, index=df.index)
    is_bull = (close > op).astype(float)
    for i in range(1, len(df)):
        bull_s.iloc[i] = (bull_s.iloc[i-1] + 1) * is_bull.iloc[i]
        bear_s.iloc[i] = (bear_s.iloc[i-1] + 1) * (1 - is_bull.iloc[i])
    feats['bull_streak'] = bull_s.clip(0,10) / 10
    feats['bear_streak'] = bear_s.clip(0,10) / 10

    print("  Statistical...")
    lret = np.log(close/close.shift(1))
    feats['autocorr_1b'] = lret.rolling(20).apply(lambda x: pd.Series(x).autocorr(lag=1) if len(x)>2 else 0, raw=False)
    feats['skew_20b']    = lret.rolling(20).skew().clip(-3,3)
    feats['kurt_20b']    = lret.rolling(20).kurt().clip(-5,5)
    feats['price_accel'] = (lret - lret.shift(1)).clip(-0.05,0.05)
    feats['new_high_20'] = (close == close.rolling(20).max()).astype(float)
    feats['new_low_20']  = (close == close.rolling(20).min()).astype(float)

    print("  Seasonality...")
    idx = df.index
    if hasattr(idx,'tz') and idx.tz is not None:
        idx = idx.tz_localize(None)
    feats['sin_hour']    = np.sin(2*np.pi*idx.hour/24)
    feats['cos_hour']    = np.cos(2*np.pi*idx.hour/24)
    feats['sin_dow']     = np.sin(2*np.pi*idx.dayofweek/5)
    feats['cos_dow']     = np.cos(2*np.pi*idx.dayofweek/5)
    feats['sin_month']   = np.sin(2*np.pi*idx.month/12)
    feats['cos_month']   = np.cos(2*np.pi*idx.month/12)
    feats['sin_doy']     = np.sin(2*np.pi*idx.dayofyear/365)
    feats['cos_doy']     = np.cos(2*np.pi*idx.dayofyear/365)
    feats['is_monday']   = (idx.dayofweek==0).astype(float)
    feats['is_friday']   = (idx.dayofweek==4).astype(float)
    feats['is_london']   = ((idx.hour>=8)&(idx.hour<16)).astype(float)
    feats['is_ny']       = ((idx.hour>=13)&(idx.hour<21)).astype(float)
    feats['is_overlap']  = ((idx.hour>=13)&(idx.hour<16)).astype(float)
    seasonal = {1:0.85,2:0.80,3:0.60,4:0.50,5:0.55,6:0.35,
                7:0.45,8:0.65,9:0.80,10:0.60,11:0.55,12:0.65}
    feats['gold_seasonal']  = idx.month.map(seasonal)
    feats['days_to_qend']   = (pd.PeriodIndex(idx, freq='Q').to_timestamp('Q') - idx.to_series().reset_index(drop=True)).dt.days.clip(0,90).values / 90
    feats['days_to_yend']   = (365 - idx.dayofyear) / 365

    return feats

def compute_htf_features(df):
    feats = pd.DataFrame(index=df.index)
    htf_files = {
        'h1': 'data/mt5_history/XAUUSD_H1.parquet',
        'h4': 'data/mt5_history/XAUUSD_H4.parquet',
        'd1': 'data/mt5_history/XAUUSD_D1.parquet',
    }
    df_r = df[['close']].reset_index()
    df_r.columns = ['time','close_m5']
    df_r['time'] = to_naive(df_r['time'])
    df_r = df_r.sort_values('time')

    for tf, fpath in htf_files.items():
        if not Path(fpath).exists():
            continue
        try:
            htf = pd.read_parquet(fpath)
            htf = strip_tz(htf)
            if 'time' in htf.columns:
                htf = htf.set_index('time')
            htf.index = pd.to_datetime(htf.index).tz_localize(None)
            htf = htf.sort_index()
            col_map = {}
            for c in htf.columns:
                if c.lower() in ['open','high','low','close','tick_volume','volume','spread']:
                    col_map[c] = c.lower()
            htf = htf.rename(columns=col_map)
            if 'close' not in htf.columns:
                htf.columns = ['open','high','low','close','tick_volume','spread','real_volume'][:len(htf.columns)]
            c = htf['close']; h = htf['high']; l = htf['low']
            hf = pd.DataFrame(index=htf.index)
            hf[f'{tf}_ret_1b']    = np.log(c/c.shift(1)).clip(-0.1,0.1)
            hf[f'{tf}_ret_3b']    = np.log(c/c.shift(3)).clip(-0.2,0.2)
            hf[f'{tf}_atr_pct']   = (atr(h,l,c,14)/(c+1e-10)).clip(0,0.05)
            hf[f'{tf}_ema20_pct'] = ((c-ema(c,20))/(c+1e-10)).clip(-0.1,0.1)
            hf[f'{tf}_rsi14']     = rsi(c,14)/100 - 0.5
            hf[f'{tf}_zscore20']  = ((c-c.rolling(20).mean())/(c.rolling(20).std()+1e-10)).clip(-5,5)
            hf_r = hf.reset_index()
            hf_r.columns = ['time'] + list(hf.columns)
            hf_r['time'] = to_naive(hf_r['time'])
            hf_r = hf_r.sort_values('time')
            merged = pd.merge_asof(df_r, hf_r, on='time', direction='backward').set_index('time')
            for col in hf.columns:
                if col in merged.columns:
                    feats[col] = merged[col].values
        except Exception as e:
            print(f"  HTF {tf} failed: {e}")
    return feats

def compute_macro_features(df):
    feats = pd.DataFrame(index=df.index)
    p = Path('data/macro_extended/fred_extended_daily.parquet')
    if not p.exists():
        return feats
    macro = pd.read_parquet(p)
    macro = strip_tz(macro)
    macro.index = pd.to_datetime(macro.index).tz_localize(None)
    macro = macro.sort_index().ffill()
    merged = safe_merge(df, macro)
    for col in macro.columns:
        if col not in merged.columns:
            continue
        s = merged[col]
        feats[f'macro_{col}']         = s.fillna(0)
        feats[f'macro_{col}_chg1d']   = s.diff(1).fillna(0)
        feats[f'macro_{col}_chg5d']   = s.diff(5).fillna(0)
        feats[f'macro_{col}_chg20d']  = s.diff(20).fillna(0)
        rm = s.rolling(252,min_periods=20).mean()
        rs = s.rolling(252,min_periods=20).std()+1e-10
        feats[f'macro_{col}_z252']    = ((s-rm)/rs).clip(-5,5).fillna(0)
    if 'DGS10' in merged.columns and 'DGS2' in merged.columns:
        yc = merged['DGS10'] - merged['DGS2']
        feats['yield_curve_2s10s'] = yc.fillna(0)
        feats['yield_curve_chg5d'] = yc.diff(5).fillna(0)
    if 'DGS10' in merged.columns and 'DGS3MO' in merged.columns:
        feats['yield_curve_3m10y'] = (merged['DGS10']-merged['DGS3MO']).fillna(0)
    if 'DFII10' in merged.columns:
        feats['real_yield_10y']    = merged['DFII10'].fillna(0)
        feats['real_yield_chg5d']  = merged['DFII10'].diff(5).fillna(0)
    if 'T10YIE' in merged.columns:
        feats['breakeven_10y']     = merged['T10YIE'].fillna(0)
        feats['breakeven_chg5d']   = merged['T10YIE'].diff(5).fillna(0)
    return feats

def compute_cross_asset_features(df):
    feats = pd.DataFrame(index=df.index)
    p = Path('data/cross_asset_extended/cross_asset_extended_daily.parquet')
    if not p.exists():
        return feats
    ca = pd.read_parquet(p)
    ca = strip_tz(ca)
    ca.index = pd.to_datetime(ca.index).tz_localize(None)
    ca = ca.sort_index().ffill()
    merged = safe_merge(df, ca)
    assets = [c for c in ca.columns if c in merged.columns]
    xau = merged.get('gld', merged['close_m5'])
    for asset in assets:
        s = merged[asset]
        feats[f'{asset}_ret1d']    = np.log(s/s.shift(1)).clip(-0.5,0.5).fillna(0)
        feats[f'{asset}_ret5d']    = np.log(s/s.shift(5)).clip(-0.5,0.5).fillna(0)
        feats[f'{asset}_ret20d']   = np.log(s/s.shift(20)).clip(-0.5,0.5).fillna(0)
        rm=s.rolling(20).mean(); rs=s.rolling(20).std()+1e-10
        feats[f'{asset}_z20d']     = ((s-rm)/rs).clip(-5,5).fillna(0)
        rm2=s.rolling(60).mean(); rs2=s.rolling(60).std()+1e-10
        feats[f'{asset}_z60d']     = ((s-rm2)/rs2).clip(-5,5).fillna(0)
    for pair, name in [('silver','gold_silver'),('copper','gold_copper'),
                       ('wti','oil_gold'),('btc','btc_gold')]:
        if pair in merged.columns:
            num = xau if 'gold' in name.split('_')[0] else merged[pair]
            den = merged[pair] if 'gold' in name.split('_')[0] else xau
            ratio = num / (den + 1e-10)
            rm=ratio.rolling(20).mean(); rs=ratio.rolling(20).std()+1e-10
            feats[f'{name}_ratio_z20'] = ((ratio-rm)/rs).clip(-5,5).fillna(0)
    gold_ret = np.log(xau/xau.shift(1)).fillna(0)
    for asset in ['dxy','silver','spx','vix','tlt','btc','wti','copper']:
        if asset not in merged.columns:
            continue
        ar = np.log(merged[asset]/merged[asset].shift(1)).fillna(0)
        feats[f'corr_{asset}_20d'] = gold_ret.rolling(20).corr(ar).clip(-1,1).fillna(0)
        feats[f'corr_{asset}_60d'] = gold_ret.rolling(60).corr(ar).clip(-1,1).fillna(0)
    ret5 = {}
    for a in ['spx','vix','hyg','dxy','eurusd','audusd','silver','copper','wti']:
        if a in merged.columns:
            s = merged[a]
            ret5[a] = np.log(s/s.shift(5)).fillna(0)
    if all(k in ret5 for k in ['spx','vix','hyg']):
        feats['risk_on_composite']   = (0.4*ret5['spx']-0.3*ret5['vix']+0.3*ret5['hyg']).clip(-0.3,0.3)
    if all(k in ret5 for k in ['dxy','eurusd','audusd']):
        feats['dollar_composite']    = (0.5*ret5['dxy']-0.25*ret5['eurusd']-0.25*ret5['audusd']).clip(-0.2,0.2)
    comps = [ret5[a] for a in ['silver','copper','wti'] if a in ret5]
    if comps:
        feats['commodity_composite'] = pd.concat(comps,axis=1).mean(axis=1).clip(-0.3,0.3)
    if 'vix' in merged.columns:
        v = merged['vix']
        feats['vix_regime'] = pd.cut(v,bins=[0,15,25,35,999],labels=[0,1,2,3]).astype(float).fillna(1)
    return feats

def compute_cot_features(df):
    feats = pd.DataFrame(index=df.index)
    p = Path('data/cot/cot_gold_weekly.parquet')
    if not p.exists():
        return feats
    cot = pd.read_parquet(p)
    cot = strip_tz(cot)
    cot.index = pd.to_datetime(cot.index).tz_localize(None)
    cot = cot.sort_index()
    merged = safe_merge(df, cot)
    for col in cot.columns:
        if col not in merged.columns:
            continue
        s = merged[col].ffill().fillna(0)
        feats[f'cot_{col}']       = s
        feats[f'cot_{col}_chg1w'] = s.diff(1).fillna(0)
        feats[f'cot_{col}_chg4w'] = s.diff(4).fillna(0)
        rm=s.rolling(52,min_periods=10).mean(); rs=s.rolling(52,min_periods=10).std()+1e-10
        feats[f'cot_{col}_z52w']  = ((s-rm)/rs).clip(-5,5).fillna(0)
        feats[f'cot_{col}_pct52'] = s.rolling(52,min_periods=10).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False).fillna(0.5)
    return feats

def compute_etf_features(df):
    feats = pd.DataFrame(index=df.index)
    for ticker in ['gld','iau']:
        fp = Path(f'data/cross_asset/{ticker}.parquet')
        if not fp.exists():
            continue
        try:
            etf = pd.read_parquet(fp)
            etf = strip_tz(etf)
            etf.index = pd.to_datetime(etf.index).tz_localize(None)
            if isinstance(etf.columns, pd.MultiIndex):
                etf.columns = etf.columns.get_level_values(0)
            col = 'Close' if 'Close' in etf.columns else etf.columns[0]
            s_df = etf[[col]].rename(columns={col: ticker})
            merged = safe_merge(df, s_df)
            s = merged[ticker].ffill().fillna(0)
            feats[f'{ticker}_level']  = s
            feats[f'{ticker}_flow1d'] = s.diff(1).fillna(0)
            feats[f'{ticker}_flow5d'] = s.diff(5).fillna(0)
            f5 = s.diff(5)
            feats[f'{ticker}_flow_z20'] = ((f5-f5.rolling(20).mean())/(f5.rolling(20).std()+1e-10)).clip(-5,5).fillna(0)
        except Exception as e:
            print(f"  ETF {ticker} error: {e}")
    return feats

def compute_alternative_features(df):
    feats = pd.DataFrame(index=df.index)
    for fp in ['data/alternative/gpr_daily.parquet','data/alternative/gpr_index.parquet']:
        if not Path(fp).exists():
            continue
        try:
            gpr = pd.read_parquet(fp)
            gpr = strip_tz(gpr)
            gpr.index = pd.to_datetime(gpr.index).tz_localize(None)
            gpr = gpr.sort_index()
            col = gpr.columns[0]
            merged = safe_merge(df, gpr[[col]])
            s = merged[col].ffill().fillna(100)
            feats['gpr_level']    = s
            feats['gpr_chg3m']    = s.diff(60).fillna(0)
            rm=s.rolling(252,min_periods=60).mean(); rs=s.rolling(252,min_periods=60).std()+1e-10
            feats['gpr_z12m']     = ((s-rm)/rs).clip(-5,5).fillna(0)
            feats['gpr_spike']    = (s > s.rolling(252,min_periods=60).quantile(0.75)).astype(float).fillna(0)
            break
        except Exception as e:
            print(f"  GPR error: {e}")
    return feats

def compute_regime_features(df, macro_feats):
    feats = pd.DataFrame(index=df.index)
    close = df['close']
    lr    = np.log(close/close.shift(1))
    rv20  = lr.rolling(20).std() * np.sqrt(288*252)
    pct   = rv20.rolling(252,min_periods=50).rank(pct=True)
    feats['vol_regime']   = pd.cut(pct,bins=[-1,0.25,0.75,0.95,1.01],
                                    labels=[0,1,2,3]).astype(float).fillna(1)
    e20=ema(close,20); e50=ema(close,50); e200=ema(close,200)
    feats['trend_regime'] = ((close>e20).astype(float)+(close>e50).astype(float)+(close>e200).astype(float))/3 - 0.5
    score = pd.Series(0.0, index=df.index)
    if 'macro_DFII10' in macro_feats.columns:
        score -= macro_feats['macro_DFII10'] * 0.3
    feats['macro_composite'] = score.clip(-1,1)
    return feats

def compute_labels(df):
    print("  (triple-barrier labels — may take a few minutes)...")
    labels = pd.DataFrame(index=df.index)
    close  = df['close']
    atr14  = atr(df['high'], df['low'], close, 14)
    atr_pct = atr14 / (close + 1e-10)

    close_arr = close.values
    high_arr  = df['high'].values
    low_arr   = df['low'].values
    atp_arr   = atr_pct.values

    for h in [6,12,24,72,144,288]:
        result = np.full(len(df), np.nan)
        for i in range(len(df) - h):
            tp = close_arr[i] * (1 + 1.5 * atp_arr[i])
            sl = close_arr[i] * (1 - 1.5 * atp_arr[i])
            tp_bar = sl_bar = None
            for j in range(i+1, i+h+1):
                if tp_bar is None and high_arr[j] >= tp:
                    tp_bar = j
                if sl_bar is None and low_arr[j]  <= sl:
                    sl_bar = j
                if tp_bar is not None and sl_bar is not None:
                    break
            if tp_bar is not None and sl_bar is not None:
                result[i] = 1.0 if tp_bar <= sl_bar else 0.0
            elif tp_bar is not None:
                result[i] = 1.0
            elif sl_bar is not None:
                result[i] = 0.0
        labels[f'label_{h}b'] = result
        pos = (result == 1).sum(); neg = (result == 0).sum()
        print(f"    label_{h}b: {pos} long, {neg} short, {np.isnan(result).sum()} NaN")

    for h in [5,20,72]:
        labels[f'fwd_ret_{h}b'] = np.log(close.shift(-h)/close).clip(-0.2,0.2)
    return labels

def main():
    print('='*60)
    print('BUILDING MASTER DATASET')
    print('='*60)

    m5 = pd.read_parquet('data/mt5_history/XAUUSD_M5_MASTER.parquet')
    m5 = strip_tz(m5)
    if 'time' in m5.columns:
        m5 = m5.set_index('time')
    m5.index = pd.to_datetime(m5.index).tz_localize(None)
    m5 = m5.sort_index()
    col_map = {c: c.lower() for c in m5.columns if c.lower() in
               ['open','high','low','close','tick_volume','volume','spread','real_volume']}
    m5 = m5.rename(columns=col_map)
    if 'close' not in m5.columns:
        m5.columns = ['open','high','low','close','tick_volume','spread','real_volume'][:len(m5.columns)]
    if 'tick_volume' not in m5.columns:
        m5['tick_volume'] = 1.0
    if 'high' not in m5.columns:
        m5['high'] = m5['close']
        m5['low']  = m5['close']
    if 'open' not in m5.columns:
        m5['open'] = m5['close']

    print(f"M5: {len(m5)} rows | {m5.index.min()} → {m5.index.max()}")
    print("Computing features...")

    pf  = compute_price_features(m5)
    print("  HTF context...")
    hf  = compute_htf_features(m5)
    print("  Macro...")
    mf  = compute_macro_features(m5)
    print("  Cross-asset...")
    cf  = compute_cross_asset_features(m5)
    print("  COT...")
    cotf= compute_cot_features(m5)
    print("  ETF flows...")
    ef  = compute_etf_features(m5)
    print("  Alternative data...")
    af  = compute_alternative_features(m5)
    print("  Regime labels...")
    macro_joined = pd.concat([pf, mf], axis=1)
    rf  = compute_regime_features(m5, macro_joined)
    print("Computing labels...")
    lab = compute_labels(m5)

    all_feats = pd.concat([pf,hf,mf,cf,cotf,ef,af,rf], axis=1)
    master    = pd.concat([all_feats, lab], axis=1)

    label_cols   = [c for c in master.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in master.columns if c not in label_cols]
    master[feature_cols] = master[feature_cols].fillna(0)
    master = master.replace([np.inf,-np.inf], 0)
    for c in feature_cols:
        try:
            master[c] = master[c].astype('float32')
        except:
            pass

    master.to_parquet(OUTPUT)
    real = [c for c in feature_cols if not master[c].eq(0).all()]
    print(f"\n{'='*60}")
    print(f"SAVED: {OUTPUT}")
    print(f"Rows:          {len(master)}")
    print(f"Real features: {len(real)}")
    print(f"Labels:        {len(label_cols)}")
    print(f"Range:         {master.index.min()} → {master.index.max()}")
    print('='*60)

if __name__ == "__main__":
    main()
