# ==========================================
# FILE: check_mt5.py
# ==========================================
import MetaTrader5 as mt5
from config import settings

print("🔍 Testing MT5 Direct Connection...")
print(f"• Target Login: {settings.MT5_LOGIN} (Type: {type(settings.MT5_LOGIN).__name__})")
print(f"• Target Server: {settings.MT5_SERVER}")

if not mt5.initialize():
    print(f"❌ MT5 terminal initialization failed. Error: {mt5.last_error()}")
    quit()

# Attempt explicit login
login_num = int(settings.MT5_LOGIN)
auth_ok = mt5.login(login=login_num, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER)

if auth_ok:
    acc = mt5.account_info()
    print("🟢 SUCCESS! Connected to Exness Account.")
    print(f"   Account Number: {acc.login}")
    print(f"   Server: {acc.server}")
    print(f"   Balance: ${acc.balance:,.2f} {acc.currency}")
    print(f"   Equity: ${acc.equity:,.2f}")
else:
    err_code, err_msg = mt5.last_error()
    print(f"❌ AUTHENTICATION FAILED!")
    print(f"   Error Code: {err_code}")
    print(f"   Error Details: {err_msg}")
    print("\n💡 Common Fixes:")
    print("   1. Check Exness Personal Area -> Accounts -> Settings -> Server Name (e.g., Exness-MT5Real8).")
    print("   2. Verify you are using the MT5 Trading Password, NOT your Exness website login password.")

mt5.shutdown()