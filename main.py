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
from broker_gateway import BrokerGateway
from config import settings

# Default execution variables
LOT_SIZE = 5.0

def send_telegram_push_notification(message: str):
    """Sends proactive market updates and trade alerts straight to your phone."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_ADMIN_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Failed to forward background alert: {e}")

def automated_trade_and_market_messenger():
    """Scans the market, calculates volatility boundaries, and executes protected trades."""
    print("📈 High-Accuracy Automated Scan Active...")
    engine = DataEngine()
    gateway = BrokerGateway()
    watch_list = ["GC=F", "BTC-USD", "EURUSD=X"]
    
    while True:
        print(f"\n🕒 [Scan: {datetime.now().strftime('%H:%M:%S')}] Evaluating high-confluence setups...")
        
        account = gateway.get_account_details()
        if account["status"] != "success":
            print("⚠️ Skipping cycle: Cannot link to MT5/Exness broker terminal.")
            time.sleep(60)
            continue
            
        if account["cash"] < 3.00:
            print("🛑 Safety Halt: Account balance too low.")
            time.sleep(300)
            continue

        for ticker in watch_list:
            exness_symbol = "XAUUSDm" if ticker == "GC=F" else ("BTCUSDm" if ticker == "BTC-USD" else "EURUSDm")
            display_name = "GOLD" if ticker == "GC=F" else ("BITCOIN" if ticker == "BTC-USD" else "EUR / USD")

            try:
                df = engine.get_analyzed_dataframe(ticker)
                latest_close = df['close'].iloc[-1]
                latest_rsi = df['rsi'].iloc[-1]
                latest_macd_hist = df['macd_histogram'].iloc[-1]
                prev_macd_hist = df['macd_histogram'].iloc[-2]
                ema_50 = df['ema_50'].iloc[-1] if 'ema_50' in df.columns else latest_close
                latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else (latest_close * 0.005)
                
                order_side = None
                sl_price = 0.0
                tp_price = 0.0
                
                # Signal Generation with dynamic bracket placement
                if latest_rsi < 35 and latest_macd_hist > prev_macd_hist and latest_close > ema_50:
                    order_side = "buy"
                    sl_price = latest_close - (1.5 * latest_atr)
                    tp_price = latest_close + (3.0 * latest_atr)
                elif latest_rsi > 65 and latest_macd_hist < prev_macd_hist and latest_close < ema_50:
                    order_side = "sell"
                    sl_price = latest_close + (1.5 * latest_atr)
                    tp_price = latest_close - (3.0 * latest_atr)
                
                if order_side:
                    precision = 2 if exness_symbol == "XAUUSDm" else (3 if exness_symbol == "BTCUSDm" else 5)
                    sl_price = round(sl_price, precision)
                    tp_price = round(tp_price, precision)

                    print(f"🎯 Confluence Signal for {display_name} ({order_side.upper()})! Executing with SL: {sl_price} | TP: {tp_price}")
                    
                    trade_result = gateway.execute_market_order(
                        symbol=exness_symbol, 
                        qty=LOT_SIZE, 
                        side=order_side,
                        sl=sl_price,
                        tp=tp_price
                    )
                    
                    if trade_result and trade_result.get("status") == "success":
                        alert_msg = (
                            f"🚀 *LIVE AUTO-TRADE EXECUTED* 🚀\n\n"
                            f"▪️ *{display_name}* ▪️\n\n"
                            f"┌──────────────────┐\n"
                            f"      * {order_side.upper()} * \n"
                            f"└──────────────────┘\n"
                            f"🔹 *Status:* Guarded on Exness Server\n"
                            f"📊 *Entry Price:* ${latest_close:,.2f}\n"
                            f"🛡️ *Stop Loss:* ${sl_price:,.2f}\n"
                            f"🎯 *Take Profit:* ${tp_price:,.2f}\n"
                            f"💼 *Lot Size:* {LOT_SIZE} lots"
                        )
                        send_telegram_push_notification(alert_msg)
                        
                        db = SessionLocal()
                        try:
                            log = TradeLog(
                                symbol=exness_symbol,
                                action=order_side.upper(),
                                mode="STRICT CONFLUENCE",
                                quantity=LOT_SIZE,
                                entry_price=latest_close,
                                pnl=0.0,
                                running_balance=account["cash"]
                            )
                            db.add(log)
                            db.commit()
                        except Exception as dbe:
                            print(f"Database write error: {dbe}")
                            db.rollback()
                        finally:
                            db.close()
                    else:
                        print(f"❌ Exness Order Blocked/Rejected: {trade_result.get('message')}")
                else:
                    print(f"   ℹ️ [{display_name}] No strong signal.")
                        
            except Exception as e:
                print(f"❌ Error scanning {ticker}: {e}")
                
        time.sleep(900)  # Scan every 15 minutes

def main():
    print("🚀 Booting Finance Track Automation Stack...")
    try:
        init_db()
    except Exception as e:
        print(f"🛑 Storage Boot Error: {e}")
        sys.exit(1)
        
    worker_thread = threading.Thread(target=automated_trade_and_market_messenger, daemon=True)
    worker_thread.start()
    
    print("\n✅ Auto-Execution Engine and Market Messenger are now LIVE.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Core application shutting down.")

if __name__ == "__main__":
    main()