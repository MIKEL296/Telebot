import logging
import sys
import asyncio
import importlib
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import settings

import broker_gateway
importlib.reload(broker_gateway)
from broker_gateway import BrokerGateway

import data_engine
importlib.reload(data_engine)
from data_engine import DataEngine

from database import SessionLocal, TradeLog

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

gateway = BrokerGateway()
engine = DataEngine()

# Set Lot size to 5.0
LOT_SIZE = 5.0

def is_admin(update: Update) -> bool:
    return update.effective_user.id == settings.TELEGRAM_ADMIN_ID

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    keyboard = [['/balance', '/execute'], ['/read', '/logs']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(" * FX signal Scalping Terminal Online.*", parse_mode="Markdown", reply_markup=reply_markup)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    account_data = await asyncio.to_thread(gateway.get_account_details)
    
    if account_data["status"] == "success":
        msg = (
            f"💰 *Portfolio Balance Metrics:*\n\n"
            f"• *Cash Balance:* ${account_data['cash']:,.2f}\n"
            f"• *Total Equity:* ${account_data['equity']:,.2f}\n"
            f"• *Buying Power:* ${account_data['buying_power']:,.2f}"
        )
    else:
        msg = "⚠️ *Broker Gateway Connection Offline.*"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    status_message = await update.message.reply_text("🔍 Running dual-lens matrix scans (Macro & Micro)...")
    watch_list = ["GC=F", "BTC-USD", "EURUSD=X"]
    
    for ticker in watch_list:
        display_name = "GOLD (XAUUSD)" if ticker == "GC=F" else ("BITCOIN (BTC)" if ticker == "BTC-USD" else "EUR / USD")
        cards_to_send = []
        
        try:
            df_15 = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="15m")
            c_15, r_15, m_15, p_m_15, e_15 = df_15['close'].iloc[-1], df_15['rsi'].iloc[-1], df_15['macd_histogram'].iloc[-1], df_15['macd_histogram'].iloc[-2], df_15['ema_50'].iloc[-1]
            if r_15 < 35 and m_15 > p_m_15 and c_15 > e_15:
                cards_to_send.append(("🥇 MAJ_BUY", f"🟢 *STRICT CONFLUENCE BUY:* Oversold at {r_15:.1f} breaking up. Highly decisive setup!"))
            elif r_15 > 65 and m_15 < p_m_15 and c_15 < e_15:
                cards_to_send.append(("🥇 MAJ_SELL", f"🔴 *STRICT CONFLUENCE SELL:* Overbought at {r_15:.1f} pivoting down. Highly decisive setup!"))
        except Exception: pass

        try:
            df_5 = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m")
            c_5, r_5, m_5, p_m_5 = df_5['close'].iloc[-1], df_5['rsi'].iloc[-1], df_5['macd_histogram'].iloc[-1], df_5['macd_histogram'].iloc[-2]
            if r_5 < 45 and m_5 > p_m_5:
                cards_to_send.append(("⚡ SCALP_BUY", f"🚀 *MICRO SCALP BUY:* Lenient momentum flip caught on 5m chart (RSI: {r_5:.1f})."))
            elif r_5 > 55 and m_5 < p_m_5:
                cards_to_send.append(("⚡ SCALP_SELL", f"🔥 *MICRO SCALP SELL:* Lenient momentum flip caught on 5m chart (RSI: {r_5:.1f})."))
        except Exception: pass

        if not cards_to_send:
            simple_card = f"▪️ *{display_name}* ▪️\n\n┌──────────────────┐\n      * WAIT * \n└──────────────────┘\n📋 *Status:* No matching gaps. Market consolidating."
            await update.message.reply_text(simple_card, parse_mode="Markdown")
        else:
            for action_tag, text_advice in cards_to_send:
                simple_card = f"▪️ *{display_name}* ▪️\n\n┌──────────────────┐\n   * {action_tag} * \n└──────────────────┘\n📋 *Calculated Direction Intel:*\n{text_advice}"
                await update.message.reply_text(simple_card, parse_mode="Markdown")
                
    await status_message.delete()

