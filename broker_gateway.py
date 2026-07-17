# ==========================================
# FILE: broker_gateway.py
# ==========================================
import logging
import MetaTrader5 as mt5
from config import settings

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class BrokerGateway:
    """Manages secure communication interfaces with the Exness MT5 Terminal Server."""
    
    def __init__(self):
        self.login = settings.MT5_LOGIN
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER

    def _ensure_connection(self) -> bool:
        """Initializes and authenticates against Exness live servers."""
        if not mt5.initialize():
            logger.error("Critical Failure: MT5 terminal initialization failed.")
            return False
            
        authorized = mt5.login(login=self.login, password=self.password, server=self.server)
        if not authorized:
            logger.error(f"Exness Authentication Denied for account {self.login}. Error: {mt5.last_error()}")
            return False
        return True

    def get_account_details(self) -> dict:
        """Pings Exness real-time account cash metrics."""
        if not self._ensure_connection():
            return {"status": "error", "message": "Broker Connection Offline"}
            
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
        """Executes market orders with active Stop Loss (SL) and Take Profit (TP)."""
        if not self._ensure_connection():
            return {"status": "error", "message": "Broker Connection Offline"}

        mt5.symbol_select(symbol, True)
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            mt5.shutdown()
            return {"status": "error", "message": f"Symbol {symbol} not found on Exness server."}

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
            "sl": float(sl),                       # Safety Stop Loss Target
            "tp": float(tp),                       # Safety Take Profit Target
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