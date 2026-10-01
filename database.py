# ==========================================
# FILE: database.py
# ==========================================
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)
    mode = Column(String)
    quantity = Column(Float, default=5.0)
    entry_price = Column(Float)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    estimated_duration = Column(String, nullable=True)
    pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)