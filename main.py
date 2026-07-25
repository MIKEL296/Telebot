# ==========================================
# FILE: main.py
# ==========================================
import sys
import time
import threading
import requests
from datetime import datetime
from database import init_db, SessionLocal, TradeLog
from data_engine import DataEngine
from config import settings

LOT_SIZE = 5.0

def send_telegram_push_notification(message: str):
    """Forwards signal prediction cards directly to your phone."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_ADMIN_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Failed to send signal push notification: {e}")

def calculate_trade_duration(interval_minutes: int, target_tp_atr_multiple: float = 3.0) -> str:
    """Estimates trade duration based on timeframe interval and ATR target distance."""
    # Base estimated candles needed to reach 3x ATR distance
    estimated_candles = max(2, int(target_tp_atr_multiple * 1.5))
    total_minutes = estimated_candles * interval_minutes
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    return f"{minutes} mins"

def automated_signal_generator():
    """Scans live markets, logs technical predictions with SL/TP/Duration, and sends pings."""
    print("📈 High-Confluence Signal Generator Active...")
    engine = DataEngine()
    watch_list = ["GC=F", "BTC-USD", "EURUSD=X"]
    
    while True:
        print(f"\n🕒 [Scan: {datetime.now().strftime('%H:%M:%S')}] Evaluating market setups...")

        for ticker in watch_list:
            display_name = "GOLD (XAUUSD)" if ticker == "GC=F" else ("BITCOIN (BTC)" if ticker == "BTC-USD" else "EUR / USD")
            asset_symbol = "XAUUSD" if ticker == "GC=F" else ("BTCUSD" if ticker == "BTC-USD" else "EURUSD")

            try:
                df = engine.get_analyzed_dataframe(ticker, interval="15m")
                latest_close = df['close'].iloc[-1]
                latest_rsi = df['rsi'].iloc[-1]
                latest_macd_hist = df['macd_histogram'].iloc[-1]
                prev_macd_hist = df['macd_histogram'].iloc[-2]
                ema_50 = df['ema_50'].iloc[-1] if 'ema_50' in df.columns else latest_close
                latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else (latest_close * 0.005)
                
                signal_side = None
                
                # Signal Rules
                if latest_rsi < 35 and latest_macd_hist > prev_macd_hist and latest_close > ema_50:
                    signal_side = "buy"
                    sl_price = latest_close - (1.5 * latest_atr)
                    tp_price = latest_close + (3.0 * latest_atr)
                elif latest_rsi > 65 and latest_macd_hist < prev_macd_hist and latest_close < ema_50:
                    signal_side = "sell"
                    sl_price = latest_close + (1.5 * latest_atr)
                    tp_price = latest_close - (3.0 * latest_atr)
                
                if signal_side:
                    precision = 2 if ticker == "GC=F" else (3 if ticker == "BTC-USD" else 5)
                    sl_price = round(sl_price, precision)
                    tp_price = round(tp_price, precision)
                    duration_est = calculate_trade_duration(interval_minutes=15, target_tp_atr_multiple=3.0)

                    print(f"🎯 Signal Detected for {display_name} ({signal_side.upper()})!")

                    # 1. Log the prediction into database
                    db = SessionLocal()
                    try:
                        log = TradeLog(
                            symbol=asset_symbol,
                            action=signal_side.upper(),
                            mode="STRICT CONFLUENCE",
                            quantity=LOT_SIZE,
                            entry_price=latest_close,
                            stop_loss=sl_price,
                            take_profit=tp_price,
                            estimated_duration=duration_est,
                            pnl=0.0
                        )
                        db.add(log)
                        db.commit()
                        db.refresh(log)
                        signal_id = log.id
                    except Exception as dbe:
                        print(f"Database write error: {dbe}")
                        db.rollback()
                        signal_id = "N/A"
                    finally:
                        db.close()

                    # 2. Push Notification Card
                    alert_msg = (
                        f"🚨 *NEW TRADE SIGNAL DETECTED* 🚨\n\n"
                        f"▪️ *{display_name}* ▪️\n\n"
                        f"┌──────────────────┐\n"
                        f"      * {signal_side.upper()} * \n"
                        f"└──────────────────┘\n"
                        f"🆔 *Signal ID:* #{signal_id}\n"
                        f"📊 *Entry Price:* ${latest_close:,.2f}\n"
                        f"🛡️ *Stop Loss (SL):* ${sl_price:,.2f}\n"
                        f"🎯 *Take Profit (TP):* ${tp_price:,.2f}\n"
                        f"⏳ *Est. Duration:* ~{duration_est}\n"
                        f"💼 *Rec. Size:* {LOT_SIZE} lots"
                    )
                    send_telegram_push_notification(alert_msg)
                else:
                    print(f"   ℹ️ [{display_name}] No matching gaps. Market consolidating.")
                        
            except Exception as e:
                print(f"❌ Error scanning {ticker}: {e}")
                
        time.sleep(900)  # Scan every 15 minutes

def main():
    print("🚀 Booting Pure Signal Generator Stack...")
    init_db()
    
    worker_thread = threading.Thread(target=automated_signal_generator, daemon=True)
    worker_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Core application shutting down.")

if __name__ == "__main__":
    main()