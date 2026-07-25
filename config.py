# ==========================================
# FILE: config.py
# ==========================================
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_ID: int = int(os.getenv("TELEGRAM_ADMIN_ID", 0))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///finance_track.db")
    
    class Config:
        case_sensitive = True

settings = Settings()