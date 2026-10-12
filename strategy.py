import logging
import pandas as pd

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)


class DynamicStrategyEngine:
    def __init__(self, fast_ema: int = 9, slow_ema: int = 21, rsi_period: int = 14):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.rsi_period = rsi_period
        self.strategy_name = f"Dual EMA Crossover ({fast_ema}/{slow_ema}) + RSI ({rsi_period})"

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_signal_and_analysis(self, symbol: str, timeframe=None) -> dict:
        if not MT5_AVAILABLE:
            return {
                "signal": "NEUTRAL",
                "reason": "MT5 library missing.",
                "strategy_name": self.strategy_name,
            }

        if timeframe is None:
            timeframe = mt5.TIMEFRAME_M5

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) < self.slow_ema + 5:
            return {
                "signal": "NEUTRAL",
                "reason": "Insufficient candle historical data from broker.",
                "strategy_name": self.strategy_name,
            }

        df = pd.DataFrame(rates)
        df["fast_ema"] = df["close"].ewm(span=self.fast_ema, adjust=False).mean()
        df["slow_ema"] = df["close"].ewm(span=self.slow_ema, adjust=False).mean()
        df["rsi"] = self._calculate_rsi(df["close"], self.rsi_period)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        signal = "NEUTRAL"
        reason = "Market consolidating. Fast EMA is within range."

        # BUY Condition
        if prev["fast_ema"] <= prev["slow_ema"] and curr["fast_ema"] > curr["slow_ema"]:
            if curr["rsi"] >= 50:
                signal = "BUY"
                reason = f"Fast EMA ({curr['fast_ema']:.2f}) crossed ABOVE Slow EMA ({curr['slow_ema']:.2f}) with Bullish RSI ({curr['rsi']:.1f})."
            else:
                reason = f"Bullish EMA crossover detected, but RSI ({curr['rsi']:.1f}) is weak (< 50)."

        # SELL Condition
        elif prev["fast_ema"] >= prev["slow_ema"] and curr["fast_ema"] < curr["slow_ema"]:
            if curr["rsi"] <= 50:
                signal = "SELL"
                reason = f"Fast EMA ({curr['fast_ema']:.2f}) crossed BELOW Slow EMA ({curr['slow_ema']:.2f}) with Bearish RSI ({curr['rsi']:.1f})."
            else:
                reason = f"Bearish EMA crossover detected, but RSI ({curr['rsi']:.1f}) is overbought (> 50)."

        # Continuation conditions
        elif curr["fast_ema"] > curr["slow_ema"] and curr["rsi"] > 55:
            signal = "BUY"
            reason = f"Strong Uptrend continuation. Fast EMA > Slow EMA and RSI ({curr['rsi']:.1f}) > 55."
        elif curr["fast_ema"] < curr["slow_ema"] and curr["rsi"] < 45:
            signal = "SELL"
            reason = f"Strong Downtrend continuation. Fast EMA < Slow EMA and RSI ({curr['rsi']:.1f}) < 45."

        return {
            "signal": signal,
            "reason": reason,
            "strategy_name": self.strategy_name,
            "fast_ema": round(curr["fast_ema"], 3),
            "slow_ema": round(curr["slow_ema"], 3),
            "rsi": round(curr["rsi"], 1),
        }


strategy_engine = DynamicStrategyEngine()