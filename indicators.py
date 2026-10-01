# ==========================================
# FILE: indicators.py
# ==========================================
import pandas as pd

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=period).mean()
    return df

def calculate_ema(df: pd.DataFrame, period: int = 50) -> pd.DataFrame:
    df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df