import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
    
    # MetaTrader 5 Configuration
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "Exness-MT5Trial9")
    # Raw string prefix 'r' fixes the \P escape sequence warning
    MT5_PATH: str = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()