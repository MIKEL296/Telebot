# ==========================================
# FILE: indicators.py
# ==========================================
import pandas as pd
import numpy as np

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
    df = df.copy()
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).copy()
    loss = (-delta.where(delta < 0, 0)).copy()
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, column: str = 'close') -> pd.DataFrame:
    df = df.copy()
    fast_ema = df[column].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df[column].ewm(span=slow_period, adjust=False).mean()
    df['macd_line'] = fast_ema - slow_ema
    df['macd_signal'] = df['macd_line'].ewm(span=signal_period, adjust=False).mean()
    df['macd_histogram'] = df['macd_line'] - df['macd_signal']
    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.copy()
    if 'high' not in df.columns or 'low' not in df.columns:
        df['atr'] = 1.5
        return df
    high = df['high']
    low = df['low']
    prev_close = df['close'].shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.ewm(alpha=1/period, adjust=False).mean()
    df['atr'] = df['atr'].fillna(1.5)
    return df

def calculate_ema(df: pd.DataFrame, period: int = 50, column: str = 'close') -> pd.DataFrame:
    df = df.copy()
    df[f'ema_{period}'] = df[column].ewm(span=period, adjust=False).mean()
    return df