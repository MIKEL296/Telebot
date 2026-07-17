# ==========================================
# FILE: data_engine.py
# ==========================================
import pandas as pd
import yfinance as yf
from indicators import calculate_rsi, calculate_macd, calculate_atr, calculate_ema

class DataEngine:
    """Handles fetching live market data frames dynamically for multi-timeframe systems."""
    
    def __init__(self):
        pass

    def get_analyzed_dataframe(self, ticker: str, interval: str = "15m", period: str = "5d") -> pd.DataFrame:
        df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        
        if df.empty:
            raise ValueError(f"No market data returned for asset symbol: {ticker}")
            
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        
        df = calculate_rsi(df, period=14)
        df = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)
        df = calculate_atr(df, period=14)
        df = calculate_ema(df, period=50) 
        
        df = df.dropna(subset=['rsi', 'macd_histogram', 'atr', 'ema_50'])
        return df