async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    status_message = await update.message.reply_text("⚡ Interrogating terminal structures for entry points...")
    watch_list = ["GC=F", "BTC-USD", "EURUSD=X"]
    chosen_trade = None
    
    for ticker in watch_list:
        try:
            df = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="15m")
            c, r, m, p_m, e = df['close'].iloc[-1], df['rsi'].iloc[-1], df['macd_histogram'].iloc[-1], df['macd_histogram'].iloc[-2], df['ema_50'].iloc[-1]
            if r < 35 and m > p_m and c > e:
                chosen_trade = {"ticker": ticker, "action": "buy", "mode": "STRICT MACD", "price": c}
                break
            elif r > 65 and m < p_m and c < e:
                chosen_trade = {"ticker": ticker, "action": "sell", "mode": "STRICT MACD", "price": c}
                break
        except Exception: pass

    if not chosen_trade:
        for ticker in watch_list:
            try:
                df = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m")
                c, r, m, p_m = df['close'].iloc[-1], df['rsi'].iloc[-1], df['macd_histogram'].iloc[-1], df['macd_histogram'].iloc[-2]
                if r < 45 and m > p_m:
                    chosen_trade = {"ticker": ticker, "action": "buy", "mode": "LENIENT SCALP", "price": c}
                    break
                elif r > 55 and m < p_m:
                    chosen_trade = {"ticker": ticker, "action": "sell", "mode": "LENIENT SCALP", "price": c}
                    break
            except Exception: pass

    await status_message.delete()
    
    if not chosen_trade:
        await update.message.reply_text("🛑 *System Guard:* Absolute zero entries found across all lenient filters.")
        return

    exness_symbol = "XAUUSDm" if chosen_trade["ticker"] == "GC=F" else ("BTCUSDm" if chosen_trade["ticker"] == "BTC-USD" else "EURUSDm")
    display_name = "GOLD" if chosen_trade["ticker"] == "GC=F" else ("BITCOIN" if chosen_trade["ticker"] == "BTC-USD" else "EUR / USD")

    try:
        # Fetch data frame again to calculate structural ATR bounds safely
        df = await asyncio.to_thread(engine.get_analyzed_dataframe, chosen_trade["ticker"], interval="15m")
        latest_atr = df['atr'].iloc[-1]
        latest_close = chosen_trade["price"]

        if chosen_trade["action"] == "buy":
            sl_price = latest_close - (1.5 * latest_atr)
            tp_price = latest_close + (3.0 * latest_atr)
        else:
            sl_price = latest_close + (1.5 * latest_atr)
            tp_price = latest_close - (3.0 * latest_atr)

        precision = 2 if exness_symbol == "XAUUSDm" else (3 if exness_symbol == "BTCUSDm" else 5)
        sl_price = round(sl_price, precision)
        tp_price = round(tp_price, precision)

        # Offload order execution
        trade_result = await asyncio.to_thread(
            gateway.execute_market_order, 
            symbol=exness_symbol, 
            qty=LOT_SIZE, 
            side=chosen_trade["action"],
            sl=sl_price,
            tp=tp_price
        )
        
        if trade_result["status"] == "success":
            acct_info = await asyncio.to_thread(gateway.get_account_details)
            running_bal = acct_info["cash"] if acct_info["status"] == "success" else 0.0

            db = SessionLocal()
            try:
                log = TradeLog(
                    symbol=exness_symbol,
                    action=chosen_trade['action'].upper(),
                    mode=chosen_trade['mode'],
                    quantity=LOT_SIZE,
                    entry_price=chosen_trade['price'],
                    pnl=0.0,
                    running_balance=running_bal
                )
                db.add(log)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Database error writing log: {e}")
            finally:
                db.close()

            await update.message.reply_text(
                f"✅ *MANUAL TRADE IMPLEMENTED*\n\n"
                f"• *Asset:* {display_name} ({exness_symbol})\n"
                f"• *Action:* {chosen_trade['action'].upper()}\n"
                f"• *Price:* ${chosen_trade['price']:,.2f}\n"
                f"• *Stop Loss:* ${sl_price:,.2f}\n"
                f"• *Take Profit:* ${tp_price:,.2f}\n"
                f"• *Lot Size:* {LOT_SIZE} lots\n"
                f"• *Status:* Guarded by active broker-side brackets.", 
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ *Broker Rejection:* {trade_result.get('message')}")
    except Exception as err:
        await update.message.reply_text(f"⚠️ Gateway error: {str(err)}")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    await update.message.reply_text("📋 Compiling real-time trade history telemetry...")
    
    account_data = await asyncio.to_thread(gateway.get_account_details)
    live_bal = account_data['cash'] if account_data["status"] == "success" else 0.0

    db = SessionLocal()
    try:
        recent_logs = db.query(TradeLog).order_by(TradeLog.id.desc()).limit(6).all()
        if not recent_logs:
            await update.message.reply_text("📝 *History Matrix Status:* Empty. No trades recorded yet.", parse_mode="Markdown")
            return
            
        log_lines = [
            f"📊 *OFFICIAL FINANCIAL TRADE LOGS*\n"
            f"💰 *Current Real-Time Balance:* ${live_bal:,.2f}\n"
            f"───────────────────\n"
        ]
        
        for entry in recent_logs:
            ticker_map = {"XAUUSDm": "GC=F", "BTCUSDm": "BTC-USD", "EURUSDm": "EURUSD=X"}
            ticker = ticker_map.get(entry.symbol)
            
            pnl_amount = 0.0
            pnl_string = "🔵 Status: Current Price Loading..."
            
            if ticker:
                try:
                    df = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m")
                    current_price = df['close'].iloc[-1]
                    price_difference = current_price - entry.entry_price
                    
                    if entry.action.upper() == "BUY":
                        pnl_amount = price_difference * entry.quantity
                    elif entry.action.upper() == "SELL":
                        pnl_amount = -price_difference * entry.quantity
                    
                    if entry.symbol == "XAUUSDm":
                        pnl_amount *= 100  # Standard Gold Contract Multiplier
                    elif entry.symbol == "EURUSDm":
                        pnl_amount *= 100000  # Standard Lot Size Multiplier
                    
                    entry.pnl = pnl_amount
                    db.add(entry)
                    db.commit()
                    
                except Exception as calc_err:
                    print(f"Error calculating real-time PnL: {calc_err}")
                    pnl_amount = entry.pnl
            
            if pnl_amount > 0:
                pnl_string = f"🟢 Profit Gained: +${pnl_amount:,.2f}"
            elif pnl_amount < 0:
                pnl_string = f"🔴 Loss Incurred: -${abs(pnl_amount):,.2f}"
            else:
                pnl_string = f"🔵 Status: Flat / Break-Even ($0.00)"

            log_lines.append(
                f"🆔 *Ticket ID #{entry.id}* | *{entry.symbol}*\n"
                f" ├ *Type:* {entry.action} ({entry.mode})\n"
                f" ├ *Entry Price:* ${entry.entry_price:,.2f}\n"
                f" ├ {pnl_string}\n"
                f" └ *Post-Trade Balance:* ${entry.running_balance:,.2f}\n"
                f"───────────────────"
            )
            
        await update.message.reply_text("\n".join(log_lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Storage execution pipeline error: {str(e)}")
    finally:
        db.close()

def main():
    from database import init_db
    try:
        init_db()
        print("✅ Core structural database verification passed.")
    except Exception as e:
        print(f"⚠️ Synchronization pass: {e}")

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).connect_timeout(30.0).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("execute", execute_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("logs", logs_command))
    
    print("🤖 Telemetry Performance Interface running... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()