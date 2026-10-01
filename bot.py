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

CURRENT_PREDICTION = {
    "symbol": "XAUUSD",
    "signal": "BUY",
    "sl_dollars": 5.0,
    "tp_dollars": 10.0,
}


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
        "⚡ *Muti Bot Dashboard Active*\nSelect a control button below:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    balance = broker.get_account_balance()

    reply_msg = (
        f"📊 *LIVE MARKET PREDICTION*\n"
        f"-----------------------------------------\n"
        f"• *Asset:* {CURRENT_PREDICTION['symbol']}\n"
        f"• *Predicted Action:* `{CURRENT_PREDICTION['signal']}`\n"
        f"• *Current MT5 Equity:* ${balance:,.2f}\n"
        f"• *Target SL / TP:* ${CURRENT_PREDICTION['sl_dollars']} /${CURRENT_PREDICTION['tp_dollars']}\n\n"
        f"💡 _Run /autotrade to let the bot automatically execute predicted trades._"
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
            f"🛡️ *Engine:* Picking and executing live predictions."
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

        msg = (
            f"⚙️ *REAL-TIME SYSTEM STATUS*\n"
            f"-----------------------------------------\n"
            f"🤖 *Auto-Execution State:* {state_str}\n"
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
                msg += (
                    f"🔹 *Ticket #{t.ticket}* | {t.symbol} ({t.side})\n"
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
    await update.message.reply_text(
        "📋 *SYSTEM LOGS:* Exness MT5 gateway active.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )


async def auto_trade_job(context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        sys_settings = db.query(SystemSettings).filter_by(id=1).first()
        if not sys_settings or not sys_settings.auto_trade_enabled:
            return

        current_balance = broker.get_account_balance()
        if (
            current_balance >= sys_settings.target_goal
            and sys_settings.target_goal > 0
        ):
            sys_settings.auto_trade_enabled = False
            db.commit()
            logger.info("Target Goal reached. Auto trading deactivated.")
            return

        symbol = CURRENT_PREDICTION["symbol"]
        side = CURRENT_PREDICTION["signal"]

        if side not in ["BUY", "SELL"]:
            return

        if broker.has_open_position(symbol):
            logger.info(f"Position already open for {symbol}. Waiting for exit...")
            return

        result = broker.execute_protected_trade(
            symbol=symbol,
            side=side,
            sl_dollars=CURRENT_PREDICTION["sl_dollars"],
            tp_dollars=CURRENT_PREDICTION["tp_dollars"],
        )

        if result.get("status") == "success" and settings.ADMIN_USER_ID:
            trade_msg = (
                f"🎯 *PREDICTED TRADE EXECUTED ON EXNESS*\n"
                f"-----------------------------------------\n"
                f"• *Ticket:* #{result.get('ticket')}\n"
                f"• *Symbol:* {result.get('symbol')}\n"
                f"• *Signal:* {side}\n"
                f"• *Volume:* {result.get('qty')} lot\n"
                f"• *Entry Price:* ${result.get('price'):,.2f}\n"
                f"• *Stop Loss:* ${result.get('sl'):,.2f}\n"
                f"• *Take Profit:* ${result.get('tp'):,.2f}"
            )
            await context.bot.send_message(
                chat_id=settings.ADMIN_USER_ID,
                text=trade_msg,
                parse_mode="Markdown",
            )
        elif result.get("status") == "error":
            logger.warning(
                f"Auto Trade Execution Error: {result.get('message')}"
            )
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
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, handle_target_goal_input
        )
    )

    if app.job_queue:
        app.job_queue.run_repeating(auto_trade_job, interval=15, first=3)

    logger.info("Bot execution engine starting...")
    app.run_polling()


if __name__ == "__main__":
    main()