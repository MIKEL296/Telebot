import logging
from config import settings
from database import SessionLocal, TradeHistory

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class BrokerGateway:
    def __init__(self):
        try:
            self.login = int(settings.MT5_LOGIN)
        except (ValueError, TypeError):
            self.login = 0
        self.password = str(settings.MT5_PASSWORD)
        self.server = str(settings.MT5_SERVER)
        self.path = str(settings.MT5_PATH)

    def _ensure_connection(self) -> tuple[bool, str]:
        if not MT5_AVAILABLE:
            return False, "MT5 library missing or unsupported OS."

        if self.login == 0 or not self.password or not self.server:
            return False, "MT5 credentials missing in configuration."

        # Check if terminal IPC connection is already established
        terminal_info = mt5.terminal_info()
        if terminal_info is not None:
            return True, "Connected"

        init_success = mt5.initialize(
            path=self.path,
            login=self.login,
            password=self.password,
            server=self.server,
        )

        if not init_success:
            err = mt5.last_error()
            return False, f"MT5 Auth Failed. Code: {err}"

        return True, "Connected"

    def resolve_symbol(self, raw_symbol: str) -> str:
        candidates = [
            raw_symbol,
            f"{raw_symbol}m",
            f"{raw_symbol}c",
            f"{raw_symbol}.a",
            f"{raw_symbol}_i",
        ]
        for sym in candidates:
            info = mt5.symbol_info(sym)
            if info is not None:
                return sym
        return raw_symbol

    def get_account_balance(self) -> float:
        connected, _ = self._ensure_connection()
        if not connected:
            return 0.0

        acc_info = mt5.account_info()
        return acc_info.balance if acc_info else 0.0

    def has_open_position(self, symbol: str) -> bool:
        connected, _ = self._ensure_connection()
        if not connected:
            return False

        active_symbol = self.resolve_symbol(symbol)
        positions = mt5.positions_get(symbol=active_symbol)
        return len(positions) > 0 if positions is not None else False

    def calculate_lot_size(
        self, symbol: str, risk_percent: float = 1.0, sl_pips: float = 20.0
    ) -> float:
        balance = self.get_account_balance()
        if balance <= 0:
            return 0.01

        risk_amount = balance * (risk_percent / 100.0)
        lot = round(risk_amount / (sl_pips * 10), 2)
        return max(0.01, lot)

    def execute_protected_trade(
        self,
        symbol: str,
        side: str,
        sl_dollars: float = 5.0,
        tp_dollars: float = 10.0,
    ) -> dict:
        connected, msg = self._ensure_connection()
        if not connected:
            return {"status": "error", "message": msg}

        active_symbol = self.resolve_symbol(symbol)
        if not mt5.symbol_select(active_symbol, True):
            return {
                "status": "error",
                "message": f"Symbol {active_symbol} unavailable.",
            }

        tick = mt5.symbol_info_tick(active_symbol)
        symbol_info = mt5.symbol_info(active_symbol)
        if not tick or not symbol_info:
            return {
                "status": "error",
                "message": "Failed to fetch market tick.",
            }

        digits = symbol_info.digits
        qty = self.calculate_lot_size(active_symbol, risk_percent=1.0, sl_pips=20.0)

        if side.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            sl = round(price - sl_dollars, digits)
            tp = round(price + tp_dollars, digits)
        elif side.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
            sl = round(price + sl_dollars, digits)
            tp = round(price - tp_dollars, digits)
        else:
            return {"status": "error", "message": f"Invalid order side: {side}"}

        # Resolve supported filling modes for Exness
        filling_mode_flags = symbol_info.filling_mode
        if filling_mode_flags & mt5.ORDER_FILLING_FOK:
            filling_type = mt5.ORDER_FILLING_FOK
        elif filling_mode_flags & mt5.ORDER_FILLING_IOC:
            filling_type = mt5.ORDER_FILLING_IOC
        else:
            filling_type = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": active_symbol,
            "volume": qty,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 50,
            "magic": 888111,
            "comment": "MutiBot Auto Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }

        result = mt5.order_send(request)

        if result is None:
            last_err = mt5.last_error()
            logger.error(f"Trade Execution Failed: No Response. MT5 Error: {last_err}")
            return {
                "status": "error",
                "message": f"Broker Rejected Order: No Response (Code: {last_err[0]} - {last_err[1]})",
            }

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            err_code = result.retcode
            err_comment = result.comment
            logger.error(f"Trade Execution Failed: {err_comment} (Code: {err_code})")
            return {
                "status": "error",
                "message": f"Broker Rejected Order: {err_comment} (Code: {err_code})",
            }

        # Store in DB
        db = SessionLocal()
        try:
            trade_entry = TradeHistory(
                ticket=result.order,
                symbol=active_symbol,
                side=side.upper(),
                qty=qty,
                price=result.price,
            )
            db.add(trade_entry)
            db.commit()
        finally:
            db.close()

        return {
            "status": "success",
            "ticket": result.order,
            "symbol": active_symbol,
            "price": result.price,
            "qty": qty,
            "sl": sl,
            "tp": tp,
        }


broker = BrokerGateway()