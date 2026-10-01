# ==========================================
# FILE: broker_gateway.py
# ==========================================
import logging
from config import settings

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not available on this platform. Broker operations in simulation mode.")

class BrokerGateway:
    """Manages communication interfaces with MT5 with platform fallback."""
    
    def __init__(self):
        self.login = settings.MT5_LOGIN
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER

    def _ensure_connection(self) -> bool:
        if not MT5_AVAILABLE:
            logger.error("MT5 execution unavailable on Linux/Cloud environment.")
            return False

        if not mt5.initialize():
            logger.error("Critical Failure: MT5 terminal initialization failed.")
            return False
            
        authorized = mt5.login(login=self.login, password=self.password, server=self.server)
        if not authorized:
            logger.error(f"Exness Authentication Denied for account {self.login}. Error: {mt5.last_error()}")
            return False
        return True

    def get_account_details(self) -> dict:
        if not self._ensure_connection():
            return {"status": "error", "message": "Broker Gateway Offline or Unsupported"}
            
        account_info = mt5.account_info()
        if account_info is None:
            mt5.shutdown()
            return {"status": "error", "message": "Failed to fetch account metrics"}
            
        data = {
            "status": "success",
            "cash": account_info.balance,
            "equity": account_info.equity,
            "buying_power": account_info.margin_free
        }
        mt5.shutdown()
        return data

    def execute_market_order(self, symbol: str, qty: float, side: str, sl: float = 0.0, tp: float = 0.0) -> dict:
        if not self._ensure_connection():
            return {"status": "error", "message": "Broker Gateway Offline or Unsupported"}

        mt5.symbol_select(symbol, True)
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            mt5.shutdown()
            return {"status": "error", "message": f"Symbol {symbol} not found on broker server."}

        if side.lower() == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        elif side.lower() == "sell":
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            mt5.shutdown()
            return {"status": "error", "message": f"Invalid order side: {side}"}

        request = {
            "action": mt5.TRADE_ACTION_DEAL,      
            "symbol": symbol,
            "volume": float(qty),
            "type": order_type,
            "price": price,
            "sl": float(sl),                       
            "tp": float(tp),                       
            "deviation": 20,                       
            "magic": 234000,                       
            "comment": "Bot Automated Entry",
            "type_time": mt5.ORDER_TIME_GTC,       
            "type_filling": mt5.ORDER_FILLING_IOC, 
        }

        result = mt5.order_send(request)
        mt5.shutdown() 

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Execution Rejected for {symbol}: {result.comment} (Code: {result.retcode})")
            return {"status": "error", "message": f"Execution failed: {result.comment} (Code: {result.retcode})"}
            
        logger.info(f"Order Implemented Successfully: Ticket #{result.order} | Price: {result.price}")
        return {"status": "success", "ticket": result.order, "price": result.price}