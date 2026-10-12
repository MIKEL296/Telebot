import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import settings
from database import init_db, SessionLocal, SystemSettings, TradeHistory
from broker_gateway import broker

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ACTIVE_SYMBOL = "XAUUSD"


def get_main_keyboard():
    keyboard = [
        ["/predict", "/history"],
        ["/autotrade", "/status"],
        ["/logs"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def is_admin(update: Update) -> bool:
    user_id = update.effective_user.id
    if settings.ADMIN_USER_ID == 0 or user_id == settings.ADMIN_USER_ID:
        return True
    return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(
        "⚡ *Muti Bot Trading Dashboard Active*\nSelect a control button below:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    balance = broker.get_account_balance()
    analysis = broker.get_market_analysis(ACTIVE_SYMBOL)

    signal_emoji = (
        "🟢"
        if analysis["signal"] == "BUY"
        else ("🔴" if analysis["signal"] == "SELL" else "⚪")
    )

    reply_msg = (
        f"📊 *LIVE MARKET & STRATEGY ANALYSIS*\n"
        f"-----------------------------------------\n"
        f"🧠 *Active Strategy:* `{analysis['strategy_name']}`\n"
        f"• *Asset:* {ACTIVE_SYMBOL}\n"
        f"• *Signal:* {signal_emoji} `{analysis['signal']}`\n"
        f"• *Reason:* _{analysis['reason']}_\n\n"
        f"📈 *Technical Indicators:*\n"
        f"• EMA 9: `{analysis.get('fast_ema', 'N/A')}`\n"
        f"• EMA 21: `{analysis.get('slow_ema', 'N/A')}`\n"
        f"• RSI (14): `{analysis.get('rsi', 'N/A')}`\n\n"
        f"💵 *MT5 Equity:* ${balance:,.2f}"
    )
    await update.message.reply_text(
        reply_msg, parse_mode="Markdown", reply_markup=get_main_keyboard()
    )


async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    context.user_data["awaiting_target_goal"] = True
    acc_balance = broker.get_account_balance()

    msg = (
        f"🤖 *MT5 / EXNESS AUTO-TRADE SETUP*\n\n"
        f"💵 *Current MT5 Balance:* ${acc_balance:,.2f}\n"
        f"🎯 *Please enter your Target Goal amount (e.g. 500 or 1000):*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_target_goal_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not context.user_data.get("awaiting_target_goal"):
        return

    text = update.message.text.strip()
    try:
        target_amount = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid input. Please enter a numerical target goal."
        )
        return

    db = SessionLocal()
    try:
        sys_settings = db.query(SystemSettings).filter_by(id=1).first()
        if not sys_settings:
            sys_settings = SystemSettings(id=1)
            db.add(sys_settings)

        sys_settings.auto_trade_enabled = True
        sys_settings.target_goal = target_amount
        db.commit()

        context.user_data["awaiting_target_goal"] = False
        starting_balance = broker.get_account_balance()

        msg = (
            f"🎯 *TARGET GOAL CONFIGURED*\n"
            f"-----------------------------------------\n"
            f"💵 *Starting Balance:* ${starting_balance:,.2f}\n"
            f"🚀 *Target Goal:* ${target_amount:,.2f}\n"
            f"🤖 *Automated Execution:* 🟢 Active\n\n"
            f"🧠 *Engine:* Dynamic EMA Crossover + RSI Strategy Active."
        )
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
    finally:
        db.close()


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    db = SessionLocal()
    try:
        sys_settings = db.query(SystemSettings).filter_by(id=1).first()
        is_active = sys_settings.auto_trade_enabled if sys_settings else False
        target_goal = sys_settings.target_goal if sys_settings else 0.0

        state_str = "🟢 ACTIVE" if is_active else "🔴 INACTIVE"
        balance = broker.get_account_balance()
        analysis = broker.get_market_analysis(ACTIVE_SYMBOL)

        msg = (
            f"⚙️ *REAL-TIME SYSTEM STATUS*\n"
            f"-----------------------------------------\n"
            f"🤖 *Auto-Execution State:* {state_str}\n"
            f"🧠 *Strategy Engine:* `{analysis['strategy_name']}`\n"
            f"📊 *Current Market Signal:* `{analysis['signal']}`\n"
            f"💵 *Current Exness Balance:* ${balance:,.2f}\n"
            f"🎯 *Active Target Goal:* ${target_goal:,.2f}\n"
            f"🔌 *Broker Connection:* Exness MT5 Terminal"
        )
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
    finally:
        db.close()


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    db = SessionLocal()
    try:
        trades = (
            db.query(TradeHistory)
            .order_by(TradeHistory.id.desc())
            .limit(5)
            .all()
        )

        if not trades:
            msg = "📜 *MT5 EXECUTION HISTORY*\n\nNo live orders logged yet."
        else:
            msg = "📜 *MT5 EXECUTION HISTORY (Last 5)*\n-----------------------------------------\n"
            for t in trades:
                side_icon = "🟢" if t.side == "BUY" else "🔴"
                msg += (
                    f"{side_icon} *Ticket #{t.ticket}* | {t.symbol} ({t.side})\n"
                    f"   Price: ${t.price} | Volume: {t.qty} lot\n"
                    f"   Time: {t.timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
                )

        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
    finally:
        db.close()


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    analysis = broker.get_market_analysis(ACTIVE_SYMBOL)
    msg = (
        f"📋 *STRATEGY LOGS*\n"
        f"-----------------------------------------\n"
        f"Strategy: {analysis['strategy_name']}\n"
        f"Symbol: {ACTIVE_SYMBOL}\n"
        f"Signal: {analysis['signal']}\n"
        f"Rationale: {analysis['reason']}"
    )
    await update.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=get_main_keyboard()
    )


async def auto_trade_job(context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        sys_settings = db.query(SystemSettings).filter_by(id=1).first()
        if not sys_settings or not sys_settings.auto_trade_enabled:
            return

        current_balance = broker.get_account_balance()
        target_goal = sys_settings.target_goal

        # Automatically stop trading when target goal is met or exceeded
        if target_goal > 0 and current_balance >= target_goal:
            sys_settings.auto_trade_enabled = False
            db.commit()

            logger.info(
                f"Target goal of ${target_goal:,.2f} reached! Disabling auto-trader."
            )

            if settings.ADMIN_USER_ID:
                target_reached_msg = (
                    f"🎉 *TARGET GOAL REACHED!*\n"
                    f"-----------------------------------------\n"
                    f"💵 *Final Balance:* ${current_balance:,.2f}\n"
                    f"🎯 *Target Goal:* ${target_goal:,.2f}\n\n"
                    f"🛑 *Auto-Trading Engine has been automatically DEACTIVATED* to protect your profits."
                )
                await context.bot.send_message(
                    chat_id=settings.ADMIN_USER_ID,
                    text=target_reached_msg,
                    parse_mode="Markdown",
                )
            return

        analysis = broker.get_market_analysis(ACTIVE_SYMBOL)
        side = analysis["signal"]

        if side not in ["BUY", "SELL"]:
            return

        if broker.has_open_position(ACTIVE_SYMBOL):
            logger.info(
                f"Position already open for {ACTIVE_SYMBOL}. Waiting for exit..."
            )
            return

        result = broker.execute_protected_trade(
            symbol=ACTIVE_SYMBOL,
            side=side,
            sl_dollars=5.0,
            tp_dollars=10.0,
        )

        if result.get("status") == "success" and settings.ADMIN_USER_ID:
            side_icon = "🟢" if side == "BUY" else "🔴"
            trade_msg = (
                f"🎯 *AUTOMATED STRATEGY TRADE EXECUTED*\n"
                f"-----------------------------------------\n"
                f"🧠 *Strategy Used:* {analysis['strategy_name']}\n"
                f"• *Ticket:* #{result.get('ticket')}\n"
                f"• *Symbol:* {result.get('symbol')}\n"
                f"• *Signal:* {side_icon} {side}\n"
                f"• *Volume:* {result.get('qty')} lot\n"
                f"• *Entry Price:* ${result.get('price'):,.2f}\n"
                f"• *Stop Loss:* ${result.get('sl'):,.2f}\n"
                f"• *Take Profit:* ${result.get('tp'):,.2f}\n"
                f"• *Target Goal:* ${target_goal:,.2f}\n"
                f"• *Reason:* _{analysis['reason']}_"
            )
            await context.bot.send_message(
                chat_id=settings.ADMIN_USER_ID,
                text=trade_msg,
                parse_mode="Markdown",
            )
        elif result.get("status") == "error":
            logger.warning(f"Auto Trade Execution Error: {result.get('message')}")
    except Exception as e:
        logger.error(f"Error in auto_trade_job: {e}")
    finally:
        db.close()


def main():
    init_db()
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("autotrade", autotrade_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("logs", logs_command))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_target_goal_input)
    )

    if app.job_queue:
        app.job_queue.run_repeating(auto_trade_job, interval=15, first=3)

    logger.info("Bot execution engine starting...")
    app.run_polling()


if __name__ == "__main__":
    main()