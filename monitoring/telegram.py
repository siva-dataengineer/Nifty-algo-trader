# monitoring/telegram.py
import requests, logging
import config

log = logging.getLogger(__name__)

def send(msg: str):
    try:
        url = f"https://api.telegram.org/bot{config.TG_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": config.TG_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"[TELEGRAM] Failed to send: {e}")

def trade_entry(symbol, side, qty, price, sl):
    send(f"<b>ENTRY {side}</b>\n"
         f"Symbol: {symbol}\n"
         f"Qty: {qty} | Price: ₹{price:.2f}\n"
         f"Stop Loss: ₹{sl:.2f}")

def trade_exit(symbol, qty, price, pnl):
    sign = "+" if pnl >= 0 else ""
    send(f"<b>EXIT</b>\n"
         f"Symbol: {symbol}\n"
         f"Qty: {qty} | Price: ₹{price:.2f}\n"
         f"PnL: <b>{sign}₹{pnl:.0f}</b>")

def daily_summary(pnl, trades, sharpe=None):
    sign = "+" if pnl >= 0 else ""
    msg  = (f"<b>Daily Summary</b>\n"
            f"Total PnL: <b>{sign}₹{pnl:.0f}</b>\n"
            f"Trades: {trades}")
    if sharpe:
        msg += f"\nSharpe: {sharpe:.2f}"
    send(msg)

def error_alert(context: str, error: str):
    send(f"<b>ERROR</b>\n{context}\n<code>{error}</code>")

def bot_started():
    send("<b>Nifty Algo Bot started</b>\nWaiting for market open (9:15 AM)...")

def bot_stopped():
    send("<b>Nifty Algo Bot stopped</b>")