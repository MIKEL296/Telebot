# ==========================================
# FILE: telegram_bot.py
# ==========================================
import logging
import sys
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import settings

from data_engine import DataEngine
from database import SessionLocal, TradeLog, init_db

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

engine = DataEngine()
LOT_SIZE = 5.0

def is_admin(update: Update) -> bool:
    return update.effective_user.id == settings.TELEGRAM_ADMIN_ID

def calculate_trade_duration(interval_minutes: int, target_tp_atr_multiple: float = 4.0) -> str:
    estimated_candles = max(3, int(target_tp_atr_multiple * 1.5))
    total_minutes = estimated_candles * interval_minutes
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    return f"{minutes} mins"

def format_quick_price(value: float, symbol: str) -> str:
    if value is None:
        return "N/A"
    if symbol in ["XAUUSD", "BTCUSD"]:
        return f"${round(value):,}"
    else:  # EURUSD / Forex
        return f"${value:.4f}"

def calculate_projected_profit(entry: float, tp: float, symbol: str, action: str, qty: float = 5.0) -> float:
    price_diff = abs(tp - entry)
    if symbol == "XAUUSD":
        return price_diff * qty * 100
    elif symbol == "EURUSD":
        return price_diff * qty * 100000
    else:  # BTCUSD
        return price_diff * qty

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    keyboard = [['/read', '/predict'], ['/logs']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("📡 *FX Signal Predictor Terminal Online.*", parse_mode="Markdown", reply_markup=reply_markup)

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
                cards_to_send.append(("🥇 MAJ_BUY", f"🟢 *STRICT CONFLUENCE BUY:* Oversold at {r_15:.1f} breaking up."))
            elif r_15 > 65 and m_15 < p_m_15 and c_15 < e_15:
                cards_to_send.append(("🥇 MAJ_SELL", f"🔴 *STRICT CONFLUENCE SELL:* Overbought at {r_15:.1f} pivoting down."))
        except Exception: pass

        try:
            df_5 = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m")
            c_5, r_5, m_5, p_m_5 = df_5['close'].iloc[-1], df_5['rsi'].iloc[-1], df_5['macd_histogram'].iloc[-1], df_5['macd_histogram'].iloc[-2]
            if r_5 < 45 and m_5 > p_m_5:
                cards_to_send.append(("⚡ SCALP_BUY", f"🚀 *MICRO SCALP BUY:* Lenient momentum flip on 5m chart (RSI: {r_5:.1f})."))
            elif r_5 > 55 and m_5 < p_m_5:
                cards_to_send.append(("⚡ SCALP_SELL", f"🔥 *MICRO SCALP SELL:* Lenient momentum flip on 5m chart (RSI: {r_5:.1f})."))
        except Exception: pass

        if not cards_to_send:
            simple_card = f"▪️ *{display_name}* ▪️\n\n┌──────────────────┐\n      * WAIT * \n└──────────────────┘\n📋 *Status:* No matching gaps. Market consolidating."
            await update.message.reply_text(simple_card, parse_mode="Markdown")
        else:
            for action_tag, text_advice in cards_to_send:
                simple_card = f"▪️ *{display_name}* ▪️\n\n┌──────────────────┐\n   * {action_tag} * \n└──────────────────┘\n📋 *Calculated Direction Intel:*\n{text_advice}"
                await update.message.reply_text(simple_card, parse_mode="Markdown")
                
    await status_message.delete()

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a high-conviction signal prediction with rapid, rounded input values."""
    if not is_admin(update): return
    status_message = await update.message.reply_text("⚡ Interrogating market structures for high-margin signal predictions...")
    watch_list = ["GC=F", "BTC-USD", "EURUSD=X"]
    chosen_trade = None
    
    for ticker in watch_list:
        try:
            df = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="15m")
            c, r, m, p_m, e = df['close'].iloc[-1], df['rsi'].iloc[-1], df['macd_histogram'].iloc[-1], df['macd_histogram'].iloc[-2], df['ema_50'].iloc[-1]
            if r < 35 and m > p_m and c > e:
                chosen_trade = {"ticker": ticker, "action": "buy", "mode": "STRICT CONFLUENCE", "price": c, "interval": 15, "tier": "HIGH"}
                break
            elif r > 65 and m < p_m and c < e:
                chosen_trade = {"ticker": ticker, "action": "sell", "mode": "STRICT CONFLUENCE", "price": c, "interval": 15, "tier": "HIGH"}
                break
        except Exception: pass

    if not chosen_trade:
        for ticker in watch_list:
            try:
                df = await asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m")
                c, r, m, p_m = df['close'].iloc[-1], df['rsi'].iloc[-1], df['macd_histogram'].iloc[-1], df['macd_histogram'].iloc[-2]
                if r < 45 and m > p_m:
                    chosen_trade = {"ticker": ticker, "action": "buy", "mode": "MICRO SCALP", "price": c, "interval": 5, "tier": "MODERATE"}
                    break
                elif r > 55 and m < p_m:
                    chosen_trade = {"ticker": ticker, "action": "sell", "mode": "MICRO SCALP", "price": c, "interval": 5, "tier": "MODERATE"}
                    break
            except Exception: pass

    await status_message.delete()
    
    if not chosen_trade:
        await update.message.reply_text("🛑 *System Guard:* Absolute zero signal entries found across all filters.")
        return

    asset_symbol = "XAUUSD" if chosen_trade["ticker"] == "GC=F" else ("BTCUSD" if chosen_trade["ticker"] == "BTC-USD" else "EURUSD")
    display_name = "GOLD" if chosen_trade["ticker"] == "GC=F" else ("BITCOIN" if chosen_trade["ticker"] == "BTC-USD" else "EUR / USD")

    try:
        interval = chosen_trade.get("interval", 15)
        tier = chosen_trade.get("tier", "MODERATE")
        df = await asyncio.to_thread(engine.get_analyzed_dataframe, chosen_trade["ticker"], interval=f"{interval}m")
        latest_atr = df['atr'].iloc[-1]
        latest_close = chosen_trade["price"]

        sl_multiplier = 1.5
        tp_multiplier = 4.0 if tier == "HIGH" else 3.0

        if chosen_trade["action"] == "buy":
            sl_price = latest_close - (sl_multiplier * latest_atr)
            tp_price = latest_close + (tp_multiplier * latest_atr)
        else:
            sl_price = latest_close + (sl_multiplier * latest_atr)
            tp_price = latest_close - (tp_multiplier * latest_atr)

        precision = 0 if asset_symbol in ["XAUUSD", "BTCUSD"] else 4
        sl_price = round(sl_price, precision)
        tp_price = round(tp_price, precision)
        
        potential_profit_usd = calculate_projected_profit(latest_close, tp_price, asset_symbol, chosen_trade["action"], LOT_SIZE)
        duration_est = calculate_trade_duration(interval_minutes=interval, target_tp_atr_multiple=tp_multiplier)

        profit_tag = "🔥 HIGH PROFIT PREDICTION" if tier == "HIGH" else "⚡ MODERATE / SCALP PREDICTION"

        db = SessionLocal()
        try:
            log = TradeLog(
                symbol=asset_symbol,
                action=chosen_trade['action'].upper(),
                mode=chosen_trade['mode'],
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
        except Exception as e:
            db.rollback()
            print(f"Database error writing log: {e}")
            signal_id = "N/A"
        finally:
            db.close()

        entry_formatted = format_quick_price(latest_close, asset_symbol)
        sl_formatted = format_quick_price(sl_price, asset_symbol)
        tp_formatted = format_quick_price(tp_price, asset_symbol)

        await update.message.reply_text(
            f"✅ *SIGNAL PREDICTION RECORDED*\n"
            f"🏆 *Rating:* {profit_tag}\n\n"
            f"• *Asset:* {display_name} ({asset_symbol})\n"
            f"• *Action:* {chosen_trade['action'].upper()}\n"
            f"• *Entry Price:* {entry_formatted}\n"
            f"⚡ *Quick SL:* `{sl_formatted}`\n"
            f"⚡ *Quick TP:* `{tp_formatted}`\n"
            f"💵 *Target Profit:* +${potential_profit_usd:,.2f} (5.0 Lots)\n"
            f"⏳ *Est. Duration:* ~{duration_est}\n"
            f"🆔 *Signal ID:* #{signal_id}\n\n"
            f"💡 _Tip: Tap the values in code blocks to copy them instantly!_", 
            parse_mode="Markdown"
        )
    except Exception as err:
        await update.message.reply_text(f"⚠️ Signal error: {str(err)}")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Non-blocking, fast historical log renderer."""
    if not is_admin(update): return
    status_msg = await update.message.reply_text("📋 Compiling signal history...")
    
    db = SessionLocal()
    try:
        recent_logs = db.query(TradeLog).order_by(TradeLog.id.desc()).limit(8).all()
        if not recent_logs:
            await status_msg.edit_text("📝 *Signal History Matrix:* Empty. No predictions recorded yet.", parse_mode="Markdown")
            return
            
        log_lines = [
            f"📊 *HISTORICAL SIGNAL PREDICTIONS*\n"
            f"───────────────────"
        ]
        
        for entry in recent_logs:
            ticker_map = {"XAUUSD": "GC=F", "BTCUSD": "BTC-USD", "EURUSD": "EURUSD=X"}
            ticker = ticker_map.get(entry.symbol)
            pnl_amount = entry.pnl if entry.pnl is not None else 0.0
            
            # Non-blocking fast price fetch with 2-second strict timeout
            if ticker:
                try:
                    df = await asyncio.wait_for(
                        asyncio.to_thread(engine.get_analyzed_dataframe, ticker, interval="5m"),
                        timeout=2.0
                    )
                    current_price = df['close'].iloc[-1]
                    price_difference = current_price - entry.entry_price
                    qty = entry.quantity if entry.quantity else LOT_SIZE
                    
                    if entry.action.upper() == "BUY":
                        pnl_amount = price_difference * qty
                    elif entry.action.upper() == "SELL":
                        pnl_amount = -price_difference * qty
                    
                    if entry.symbol == "XAUUSD":
                        pnl_amount *= 100
                    elif entry.symbol == "EURUSD":
                        pnl_amount *= 100000
                    
                    entry.pnl = pnl_amount
                    db.add(entry)
                    db.commit()
                except Exception:
                    # Fallback cleanly if network times out
                    pnl_amount = entry.pnl if entry.pnl is not None else 0.0

            if pnl_amount > 0:
                pnl_string = f"🟢 Floating Gain: +${pnl_amount:,.2f}"
            elif pnl_amount < 0:
                pnl_string = f"🔴 Floating Drawdown: -${abs(pnl_amount):,.2f}"
            else:
                pnl_string = f"🔵 Status: At Entry Level ($0.00)"

            entry_disp = format_quick_price(entry.entry_price, entry.symbol)
            sl_disp = format_quick_price(getattr(entry, 'stop_loss', None), entry.symbol)
            tp_disp = format_quick_price(getattr(entry, 'take_profit', None), entry.symbol)
            duration_disp = getattr(entry, 'estimated_duration', None) or "~1h"

            log_lines.append(
                f"🆔 *Signal ID #{entry.id}* | *{entry.symbol}*\n"
                f" ├ *Type:* {entry.action} ({entry.mode})\n"
                f" ├ *Entry:* {entry_disp}\n"
                f" ├ *SL:* `{sl_disp}` | *TP:* `{tp_disp}`\n"
                f" ├ *Est. Time:* ~{duration_disp}\n"
                f" └ {pnl_string}\n"
                f"───────────────────"
            )
            
        await status_msg.edit_text("\n".join(log_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Logs exception: {e}")
        await status_msg.edit_text(f"❌ Storage error: {str(e)}")
    finally:
        db.close()

def main():
    init_db()

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).connect_timeout(30.0).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("logs", logs_command))
    
    print("🤖 Telegram Signal Interface running... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()