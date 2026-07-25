# ==========================================
# FILE: database.py
# ==========================================
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./finance_track.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    symbol = Column(String, index=True)
    action = Column(String)            # BUY / SELL
    mode = Column(String)              # STRICT CONFLUENCE / LENIENT SCALP
    quantity = Column(Float, default=5.0)
    entry_price = Column(Float)        # Price predicted at time of signal
    stop_loss = Column(Float)          # Suggested SL
    take_profit = Column(Float)        # Suggested TP
    estimated_duration = Column(String)# Expected duration (e.g. '1h 30m')
    pnl = Column(Float, default=0.0)   # Dynamic floating PnL tracking prediction accuracy
    running_balance = Column(Float, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Signal database tables successfully verified.")